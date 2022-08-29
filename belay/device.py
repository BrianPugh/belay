import ast
import importlib.resources as pkg_resources
import linecache
import secrets
import string
import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache, wraps
from inspect import isgeneratorfunction
from pathlib import Path
from typing import Callable, Dict, Generator, List, Optional, Set, TextIO, Tuple, Union

from . import snippets
from ._minify import minify as minify_code
from .exceptions import FeatureUnavailableError, SpecialFunctionNameError
from .inspect import getsource
from .pyboard import Pyboard, PyboardException
from .webrepl import WebreplToSerial

# Typing
PythonLiteral = Union[None, bool, bytes, int, float, str, List, Dict, Set]
BelayGenerator = Generator[PythonLiteral, None, None]
BelayReturn = Union[BelayGenerator, PythonLiteral]
BelayCallable = Callable[..., BelayReturn]


_python_identifier_chars = (
    string.ascii_uppercase + string.ascii_lowercase + string.digits
)


@lru_cache
def _read_snippet(name):
    return pkg_resources.read_text(snippets, f"{name}.py")


def _local_hash_file(fn: str) -> int:
    """Compute the FNV-1a 64-bit hash of a file."""
    h = 0xCBF29CE484222325
    size = 1 << 64
    with open(fn, "rb") as f:  # noqa: PL123
        while True:
            data = f.read(65536)
            if not data:
                break
            for byte in data:
                h = h ^ byte
                h = (h * 0x100000001B3) % size
    return h


def _random_python_identifier(n=16):
    return "_" + "".join(secrets.choice(_python_identifier_chars) for _ in range(n))


class _Executer(ABC):
    def __init__(self, device):
        # To avoid Executer.__setattr__ raising an error
        object.__setattr__(self, "_belay_device", device)

    def __setattr__(self, name: str, value: BelayCallable):
        if (
            name.startswith("_belay")
            or name.startswith("__belay")
            or (name.startswith("__") and name.endswith("__"))
        ):
            raise SpecialFunctionNameError(
                f'Not allowed to register function named "{name}".'
            )
        super().__setattr__(name, value)

    def __getattr__(self, name: str) -> BelayCallable:
        # Just here for linting purposes.
        raise AttributeError

    @abstractmethod
    def __call__(self):
        raise NotImplementedError


class _TaskExecuter(_Executer):
    def __call__(
        self,
        f: Optional[BelayCallable] = None,
        /,
        minify: bool = True,
        register: bool = True,
    ) -> BelayCallable:
        """Decorator that send code to device that executes when decorated function is called on-host.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept and return python literals.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self`` with same name as ``f``.
            Defaults to ``True``.

        Returns
        -------
        Callable
            Remote-executor function.
        """
        if f is None:
            return self  # type: ignore

        name = f.__name__
        src_code, src_lineno, src_file = getsource(f)
        src_lineno -= 1  # Because of the injected ``@__belay`` decorator below

        # Add the __belay decorator for handling result serialization.
        src_code = f"@__belay({repr(name)})\n" + src_code

        # Send the source code over to the device.
        self._belay_device(src_code, minify=minify)

        @wraps(f)
        def func_executer(*args, **kwargs):
            cmd = f"_belay_{name}(*{repr(args)}, **{repr(kwargs)})"

            return self._belay_device._traceback_execute(
                src_file, src_lineno, name, cmd
            )

        @wraps(f)
        def multi_func_executer(*args, **kwargs):
            res = func_executer(*args, **kwargs)
            if hasattr(f, "_belay_level"):
                # Call next device's wrapper.
                if f._belay_level == 1:
                    res = [f(*args, **kwargs), res]
                else:
                    res = [*f(*args, **kwargs), res]

            return res

        multi_func_executer._belay_level = 1
        if hasattr(f, "_belay_level"):
            multi_func_executer._belay_level += f._belay_level

        @wraps(f)
        def gen_executer(*args, **kwargs):
            # Step 1: Create the on-device generator
            gen_identifier = _random_python_identifier()
            cmd = f"{gen_identifier} = _belay_{name}(*{repr(args)}, **{repr(kwargs)})"
            self._belay_device._traceback_execute(src_file, src_lineno, name, cmd)
            # Step 2: Create the host generator that invokes ``next()`` on-device.
            cmd = f"__belay_gen_next({gen_identifier})"

            def gen_inner():
                try:
                    while True:
                        yield self._belay_device._traceback_execute(
                            src_file, src_lineno, name, cmd
                        )
                except StopIteration:
                    pass
                # Delete the exhausted generator on-device.
                self._belay_device(f"del {gen_identifier}")

            return gen_inner()

        @wraps(f)
        def multi_gen_executer(*args, **kwargs):
            raise NotImplementedError

        multi_gen_executer._belay_level = 1
        if hasattr(f, "_belay_level"):
            multi_gen_executer._belay_level += f._belay_level

        if isgeneratorfunction(f):
            executer = gen_executer

            # TODO: define multi_gen_executer
            if multi_gen_executer._belay_level > 1:
                raise NotImplementedError(
                    "Multi-device generator task decorating not yet implemented."
                )
        else:
            executer = multi_func_executer

        if register:
            setattr(self, name, executer)

        return executer


