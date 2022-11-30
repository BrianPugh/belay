import ast
import concurrent.futures
import linecache
import re
import subprocess  # nosec
import sys
import tempfile
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from typing import Callable, Optional, TextIO, Tuple, Union

from autoregistry import Registry
from pathspec import PathSpec
from serial import SerialException

from ._minify import minify as minify_code
from .exceptions import ConnectionLost, MaxHistoryLengthError
from .executers import Executer, SetupExecuter, TaskExecuter, ThreadExecuter
from .hash import fnv1a
from .helpers import read_snippet, wraps_partial
from .inspect import isexpression
from .pyboard import Pyboard, PyboardError, PyboardException
from .typing import BelayReturn
from .webrepl import WebreplToSerial


class NotBelayResponse(Exception):
    """Parsed response wasn't for Belay."""


def _parse_belay_response(line):
    if not line.startswith("_BELAY"):
        raise NotBelayResponse
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


def _discover_files_dirs(
    remote_dir: str,
    local_file_or_folder: Path,
    ignore: Optional[list] = None,
):
    src_objects = []
    if local_file_or_folder.is_dir():
        if ignore is None:
            ignore = []
        ignore_spec = PathSpec.from_lines("gitwildmatch", ignore)
        for src_object in local_file_or_folder.rglob("*"):
            if ignore_spec.match_file(str(src_object)):
                continue
            src_objects.append(src_object)
        # Sort so that folder creation comes before file sending.
        src_objects.sort()

        src_files, src_dirs = [], []
        for src_object in src_objects:
            if src_object.is_dir():
                src_dirs.append(src_object)
            else:
                src_files.append(src_object)
        dst_files = [
            remote_dir / src.relative_to(local_file_or_folder) for src in src_files
        ]
    else:
        src_files = [local_file_or_folder]
        src_dirs = []
        dst_files = [Path(remote_dir) / local_file_or_folder.name]

    return src_files, src_dirs, dst_files


def _preprocess_keep(
    keep: Union[None, list, str, bool],
    dst: str,
) -> list:
    if keep is None:
        if dst == "/":
            keep = ["boot.py", "webrepl_cfg.py", "lib"]
        else:
            keep = []
    elif isinstance(keep, str):
        keep = [keep]
    elif isinstance(keep, (list, tuple)):
        pass
    elif isinstance(keep, bool):
        keep = []
    else:
        raise ValueError
    keep = [str(dst / Path(x)) for x in keep]
    return keep


def _preprocess_ignore(ignore: Union[None, str, list, tuple]) -> list:
    if ignore is None:
        ignore = ["*.pyc", "__pycache__", ".DS_Store", ".pytest_cache"]
    elif isinstance(ignore, str):
        ignore = [ignore]
    elif isinstance(ignore, (list, tuple)):
        ignore = list(ignore)
    else:
        raise ValueError
    return ignore


def _preprocess_src_file(
    tmp_dir: Union[str, Path],
    src_file: Union[str, Path],
    minify: bool,
    mpy_cross_binary: Union[str, Path, None],
) -> Path:
    tmp_dir = Path(tmp_dir)
    src_file = Path(src_file)

    if src_file.is_absolute():
        transformed = tmp_dir / src_file.relative_to(tmp_dir.anchor)
    else:
        transformed = tmp_dir / src_file
    transformed.parent.mkdir(parents=True, exist_ok=True)

    if src_file.suffix == ".py":
        if mpy_cross_binary:
            transformed = transformed.with_suffix(".mpy")
            subprocess.check_output(  # nosec
                [mpy_cross_binary, "-o", transformed, src_file]
            )
            return transformed
        elif minify:
            minified = minify_code(src_file.read_text())
            transformed.write_text(minified)
            return transformed

    return src_file


def _preprocess_src_file_hash(*args, **kwargs):
    src_file = _preprocess_src_file(*args, **kwargs)
    src_hash = fnv1a(src_file)
    return src_file, src_hash


