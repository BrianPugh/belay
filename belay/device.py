import ast
import atexit
import concurrent.futures
import contextlib
import importlib.resources as importlib_resources
import linecache
import re
import shutil
import sys
from inspect import signature
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from types import ModuleType
from typing import Any, Callable, Optional, TextIO, TypeVar, Union, overload

from serial import SerialException
from serial.tools.miniterm import Miniterm
from typing_extensions import ParamSpec

from ._minify import minify as minify_code
from .device_meta import DeviceMeta
from .device_support import Implementation, MethodMetadata, sort_executers
from .device_sync_support import (
    discover_files_dirs,
    generate_dst_dirs,
    preprocess_ignore,
    preprocess_keep,
    preprocess_src_file_hash,
)
from .exceptions import (
    ConnectionLost,
    InternalError,
    MaxHistoryLengthError,
    NotBelayResponseError,
)
from .executers import (
    Executer,
    SetupExecuter,
    TaskExecuter,
    TeardownExecuter,
    ThreadExecuter,
)
from .helpers import get_fnv1a32_native_path, read_snippet, wraps_partial
from .inspect import import_names, isexpression
from .proxy_object import ProxyObject, get_proxy_object_target_name
from .pyboard import Pyboard, PyboardError, PyboardException
from .typing import BelayReturn, PathType
from .utils import Sentinel
from .webrepl import WebreplToSerial

P = ParamSpec("P")
R = TypeVar("R")


class UNPARSABLE_RESULT(Sentinel):  # noqa: N801
    """Could not parse the micropython repr return value; could be a non-AST object."""


class NO_RESULT(Sentinel):  # noqa: N801
    """No result."""


def remove_call(expression: str, func_name: str, required=False) -> str:
    expression = expression.strip()
    func_name_with_parenthesis = func_name + "("
    if expression.startswith(func_name_with_parenthesis) and expression[-1] == ")":
        return expression[len(func_name_with_parenthesis) : -1]

    if required:
        raise ValueError

    return expression


def extended_literal_eval(expression):
    """
    Extended version of ast.literal_eval that also handles other common builtins.
    """
    # If it's a string that looks like dict_keys, convert it to a list
    if isinstance(expression, str) and expression.startswith("dict_keys("):
        return list(ast.literal_eval(remove_call(expression, "dict_keys")))

    return ast.literal_eval(expression)


def parse_belay_response(
    line: str,
    result_parser: Callable[[str], Any] = extended_literal_eval,
):
    """Parse a Belay response string into a python object.

    Parameters
    ----------
    line: str
        String representations of a python object.
        e.g. "(1, 2, 'foo')"
    result_parser: Callable
        Function that accepts a string and returns a python object.
    """
    if not line.startswith("_BELAY"):
        raise NotBelayResponseError
    line = line.rstrip()
    line = line[6:]
    code, line = line[0], line[1:]

    if code == "R":
        # Result
        id_, line = line.split("|", 1)
        id_ = int(id_) if id_ else NO_RESULT
        if not line:
            return id_, NO_RESULT
        try:
            parsed_result = result_parser(line)
        except Exception:
            parsed_result = UNPARSABLE_RESULT
        return id_, parsed_result
    elif code == "S":
        # StopIteration
        raise StopIteration
    else:
        raise ValueError(f'Received unknown code: "{code}"')


