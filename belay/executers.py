import inspect
from abc import abstractmethod
from functools import wraps
from typing import Callable, Optional

from autoregistry import Registry

from ._minify import minify as _minify
from .exceptions import FeatureUnavailableError, SpecialFunctionNameError
from .helpers import random_python_identifier, wraps_partial
from .inspect import getsource
from .typing import BelayCallable


class Executer(Registry, suffix="Executer"):
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


class SetupExecuter(Executer):
    def __call__(
        self,
        f: Optional[BelayCallable] = None,
        *,
        minify: bool = True,
        register: bool = True,
        record: bool = True,
    ):
        """See ``Device.setup``."""
        if f is None:
            return wraps_partial(self, minify=minify, register=register, record=record)
        if inspect.isgeneratorfunction(f):
            raise ValueError("@Device.setup does not support generators.")
        name = f.__name__
        src_code, src_lineno, src_file = getsource(f, strip_signature=True)
        if minify:
            src_code = _minify(src_code)
        signature = inspect.signature(f)

        @wraps(f)
        def executer(*args, **kwargs):
            cmd = src_code
            bound_arguments = signature.bind(*args, **kwargs)
            bound_arguments.apply_defaults()
            arg_assign_cmd = "\n".join(
                f"{name}={repr(val)}" for name, val in bound_arguments.arguments.items()
            )
            if arg_assign_cmd:
                cmd = arg_assign_cmd + "\n" + cmd

            return self._belay_device._traceback_execute(
                src_file, src_lineno, name, cmd, record=record
            )

        if register:
            setattr(self, name, executer)

        return executer


class TaskExecuter(Executer):
    def __call__(
        self,
        f: Optional[BelayCallable] = None,
        *,
        minify: bool = True,
        register: bool = True,
        record: bool = False,
    ):
        """See ``Device.task``."""
        if f is None:
            return wraps_partial(self, minify=minify, register=register, record=record)

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
                src_file, src_lineno, name, cmd, record=record
            )

        @wraps(f)
        def gen_executer(*args, **kwargs):
            if record:
                raise NotImplementedError(
                    "Recording of generator tasks is currently not supported."
                )
            # Step 1: Create the on-device generator
            gen_identifier = random_python_identifier()
            cmd = f"{gen_identifier} = _belay_{name}(*{repr(args)}, **{repr(kwargs)})"
            self._belay_device._traceback_execute(
                src_file, src_lineno, name, cmd, record=False
            )
            # Step 2: Create the host generator that invokes ``next()`` on-device.

            def gen_inner():
                send_val = None
                try:
                    while True:
                        cmd = f"__belay_gen_next({gen_identifier}, {repr(send_val)})"
                        send_val = yield self._belay_device._traceback_execute(
                            src_file, src_lineno, name, cmd, record=False
                        )
                except StopIteration:
                    pass
                # Delete the exhausted generator on-device.
                self._belay_device(f"del {gen_identifier}")

            return gen_inner()

        executer = gen_executer if inspect.isgeneratorfunction(f) else func_executer

        if register:
            setattr(self, name, executer)

        return executer


class ThreadExecuter(Executer):
    def __call__(
        self,
        f: Optional[Callable[..., None]] = None,
        *,
        minify: bool = True,
        register: bool = True,
        record: bool = True,
    ) -> Callable[..., None]:
        """See ``Device.thread``."""
        if f is None:
            return wraps_partial(self, minify=minify, register=register, record=record)

        if self._belay_device.implementation.name == "circuitpython":
            raise FeatureUnavailableError("CircuitPython does not support threading.")

        name = f.__name__
        src_code, src_lineno, src_file = getsource(f)

        # Send the source code over to the device.
        self._belay_device(src_code, minify=minify)

        @wraps(f)
        def executer(*args, **kwargs):
            cmd = f"import _thread; _thread.start_new_thread({name}, {repr(args)}, {repr(kwargs)})"
            self._belay_device._traceback_execute(
                src_file, src_lineno, name, cmd, record=record
            )

        if register:
            setattr(self, name, executer)

        return executer