def _generate_dst_dirs(dst, src, src_dirs) -> list:
    dst_dirs = [str(dst / x.relative_to(src)) for x in src_dirs]
    # Add all directories leading up to ``dst``.
    dst_prefix_tokens = dst.split("/")
    for i in range(2, len(dst_prefix_tokens) + (dst[-1] != "/")):
        dst_dirs.append("/".join(dst_prefix_tokens[:i]))
    dst_dirs.sort()
    return dst_dirs


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
    platform: str
        Board identifier. May not be consistent from MicroPython to CircuitPython.
        e.g. The Pi Pico is "rp2" in MicroPython, but "RP2040"  in CircuitPython.
    emitters: tuple[str]
        Tuple of available emitters on-device ``{"native", "viper"}``.
    """

    name: str
    version: Tuple[int, int, int]
    platform: str
    emitters: Tuple[str]


@dataclass
class MethodMetadata:
    executer: Callable
    kwargs: dict


class Device(Registry):
    """Belay interface into a micropython device.

    Attributes
    ----------
    implementation: Implementation
        Implementation details of device.
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

        for executer_name, executer_cls in Executer.items():
            setattr(self, executer_name, executer_cls(self))

        self._exec_snippet("startup")

        self.implementation = Implementation(
            *self(
                "(sys.implementation.name, sys.implementation.version, sys.platform)"
            ),
            emitters=self._emitter_check(),
        )

        if startup is None:
            if self.implementation.name == "circuitpython":
                self._exec_snippet("convenience_imports_circuitpython")
            else:
                self._exec_snippet("convenience_imports_micropython")
        elif startup:
            self(startup)

        # if subclassing Device, register methods decorated with
        # ``@Device.task`` and ``@Device.thread``.
        for name, method in vars(type(self)).items():
            metadata = getattr(method, "__belay__", None)
            if not metadata:
                continue
            executer = getattr(self, metadata.executer.__registry__.name)
            setattr(
                self,
                name,
                executer(method, **metadata.kwargs),
            )

    def _emitter_check(self):
        # Detect which emitters are available
        emitters = []
        try:
            self._exec_snippet("emitter_check")
        except PyboardException as e:
            if "invalid micropython decorator" not in str(e):
                raise e
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
                    raise Exception(f"Unknown emitter line {line_e}.")
        else:
            emitters.append("native")
            emitters.append("viper")
            self("del __belay_emitter_test")

        return tuple(emitters)

    def _connect_to_board(self, **kwargs):
        self._board = Pyboard(**kwargs)
        if isinstance(self._board.serial, WebreplToSerial):
            soft_reset = False
        else:
            soft_reset = True
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
        cmd: str,
        *,
        minify: bool = True,
        stream_out: TextIO = sys.stdout,
        record=True,
    ):
        """Execute code on-device.

        Parameters
        ----------
        cmd: str
            Python code to execute. May be a statement or expression.
        minify: bool
            Minify ``cmd`` code prior to sending.
            Reduces the number of characters that need to be transmitted.
            Defaults to ``True``.
        record: bool
            Record the call for state-reconstruction if device is accidentally reset.
            Defaults to ``True``.

        Returns
        -------
            Correctly interpreted return value from executing code on-device.
        """
        if minify:
            cmd = minify_code(cmd)

        if isexpression(cmd):
            cmd = f"print('_BELAYR' + repr({cmd}))"

        if (
            record
            and self.attempts
            and len(self._cmd_history) < self.MAX_CMD_HISTORY_LEN
        ):
            self._cmd_history.append(cmd)

        out = None
        data_consumer_buffer = []

        def data_consumer(data):
            """Handle input data stream immediately."""
            nonlocal out
            if data == b"\x04":
                return
            data_consumer_buffer.append(data.decode())
            if b"\n" in data:
                line = "".join(data_consumer_buffer)
                data_consumer_buffer.clear()

                try:
                    out = _parse_belay_response(line)
                except NotBelayResponse:
                    if stream_out:
                        stream_out.write(line)

        try:
            self._board.exec(cmd, data_consumer=data_consumer)
        except (SerialException, ConnectionResetError):
            # Board probably disconnected.
            if self.attempts:
                self.reconnect()
                self._board.exec(cmd, data_consumer=data_consumer_buffer)
            else:
                raise ConnectionLost

        return out

    def sync(
        self,
        folder: Union[str, Path],
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

        # Create a list of all files and dirs (on-device).
        # This is so we know what to clean up after done syncing.
        snippets_to_execute = []

        if progress_update:
            progress_update(description="Bootstrapping sync...")
        if "viper" in self.implementation.emitters:
            snippets_to_execute.append("hf_viper")
        elif "native" in self.implementation.emitters:
            snippets_to_execute.append("hf_native")
        else:
            snippets_to_execute.append("hf")

        if self.implementation.name == "circuitpython":
            snippets_to_execute.append("ilistdir_circuitpython")
        else:
            snippets_to_execute.append("ilistdir_micropython")
        snippets_to_execute.append("sync_begin")
        self._exec_snippet(*snippets_to_execute)

        # Remove the keep files from the on-device ``all_files`` set
        # so they don't get deleted.
        keep_all = folder.is_file() or keep is True
        keep = _preprocess_keep(keep, dst)
        ignore = _preprocess_ignore(ignore)

        src_files, src_dirs, dst_files = _discover_files_dirs(dst, folder, ignore)

        if mpy_cross_binary:
            dst_files = [
                dst_file.with_suffix(".mpy") if dst_file.suffix == ".py" else dst_file
                for dst_file in dst_files
            ]
        dst_files = [str(dst_file) for dst_file in dst_files]
        dst_dirs = _generate_dst_dirs(dst, folder, src_dirs)

        if keep_all:
            self("del __belay_del_fs")
        else:
            self(
                f"__belay_del_fs({repr(dst)}, {repr(set(keep + dst_files))}); del __belay_del_fs"
            )

        # Try and make all remote dirs
        if dst_dirs:
            if progress_update:
                progress_update(description="Creating remote directories...")
            self(f"__belay_mkdirs({repr(dst_dirs)})")

        with tempfile.TemporaryDirectory() as tmp_dir, concurrent.futures.ThreadPoolExecutor() as executor:
            tmp_dir = Path(tmp_dir)

            def _preprocess_src_file_hash_helper(src_file):
                return _preprocess_src_file_hash(
                    tmp_dir, src_file, minify, mpy_cross_binary
                )

            src_files_and_hashes = executor.map(
                _preprocess_src_file_hash_helper, src_files
            )

            # Get all remote hashes
            if progress_update:
                progress_update(description="Fetching remote hashes...")
            dst_hashes = self(f"__belay_hfs({repr(dst_files)})")

            if len(dst_hashes) != len(dst_files):
                raise Exception

            puts = []
            for (src_file, src_hash), dst_file, dst_hash in zip(
                src_files_and_hashes, dst_files, dst_hashes
            ):
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

        # Remove all the files and directories that did not exist in local filesystem.
        if progress_update:
            progress_update(description="Cleaning up...")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def close(self) -> None:
        """Close the connection to device."""
        return self._board.close()

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

    @staticmethod
    def setup(f=None, **kwargs) -> Callable:
        """setup(f, *, minify=True, register=True, record=True)

        Decorator that executes function's body in a global-context on-device when called.

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
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.setup, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        f.__belay__ = MethodMetadata(executer=SetupExecuter, kwargs=kwargs)
        return f

    @staticmethod
    def task(f=None, **kwargs) -> Callable:
        """task(f, *, minify=True, register=True, record=False)

        Decorator that send code to device that executes when decorated function is called on-host.

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
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.task, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        f.__belay__ = MethodMetadata(executer=TaskExecuter, kwargs=kwargs)
        return f

    @staticmethod
    def thread(f=None, **kwargs) -> Callable:
        """thread(f, *, minify=True, register=True, record=True)

        Decorator that send code to device that spawns a thread when executed.

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
        """  # noqa: D400
        if f is None:
            return wraps_partial(Device.task, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        f.__belay__ = MethodMetadata(executer=ThreadExecuter, kwargs=kwargs)
        return f

    def _traceback_execute(
        self,
        src_file: Union[str, Path],
        src_lineno: int,
        name: str,
        cmd: str,
        record: bool = True,
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

        Returns
        -------
            Correctly interpreted return value from executing code on-device.
        """
        src_file = str(src_file)

        try:
            res = self(cmd, record=record)
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