class _ThreadExecuter(_Executer):
    def __call__(
        self,
        f: Optional[Callable[..., None]] = None,
        /,
        minify: bool = True,
        register: bool = True,
    ) -> Callable[..., None]:
        """Decorator that send code to device that spawns a thread when executed.

        Parameters
        ----------
        f: Callable
            Function to decorate. Can only accept python literals as arguments.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Defaults to ``True``.
        register: bool
            Assign an attribute to ``self`` with same name as ``f``.
            Defaults to ``True``.

        Returns
        -------
        Callable
            Remote-executor function.
        """
        if f is None:
            return self  # type: ignore

        if self._belay_device.implementation.name == "circuitpython":
            raise FeatureUnavailableError("CircuitPython does not support threading.")

        name = f.__name__
        src_code, src_lineno, src_file = getsource(f)

        # Send the source code over to the device.
        self._belay_device(src_code, minify=minify)

        @wraps(f)
        def executer(*args, **kwargs):
            cmd = f"import _thread; _thread.start_new_thread({name}, {repr(args)}, {repr(kwargs)})"
            self._belay_device._traceback_execute(src_file, src_lineno, name, cmd)

        @wraps(f)
        def multi_executer(*args, **kwargs):
            res = executer(*args, **kwargs)
            if hasattr(f, "_belay_level"):
                # Call next device's wrapper.
                if f._belay_level == 1:
                    res = [f(*args, **kwargs), res]
                else:
                    res = [*f(*args, **kwargs), res]

            return res

        multi_executer._belay_level = 1
        if hasattr(f, "_belay_level"):
            multi_executer._belay_level += f._belay_level

        if register:
            setattr(self, name, executer)

        return multi_executer


@dataclass
class Implementation:
    """Implementation dataclass detailing the device.

    Parameters
    ----------
    name: str
        Type of python running on device.
        One of ``{"micropython", "circuitpython"}``.
    version: Tuple[int, int, int]
        ``(major, minor, patch)`` Semantic versioning of device's firmware.
    """

    name: str
    version: Tuple[int, int, int]