class Device(metaclass=DeviceMeta):
    """Belay interface into a micropython device.

    Can be used as a context manager; calls ``self.close`` on exit.

    Uses the ``autoregistry.RegistryMeta`` metaclass for easy-to-access subclasses.

    Attributes
    ----------
    implementation: Implementation
        Implementation details of device.

    Notes
    -----
    When subclassing Device, it is probably easier to override the following method hooks rather than
    overriding :meth:`__init__`:

    * :meth:`__pre_autoinit__` - Called before ``@Device.setup(autoinit=True)`` methods.
      Ideal for syncing files or dependencies via :meth:`sync` or :meth:`sync_dependencies`.

    * :meth:`__post_init__` - Called after ``@Device.setup(autoinit=True)`` methods.
      Ideal for setting host attributes based on device state.
    """

    MAX_CMD_HISTORY_LEN = 1000

    def __init__(
        self,
        *args,
        startup: Optional[str] = None,
        attempts: int = 0,
        **kwargs,
    ):
        """Create a MicroPython device.

        Parameters
        ----------
        startup: str
            Code to run on startup. Defaults to a few common imports.
        attempts: int
            If device disconnects, attempt to re-connect this many times (with 1 second between attempts).
            WARNING: this may result in unexpectedly long blocking calls when reconnecting!
        """
        self._board_kwargs = signature(Pyboard).bind(*args, **kwargs).arguments
        self.attempts = attempts
        self._cmd_history = []

        self._connect_to_board(**self._board_kwargs)

        self._exec_snippet("startup")

        # Obtain implementation early on so implementation-specific executers can be bound.
        self.implementation = Implementation(
            *self(
                "(sys.implementation.name, sys.implementation.version, sys.platform, getattr(sys.implementation, '_mpy', None))"
            ),
            emitters=self._emitter_check(),
        )

        # Setup executer generators and bind to private attributes.
        executer_generators = {}
        for executer_name, executer_cls in Executer.items():
            executer_generator = executer_cls(self)
            # Private interface, will always be available
            attr_name = f"_belay_{executer_name}"
            setattr(self, attr_name, executer_generator)
            executer_generators[executer_name] = executer_generator

        # If subclassing Device, register methods decorated with
        # executer markers (e.g. ``@Device.task``).
        autoinit_executers = []
        instantiated_executer_names = set()
        for method_name in dir(type(self)):
            # Get method from self to trigger descriptors.
            try:
                method = getattr(self, method_name)
                metadata = method.__belay__
            except AttributeError:
                continue
            executer_name = metadata.executer.__registry__.name
            executer_generator = executer_generators[executer_name]
            executer = executer_generator(method, **metadata.kwargs)
            instantiated_executer_names.add(executer_name)

            if metadata.autoinit:
                autoinit_executers.append(executer)

            setattr(
                self,
                method_name,
                executer,
            )

        # Setup publicly accessible if the name hasn't been stomped.
        for executer_name, executer_generator in executer_generators.items():
            if executer_name in instantiated_executer_names:
                continue
            setattr(self, executer_name, executer_generator)

        if startup is None:
            if self.implementation.name == "circuitpython":
                self._exec_snippet("convenience_imports_circuitpython")
            else:
                self._exec_snippet("convenience_imports_micropython")
        elif startup:
            self(startup)

        self.__pre_autoinit__()

        for executer in sort_executers(autoinit_executers):
            executer()

        atexit.register(self.close)

        self.__post_init__()

    def __pre_autoinit__(self):
        """Runs near the end of ``__init__``, but before methods marked with ``setup(autoinit=True)`` are invoked.

        This would be a good location to call items like:
            * ``self.sync(...)`` - Basic file sync
            * ``self.sync_dependencies(...)`` - More advanced sync.
              Recommended way of getting dependencies on-device.
        """
        pass

    def __post_init__(self):
        """Runs at the very end of ``__init__``.

        Good for subclasses to initialize attributes or to perform additional device setup.
        """
        pass

    def _emitter_check(self):
        # Detect which emitters are available
        emitters = []
        try:
            self._exec_snippet("emitter_check")
        except PyboardException as e:
            if "invalid micropython decorator" not in str(e):
                raise
            # Get line of exception
            line_e = int(re.findall(r"line (\d+)", str(e))[-1])
            if line_e == 1:
                # No emitters available
                pass
            else:
                emitters.append("native")
                if line_e == 3:
                    # viper is not available
                    pass
                else:
                    raise InternalError(f"Unknown emitter line {line_e}.") from e
        else:
            emitters.append("native")
            emitters.append("viper")
            self("del __belay_emitter_test")

        return tuple(emitters)

    def _connect_to_board(self, **kwargs):
        self._board = Pyboard(**kwargs)
        soft_reset = not isinstance(self._board.serial, WebreplToSerial)
        self._board.enter_raw_repl(soft_reset=soft_reset)

    def _exec_snippet(self, *names: str) -> BelayReturn:
        """Load and execute a snippet from the snippets sub-package.

        Parameters
        ----------
        names : str
            Snippet(s) to load and execute.
        """
        snippets = [read_snippet(name) for name in names]
        return self("\n".join(snippets))

    def __call__(
        self,
        cmd: Union[str, ProxyObject],
        *,
        minify: bool = True,
        stream_out: TextIO = sys.stdout,
        record=True,
        trusted: bool = False,
        proxy: bool = False,
        delete: Optional[bool] = None,
    ):
        """Execute code on-device.

        This method can execute both Python statements (e.g., ``x = 5``) and expressions
        (e.g., ``x + 5``).

        Parameters
        ----------
        cmd: Union[str, ProxyObject]
            Python code to execute. May be a statement or expression.
            If a :class:`ProxyObject`, will resolve it to its actual remote value.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Reduces the number of characters that need to be transmitted.
            Defaults to ``True``.
        stream_out: TextIO
            Stream to write device output to. Defaults to ``sys.stdout``.
            Set to ``None`` to suppress output.
        record: bool
            Record the call for state-reconstruction if device is accidentally reset.
            Defaults to ``True``.
        trusted: bool
            Fully trust remote device for parsing return values.
            When set to ``False`` (default), only AST-safe types
            ``[None, bool, bytes, int, float, str, List, Dict, Set]`` can be parsed.
            When set to ``True``, any value whose ``repr`` can be evaluated is returned.
            **Warning**: ``trusted=True`` allows the remote device to execute arbitrary
            code on the host. Only use with devices you fully trust.
            Defaults to ``False``.
        proxy: bool
            Create a :class:`ProxyObject` for expression results instead of returning
            the actual value.

            When ``True``:
                - Mutable objects (list, dict, custom classes) return as :class:`ProxyObject`
                - Immutable objects (int, str, bool, etc.) still return as direct values
                - Import statements are automatically detected and create proxies

            Examples::

                # Without proxy - returns actual list
                my_list = device("sensor.readings")  # [1, 2, 3]

                # With proxy - returns ProxyObject wrapper
                my_list_proxy = device("sensor.readings", proxy=True)
                my_list_proxy[0]  # Access via proxy, returns 1

                # Resolve proxy to actual value
                actual_list = device(my_list_proxy)  # [1, 2, 3]

            Defaults to ``False``.
        delete: Optional[bool]
            Control lifecycle of remote objects when using ``proxy=True``.

            When ``True``: Remote object is deleted when the Python :class:`ProxyObject` is
            garbage collected. Use for temporary/intermediate objects.

            When ``False``: Remote object persists after :class:`ProxyObject` deletion.
            Use for long-lived objects like imported modules.

            When ``None`` (default):
                - ``False`` if ``cmd`` is an import statement
                - ``True`` otherwise

            Examples::

                # Auto-delete temporary object
                temp = device("[1, 2, 3]", proxy=True)  # delete=True (default)
                del temp  # Remote list is deleted

                # Keep imported module
                os = device("import os", proxy=True)  # delete=False (default for imports)
                del os  # Remote 'os' module persists

                # Explicitly control
                keep = device("my_data", proxy=True, delete=False)

        Returns
        -------
        Any
            Return value depends on the code and parameters:

            - **Statements**: Returns ``None``
            - **Expressions with proxy=False**: Returns the actual parsed value
            - **Expressions with proxy=True**:
                - Immutable types: Returns actual value (int, str, bool, None, bytes, float)
                - Mutable types: Returns :class:`ProxyObject`
            - **Import statements with proxy=True**: Returns :class:`ProxyObject` or
              tuple of :class:`ProxyObject` for multiple imports

        Raises
        ------
        PyboardException
            If the remote code execution fails or raises an exception.
        ConnectionLost
            If the device connection is lost during execution.

        Examples
        --------
        Basic usage::

            # Execute a statement
            device("led.on()")

            # Execute an expression and get the result
            temperature = device("sensor.temperature()")

            # Use proxy mode for remote object interaction
            sensor_proxy = device("sensor", proxy=True)
            temperature = sensor_proxy.temperature()

            # Import and use modules
            machine = device("import machine", proxy=True)
            pin = machine.Pin(25, machine.Pin.OUT)

            # Resolve a proxy to get actual value
            my_list_proxy = device("[1, 2, 3]", proxy=True)
            actual_list = device(my_list_proxy)  # [1, 2, 3]
        """
        if isinstance(cmd, ProxyObject):
            cmd = get_proxy_object_target_name(cmd)

        cmd = dedent(cmd)

        if minify:
            cmd = minify_code(cmd)

        is_expression = isexpression(cmd)
        imported_names = import_names(cmd)
        if delete is None:
            if imported_names:
                delete = False
            else:
                delete = True
        if is_expression:
            # Belay Tasks are inherently expressions as well.
            if proxy:
                cmd = f"__belay_obj_create({cmd})"
            else:
                cmd = f'print("_BELAYR|"+repr({cmd}))'

        if record and self.attempts and len(self._cmd_history) < self.MAX_CMD_HISTORY_LEN:
            self._cmd_history.append(cmd)

        id_, result = NO_RESULT, NO_RESULT
        data_consumer_buffer = bytearray()

        def data_consumer(data):
            """Handle input data stream immediately."""
            nonlocal id_, result
            data = data.replace(b"\x04", b"")
            if not data:
                return
            data_consumer_buffer.extend(data)
            while (i := data_consumer_buffer.find(b"\n")) >= 0:
                i += 1
                line = data_consumer_buffer[:i].decode()
                data_consumer_buffer[:] = data_consumer_buffer[i:]
                try:
                    if trusted:
                        id_, result = parse_belay_response(line, result_parser=eval)
                    else:
                        id_, result = parse_belay_response(line)
                except NotBelayResponseError:
                    if stream_out:
                        stream_out.write(line)

        try:
            self._board.exec(cmd, data_consumer=data_consumer)
        except (SerialException, ConnectionResetError) as e:
            # Board probably disconnected.
            if self.attempts:
                self.reconnect()
                self._board.exec(cmd, data_consumer=data_consumer)
            else:
                raise ConnectionLost from e

        if id_ is not NO_RESULT:
            result = ProxyObject(self, f"__belay_obj_{id_}", delete=delete)
        elif result is NO_RESULT:
            if proxy:
                if imported_names:
                    # Create a ProxyObject for the imported objects.
                    if len(imported_names) == 1:
                        return self(imported_names[0], proxy=True, delete=False)
                    else:
                        return tuple(self(x, proxy=True, delete=False) for x in imported_names)
                else:
                    raise NotImplementedError("Unreachable: NO_RESULT, proxy=True, not import.")
            else:
                # Happens for non-expressions.
                result = None
        else:
            # Typical AST-parsed result.
            pass

        return result

    def proxy(self, cmd: str, delete: Optional[bool] = None) -> Union[ProxyObject, tuple[ProxyObject, ...]]:
        """Create a :class:`.ProxyObject` for interacting with remote objects.

        This is a convenience method that combines object creation and proxy wrapping.
        It automatically detects whether ``cmd`` is a simple variable name, an expression,
        or an import statement, and handles each appropriately.

        Parameters
        ----------
        cmd: str
            Remote object reference, expression, or import statement.

            - **Identifier** (e.g., ``"my_var"``): Creates proxy to existing variable
            - **Expression** (e.g., ``"[1, 2, 3]"``): Evaluates and creates proxy to result
            - **Import** (e.g., ``"import os"``): Imports module and creates proxy to it

        delete: Optional[bool]
            Control remote object lifecycle when proxy is deleted.

            - ``True``: Delete remote object when proxy is garbage collected
            - ``False``: Keep remote object after proxy deletion
            - ``None`` (default): Auto-detect based on ``cmd``:
                - Identifiers → ``False`` (preserve existing variables)
                - Import statements → ``False`` (preserve imported modules)
                - Expressions → ``True`` (clean up temporary objects)

        Returns
        -------
        Union[ProxyObject, Tuple[ProxyObject, ...]]
            - Single :class:`ProxyObject` for most cases
            - Tuple of :class:`ProxyObject` instances for multi-import statements
              (e.g., ``"from math import sin, cos"``)

        Examples
        --------
        Reference existing variable::

            device("sensor_data = [1, 2, 3, 4, 5]")
            data_proxy = device.proxy("sensor_data")
            print(data_proxy[0])  # 1
            # sensor_data persists on device after data_proxy is deleted

        Create proxy from expression::

            # Create temporary list on device
            temp_proxy = device.proxy("[10, 20, 30]")
            print(temp_proxy[1])  # 20
            # List is auto-deleted when temp_proxy goes out of scope

        Import and use modules::

            # Import a module
            machine = device.proxy("import machine")
            pin = machine.Pin(25, machine.Pin.OUT)
            pin.on()

        Multiple imports::

            # Import multiple items
            sin, cos = device.proxy("from math import sin, cos")
            result = sin(0)  # 0

        See Also
        --------
        ProxyObject : The proxy object class for remote object interaction
        Device.__call__ : Lower-level method for executing code with proxy support
        """
        if cmd.isidentifier():
            if delete is None:
                delete = False
            return ProxyObject(self, cmd, delete=delete)
        else:
            return self(cmd, proxy=True, delete=delete)

    def sync(
        self,
        folder: PathType,
        dst: str = "/",
        keep: Union[None, list, str, bool] = None,
        ignore: Union[None, list, str] = None,
        minify: bool = True,
        mpy_cross_binary: Union[str, Path, None] = None,
        progress_update=None,
    ) -> None:
        """Sync a local directory to the remote filesystem.

        For each local file, check the remote file's hash, and transfer if they differ.
        If a file/folder exists on the remote filesystem that doesn't exist in the local
        folder, then delete it (unless it's in ``keep``).

        Parameters
        ----------
        folder: str, Path
            Single file or directory of files to sync to the root of the board's filesystem.
        dst: str
            Destination **directory** on device.
            Defaults to unpacking ``folder`` to root.
        keep: None | str | list | bool
            Do NOT delete these file(s) on-device if not present in ``folder``.
            If ``true``, don't delete any files on device.
            If ``false``, delete all unsynced files (same as passing ``[]``).
            If ``dst is None``, defaults to ``["boot.py", "webrepl_cfg.py", "lib"]``.
        ignore: None | str | list
            Git's wildmatch patterns to NOT sync to the device.
            Defaults to ``["*.pyc", "__pycache__", ".DS_Store", ".pytest_cache"]``.
        minify: bool
            Minify python files prior to syncing.
            Defaults to ``True``.
        mpy_cross_binary: Union[str, Path, None]
            Path to mpy-cross binary. If provided, ``.py`` will automatically
            be compiled.
            Takes precedence over minifying.
        progress_update:
            Partial for ``rich.progress.Progress.update(task_id,...)`` to update with sync status.
        """
        folder = Path(folder).resolve()

        dst = str(dst)
        if not dst.startswith("/"):
            raise ValueError('dst must start with "/"')
        elif len(dst) > 1:
            dst = dst.rstrip("/")

        if not folder.exists():
            raise ValueError(f'"{folder}" does not exist.')

        with TemporaryDirectory() as tmp_dir, concurrent.futures.ThreadPoolExecutor() as executor:
            tmp_dir = Path(tmp_dir)

            # Create a list of all files and dirs (on-device).
            # This is so we know what to clean up after done syncing.
            snippets_to_execute = []

            # Remove the keep files from the on-device ``all_files`` set
            # so they don't get deleted.
            keep_all = folder.is_file() or keep is True
            keep = preprocess_keep(keep, dst)
            ignore = preprocess_ignore(ignore)

            src_files, src_dirs, dst_files = discover_files_dirs(dst, folder, ignore)

            def _preprocess_src_file_hash_helper(src_file):
                return preprocess_src_file_hash(tmp_dir, src_file, minify, mpy_cross_binary)

            futures = [executor.submit(_preprocess_src_file_hash_helper, src_file) for src_file in src_files]

            if progress_update:
                progress_update(description="Bootstrapping sync...")

            if self.implementation.name == "circuitpython":
                snippets_to_execute.append("ilistdir_circuitpython")
            else:
                snippets_to_execute.append("ilistdir_micropython")

            snippets_to_execute.append("sync_begin")

            # Place the fnv1a32 at the end of snippets_to_execute, as there's a chance
            # the micropython interpreter wasn't compiled with all the required features.
            fnv1a32_native_path = get_fnv1a32_native_path(self.implementation)
            if fnv1a32_native_path:
                # Sync a pre-compiled native fnv1a32 hashing module.
                src_size = fnv1a32_native_path.stat().st_size
                try:
                    # Check if file exists and has the same size
                    remote_size = self("os.stat('/_belay_fnv1a32.mpy')[6]")
                    sync_nativemodule = remote_size != src_size
                except PyboardException:
                    sync_nativemodule = True

                if sync_nativemodule:
                    self._board.fs_put(str(fnv1a32_native_path), "/_belay_fnv1a32.mpy")

                snippets_to_execute.append("hf_nativemodule")
            elif "viper" in self.implementation.emitters:
                snippets_to_execute.append("hf_viper")
            elif "native" in self.implementation.emitters:
                snippets_to_execute.append("hf_native")
            else:
                snippets_to_execute.append("hf")

            try:
                self._exec_snippet(*snippets_to_execute)
            except PyboardException:
                if not fnv1a32_native_path:
                    raise

                # A bit fragile, but fragile for the sake of performance.
                # This is most likely the micropython interpreter being unable to import the fnv1a32 mpy file.
                # Fallback to one of the other fnv1a32 implementations.
                if "viper" in self.implementation.emitters:
                    self._exec_snippet("hf_viper")
                elif "native" in self.implementation.emitters:
                    self._exec_snippet("hf_native")
                else:
                    self._exec_snippet("hf")

            if mpy_cross_binary:
                dst_files = [
                    dst_file.with_suffix(".mpy") if dst_file.suffix == ".py" else dst_file for dst_file in dst_files
                ]
            dst_files = [dst_file.as_posix() for dst_file in dst_files]
            dst_dirs = generate_dst_dirs(dst, folder, src_dirs)

            if keep_all:
                self("del __belay_del_fs")
            else:
                self(
                    f"__belay_del_fs({repr(dst)}, {repr(set(keep + dst_files + ['/_belay_fnv1a32.mpy']))}); del __belay_del_fs"
                )

            # Try and make all remote dirs
            if dst_dirs:
                if progress_update:
                    progress_update(description="Creating remote directories...")
                self(f"__belay_mkdirs({repr(dst_dirs)})")

            # Get all remote hashes
            if progress_update:
                progress_update(description="Fetching remote hashes...")
            dst_hashes = self(f"__belay_hfs({repr(dst_files)})")

            if len(dst_hashes) != len(dst_files):
                raise InternalError

            src_files_and_hashes = [future.result() for future in futures]
            puts = []
            for (src_file, src_hash), dst_file, dst_hash in zip(src_files_and_hashes, dst_files, dst_hashes):
                if src_hash != dst_hash:
                    puts.append((src_file, dst_file))

            if progress_update:
                progress_update(total=len(puts))

            for src_file, dst_file in puts:
                if progress_update:
                    progress_update(description=f"Pushing: {dst_file[1:]}")
                self._board.fs_put(src_file, dst_file)
                if progress_update:
                    progress_update(advance=1)

    def sync_dependencies(
        self,
        package: Union[ModuleType, str],
        *subfolders: PathType,
        dst="/lib",
        **kwargs,
    ):
        """Convenience method for syncing dependencies bundled with package.

        If using Belay's package manager feature, set ``dependencies_path``
        to a folder *inside* your python package (e.g.
        ``dependencies_path="mypackage/dependencies"``).

        The following example will sync all the files/folders in
        ``mypackage/dependencies/main`` to device's ``/lib``.

        .. code-block:: python

            import mypackage

            device.sync_package(mypackage, "dependencies/main")

        For intended use, ``sync_dependencies`` should be **only be called
        once**. Multiple invocations overwrite/delete previous calls' contents.

        .. code-block:: python

            # Good
            device.sync_package(mypackage, "dependencies/main", "dependencies/dev")

            # Bad (deletes on-device files from "dependencies/main")
            device.sync_package(mypackage, "dependencies/main")
            device.sync_package(mypackage, "dependencies/dev")

        Parameters
        ----------
        package: Union[ModuleType, str]
            Either the imported package or the name of a package that
            contains the data we would like to sync.
        *subfolders
            Subfolder(s) to combine and then sync to ``dst``.
            Typically something like "dependencies/main"
        dst: Union[str, Path]
            On-device destination directory.
            Defaults to ``/lib``.
        **kwargs
            Passed along to ``Device.sync``.
        """
        pkg_files = importlib_resources.files(package)
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            for subfolder in subfolders:
                with importlib_resources.as_file(pkg_files / str(subfolder)) as f:
                    shutil.copytree(f, tmp_dir, dirs_exist_ok=True)
            self.sync(tmp_dir, dst=dst, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self) -> None:
        """Close the connection to device.

        Automatically called on context manager exit.
        """
        # Invoke all teardown executers prior to closing out connection.
        if self._board is None:
            # Has already been closed
            return

        atexit.unregister(self.close)

        self._board.cancel_running_program()

        for executer in sort_executers(self._belay_teardown._belay_executers):
            executer()

        self._board.close()
        self._board = None

    def reconnect(self, attempts: Optional[int] = None) -> None:
        """Reconnect to the device and replay the command history.

        Parameters
        ----------
        attempts : int
            Number of times to attempt to connect to board with a 1 second delay in-between.
            If ``None``, defaults to whatever value was supplied to init.
            If init value is 0, then defaults to 1.
        """
        if len(self._cmd_history) == self.MAX_CMD_HISTORY_LEN:
            raise MaxHistoryLengthError

        kwargs = self._board_kwargs.copy()
        kwargs["attempts"] = attempts
        if kwargs["attempts"] is None:
            kwargs["attempts"] = self.attempts if self.attempts else 1

        try:
            self._connect_to_board(**kwargs)
        except PyboardError as e:
            raise ConnectionLost from e

        # Playback the history
        for cmd in self._cmd_history:
            self(cmd, record=False)

    @overload
    @staticmethod
    def setup(f: Callable[P, R]) -> Callable[P, R]: ...

    @overload
    @staticmethod
    def setup(
        *, autoinit: bool = False, implementation: str = "", **kwargs
    ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    @staticmethod
    def setup(
        f: Optional[Callable[P, R]] = None,
        autoinit: bool = False,
        implementation: str = "",
        **kwargs,
    ) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
        """Execute decorated function's body in a global-context on-device when called.

        Function arguments are also set in the global context.

        Can either be used as a staticmethod ``@Device.setup`` for marking methods in a subclass of ``Device``, or as a standard method ``@device.setup`` for marking functions to a specific ``Device`` instance.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept and return python literals.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self.setup`` with same name as ``f``.
            Defaults to ``True``.
        record: bool
            Each invocation of the executer is recorded for playback upon reconnect.
            Defaults to ``True``.
        autoinit: bool
            Automatically invokes decorated functions at the end of object ``__init__``.
            Methods will be executed in order-registered.
            Defaults to ``False``.
        ignore_errors: bool
            Discard any device-side uncaught exception.
            Defaults to ``False``.
        implementation: str
            If supplied, the provided method will **only** be used if the board's implementation **name** matches.
            Several methods of the same name can be overloaded that support different implementations.
            Common values include "micropython", and "circuitpython".
            Defaults to an empty string, which **all** implementations will match to.
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.setup, autoinit=autoinit, implementation=implementation, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        if signature(f).parameters and autoinit:
            raise ValueError(f"Method {f} decorated with @Device.setup(autoinit=True) must have no arguments.")

        f.__belay__ = MethodMetadata(
            executer=SetupExecuter,
            autoinit=autoinit,
            implementation=implementation,
            kwargs=kwargs,
        )
        return f

    @overload
    @staticmethod
    def teardown(f: Callable[P, R]) -> Callable[P, R]: ...

    @overload
    @staticmethod
    def teardown(*, implementation: str = "", **kwargs) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    @staticmethod
    def teardown(
        f: Optional[Callable[P, R]] = None, implementation: str = "", **kwargs
    ) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
        """Executes decorated function's body in a global-context on-device when ``device.close()`` is called.

        Function arguments are also set in the global context.

        Can either be used as a staticmethod ``@Device.teardown`` for marking methods in a subclass of ``Device``, or as a standard method ``@device.teardown`` for marking functions to a specific ``Device`` instance.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept and return python literals.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self.teardown`` with same name as ``f``.
            Defaults to ``True``.
        record: bool
            Each invocation of the executer is recorded for playback upon reconnect.
            Defaults to ``True``.
        ignore_errors: bool
            Discard any device-side uncaught exception.
            Defaults to ``False``.
        implementation: str
            If supplied, the provided method will **only** be used if the board's implementation **name** matches.
            Several methods of the same name can be overloaded that support different implementations.
            Common values include "micropython", and "circuitpython".
            Defaults to an empty string, which **all** implementations will match to.
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.teardown, implementation=implementation, **kwargs)  # type: ignore[reportGeneralTypeIssues]

        if signature(f).parameters:
            raise ValueError(f'Method {f} decorated with "@Device.teardown" must have no arguments.')

        f.__belay__ = MethodMetadata(executer=TeardownExecuter, implementation=implementation, kwargs=kwargs)
        return f

    @overload
    @staticmethod
    def task(f: Callable[P, R]) -> Callable[P, R]: ...

    @overload
    @staticmethod
    def task(*, implementation: str = "", **kwargs) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    @staticmethod
    def task(
        f: Optional[Callable[P, R]] = None, implementation: str = "", **kwargs
    ) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
        """Execute decorated function on-device.

        Sends source code to device at decoration time.
        Execution sends involves much smaller overhead.

        Can either be used as a staticmethod ``@Device.task`` for marking methods in a subclass of ``Device``, or as a standard method ``@device.task`` for marking functions to a specific ``Device`` instance.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept and return python literals.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self.task`` with same name as ``f``.
            Defaults to ``True``.
        record: bool
            Each invocation of the executer is recorded for playback upon reconnect.
            Only recommended to be set to ``True`` for a setup-like function.
            Defaults to ``False``.
        implementation: str
            If supplied, the provided method will **only** be used if the board's implementation **name** matches.
            Several methods of the same name can be overloaded that support different implementations.
            Common values include "micropython", and "circuitpython".
            Defaults to an empty string, which **all** implementations will match to.
        trusted: bool
            Fully trust remote device.
            When set to ``False``, only ``[None, bool, bytes, int, float, str, List, Dict, Set]`` return
            values can be parsed.
            When set to ``True``, any value who's ``repr`` can be evaluated to create a python object can be
            returned. However, **this also allows the remote device to execute arbitrary code on host**.
            Defaults to ``False``.
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.task, implementation=implementation, **kwargs)  # type: ignore[reportGeneralTypeIssues]

        f.__belay__ = MethodMetadata(executer=TaskExecuter, implementation=implementation, kwargs=kwargs)
        return f

    @overload
    @staticmethod
    def thread(f: Callable[P, R]) -> Callable[P, R]: ...

    @overload
    @staticmethod
    def thread(*, implementation: str = "", **kwargs) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    @staticmethod
    def thread(
        f: Optional[Callable[P, R]] = None, implementation: str = "", **kwargs
    ) -> Union[Callable[[Callable[P, R]], Callable[P, R]], Callable[P, R]]:
        """Spawn on-device thread that executes decorated function.

        Can either be used as a staticmethod ``@Device.thread`` for marking methods in a subclass of ``Device``, or as a standard method ``@device.thread`` for marking functions to a specific ``Device`` instance.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept python literals as arguments.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self.thread`` with same name as ``f``.
            Defaults to ``True``.
        record: bool
            Each invocation of the executer is recorded for playback upon reconnect.
            Defaults to ``True``.
        implementation: str
            If supplied, the provided method will **only** be used if the board's implementation **name** matches.
            Several methods of the same name can be overloaded that support different implementations.
            Common values include "micropython", and "circuitpython".
            Defaults to an empty string, which **all** implementations will match to.
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.task, implementation=implementation, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        f.__belay__ = MethodMetadata(executer=ThreadExecuter, implementation=implementation, kwargs=kwargs)
        return f

    def terminal(self, *, exit_char=chr(0x1D)):
        """Start a blocking interactive terminal over the serial port."""
        self._board.exit_raw_repl()  # In case we were previously in raw repl mode.
        miniterm = Miniterm(self._board.serial)
        miniterm.set_rx_encoding("UTF-8")
        miniterm.set_tx_encoding("UTF-8")
        miniterm.exit_character = exit_char
        miniterm.start()
        with contextlib.suppress(KeyboardInterrupt):
            miniterm.join(True)
        miniterm.join()

    def soft_reset(self):
        """Reset device, executing ``main.py`` if available."""
        # When in Raw REPL, ctrl-d will perform a reset, but won't execute ``main.py``
        # https://github.com/micropython/micropython/issues/2249
        self._board.exit_raw_repl()
        self._board.read_until(b">>>")
        self._board.ctrl_d()

    def _traceback_execute(
        self,
        src_file: PathType,
        src_lineno: int,
        name: str,
        cmd: str,
        record: bool = True,
        trusted: bool = False,
    ):
        """Invoke ``cmd``, and reinterprets raised stacktrace in ``PyboardException``.

        Parameters
        ----------
        src_file: Union[str, Path]
            Path to the file containing the code of the function that ``cmd`` will execute.
        src_lineno: int
            Line number into ``src_file`` that the function starts.
        name: str
            Name of the function.
        cmd: str
            Python command that executes a function on-device.
        record: bool
            Record the call for state-reconstruction if device is accidentally reset.
            Defaults to ``True``.
        trusted: bool
            Fully trust remote device.
            When set to ``False``, only ``[None, bool, bytes, int, float, str, List, Dict, Set]`` return
            values can be parsed.
            When set to ``True``, any value who's ``repr`` can be evaluated to create a python object can be
            returned. However, **this also allows the remote device to execute arbitrary code on host**.
            Defaults to ``False``.

        Returns
        -------
            Correctly interpreted return value from executing code on-device.
        """
        src_file = str(src_file)

        try:
            res = self(cmd, record=record, trusted=trusted)
        except PyboardException as e:
            new_lines = []

            msg = e.args[0]
            lines = msg.split("\n")
            for line in lines:
                new_lines.append(line)

                try:
                    file, lineno, fn = line.strip().split(",", 2)
                except ValueError:
                    continue

                if file != 'File "<stdin>"' or fn != f" in {name}":
                    continue

                lineno = int(lineno[6:]) - 1 + src_lineno

                new_lines[-1] = f'  File "{src_file}", line {lineno},{fn}'

                # Get what that line actually is.
                new_lines.append("    " + linecache.getline(src_file, lineno).strip())
            new_msg = "\n".join(new_lines)
            e.args = (new_msg,)
            raise
        return res