class Device:
    """Belay interface into a micropython device.

    Attributes
    ----------
    implementation: Implementation
        Implementation details of device.
    """

    def __init__(
        self,
        *args,
        startup: Optional[str] = None,
        **kwargs,
    ):
        """Create a MicroPython device.

        Parameters
        ----------
        startup: str
            Code to run on startup. Defaults to a few common imports.
        """
        self._board = Pyboard(*args, **kwargs)
        if isinstance(self._board.serial, WebreplToSerial):
            soft_reset = False
        else:
            soft_reset = True
        self._board.enter_raw_repl(soft_reset=soft_reset)

        self.task = _TaskExecuter(self)
        self.thread = _ThreadExecuter(self)

        self._exec_snippet("startup")

        self.implementation = Implementation(
            *self(
                'print("_BELAYR("'
                '+ repr(sys.implementation.name) + ","'
                "+ repr(sys.implementation.version)"
                '+")")'
            )
        )

        if startup is None:
            if self.implementation.name == "circuitpython":
                self._exec_snippet("convenience_imports_circuitpython")
            else:
                self._exec_snippet("convenience_imports_micropython")
        elif startup:
            self(startup)

    def _exec_snippet(self, *names: str) -> BelayReturn:
        """Load and execute a snippet from the snippets sub-package.

        Parameters
        ----------
        names : str
            Snippet(s) to load and execute.
        """
        snippets = [_read_snippet(name) for name in names]
        return self("\n".join(snippets))

    def __call__(
        self,
        cmd: str,
        minify: bool = True,
        stream_out: TextIO = sys.stdout,
    ) -> BelayReturn:
        """Execute code on-device.

        Parameters
        ----------
        cmd: str
            Python code to execute.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Reduces the number of characters that need to be transmitted.
            Defaults to ``True``.

        Returns
        -------
            Return value from executing code on-device.
        """
        if minify:
            cmd = minify_code(cmd)

        res = self._board.exec(cmd).decode()

        lines = res.split("\r\n")

        for line in lines[:-1]:
            if line.startswith("_BELAY"):
                line = line[6:]
                code, line = line[0], line[1:]

                if code == "R":
                    # Result
                    return ast.literal_eval(line)
                elif code == "S":
                    # StopIteration
                    raise StopIteration
                else:
                    raise ValueError(f'Received unknown code: "{code}"')

            if stream_out:
                stream_out.write(line)
                stream_out.write("\n")

    def sync(
        self,
        folder: Union[str, Path],
        minify: bool = True,
        keep: Union[None, list, str] = None,
        progress_update=None,
    ) -> None:
        """Sync a local directory to the root of remote filesystem.

        For each local file, check the remote file's hash, and transfer if they differ.
        If a file/folder exists on the remote filesystem that doesn't exist in the local
        folder, then delete it.

        Parameters
        ----------
        folder: str, Path
            Directory of files to sync to the root of the board's filesystem.
        minify: bool
            Minify python files prior to syncing.
            Defaults to ``True``.
        keep: str or list
            Do NOT delete these file(s) on-device if not present in ``folder``.
            Defaults to ``["boot.py", "webrepl_cfg.py"]``.
        progress:
            Partial for ``rich.progress.Progress.update(task_id,...)`` to update with sync status.
        """
        folder = Path(folder).resolve()

        if not folder.exists():
            raise ValueError(f'"{folder}" does not exist.')
        if not folder.is_dir():
            raise ValueError(f'"{folder}" is not a directory.')

        # Create a list of all files and dirs (on-device).
        # This is so we know what to clean up after done syncing.
        if progress_update:
            progress_update(description="Bootstrapping sync...")
        self._exec_snippet("sync_begin")

        # Remove the keep files from the on-device ``all_files`` set
        # so they don't get deleted.
        if keep is None:
            keep = ["boot.py", "webrepl_cfg.py"]
        elif isinstance(keep, str):
            keep = [keep]
        keep = [x if x[0] == "/" else "/" + x for x in keep]

        # Sort so that folder creation comes before file sending.
        src_objects = sorted(folder.rglob("*"))
        src_files, src_dirs = [], []
        for src_object in src_objects:
            if src_object.is_dir():
                src_dirs.append(src_object)
            else:
                src_files.append(src_object)
        dst_files = [f"/{src.relative_to(folder)}" for src in src_files]
        dst_dirs = [f"/{src.relative_to(folder)}" for src in src_dirs]
        dst_dirs.sort()
        keep = [x for x in keep if x not in dst_files]
        if dst_files + keep:
            self(f"for x in {repr(dst_files + keep)}:\n all_files.discard(x)")

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
            raise Exception

        if progress_update:
            progress_update(total=len(src_files))
        for src, dst, dst_hash in zip(src_files, dst_files, dst_hashes):
            if progress_update:
                progress_update(description=f"Syncing: {dst[1:]}")

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir = Path(tmp_dir)

                if minify and src.suffix == ".py":
                    minified = minify_code(src.read_text())
                    src = tmp_dir / src.name
                    src.write_text(minified)

                # All other files, just sync over.
                src_hash = _local_hash_file(src)
                if src_hash != dst_hash:
                    self._board.fs_put(src, dst)

            if progress_update:
                progress_update(advance=1)

        # Remove all the files and directories that did not exist in local filesystem.
        if progress_update:
            progress_update(description="Cleaning up...")
        self._exec_snippet("sync_end")

    def close(self):
        """Close the connection to device."""
        return self._board.close()

    def _traceback_execute(
        self,
        src_file: Union[str, Path],
        src_lineno: int,
        name: str,
        cmd: str,
    ) -> BelayReturn:
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
        """
        src_file = str(src_file)

        try:
            res = self(cmd)
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
