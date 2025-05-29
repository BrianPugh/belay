from typing import TYPE_CHECKING, Union

from belay.pyboard import PyboardException

if TYPE_CHECKING:
    from belay.device import Device


def _is_magic(name) -> bool:
    return name.startswith("__") and name.endswith("__")


def _promote_exception(e: PyboardException):
    # semi-jank way of promoting exceptions
    if "AttributeError: " in e.args[0]:
        raise AttributeError from e
    if "KeyError: " in e.args[0]:
        raise KeyError from e
    if "IndexError: " in e.args[0]:
        raise IndexError from e
    if "ValueError: " in e.args[0]:
        raise ValueError from e
    if "TypeError: " in e.args[0]:
        raise TypeError from e
    raise e


class ProxyObject:
    """Proxy object for interacting/mimicking a remote micropython object.

    If subclassing :class:`ProxyObject`:

    1. Be sure to call ``super().__init__(device, name)`` first.
    2. Use ``object.__setattr__(self, "some_attribute_name", value)`` to create/set a local attribute.
       Attributes created this way will *only* be stored locally in CPython and will not interact
       with the micropython board. Subsequent writes to this attribute can be done "normally"
       (without ``object.__setattr__``).
    """

    def __init__(self, device: "Device", name: str, delete: bool = True):
        """Create a :class:`ProxyObject`.

        Parameters
        ----------
        device: belay.Device
            Belay :class:`Device` object for interacting with the micropython board.
        name: str
            Name of the remote object for the proxy-object to interact with.
        delete: bool
            Delete micropython reference on cpython delete.
        """
        object.__setattr__(self, "_belay_device", device)
        object.__setattr__(self, "_belay_target_name", name)
        object.__setattr__(self, "_belay_delete", delete)

    def __getattribute__(self, name):
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)

        if not _is_magic(name):
            # If it's not a magic-method, try to see if
            # this class directly has the attribute.
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                pass

        full_name = f"{target_name}.{name}"
        try:
            return device(full_name, proxy=True, delete=True)
        except PyboardException as e:
            _promote_exception(e)

    def __setattr__(self, name, value):
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)

        if not _is_magic(name):
            # If it's not a magic-method, try to see if
            # this ProxyObject itself directly has the attribute.
            try:
                object.__getattribute__(self, name)
            except AttributeError:
                pass
            else:
                # Set the local cpython ProxyObject object attribute.
                object.__setattr__(self, name, value)
                return

        device(f"{target_name}.{name} = {value!r}")

    def __getitem__(self, key):
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        expression = f"{target_name}[{key!r}]"
        try:
            return device(expression, proxy=True, delete=True)
        except PyboardException as e:
            _promote_exception(e)

    def __setitem__(self, key, value):
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        expression = f"{target_name}[{key!r}]={value!r}"
        try:
            device(expression)
        except PyboardException as e:
            _promote_exception(e)

    def __len__(self) -> int:
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        expression = f"len({target_name})"
        return device(expression)  # Do not proxy; we want the integer value.

    def __del__(self):
        """Delete reference to micropython object."""
        delete = object.__getattribute__(self, "_belay_delete")
        if not delete:
            return
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        cmd = f"del {target_name}"
        device(cmd)

    def __call__(self, *args, **kwargs):
        # TODO: this won't handle generators properly
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)

        cmd = f"{target_name}("

        # Resolve nested ProxyObjects to their micropython equivalent.
        resolved_args = []
        for arg in args:
            if isinstance(arg, ProxyObject):
                resolved_args.append(get_proxy_object_target_name(arg))
            else:
                resolved_args.append(repr(arg))
        resolved_args = ",".join(resolved_args)
        if resolved_args:
            cmd += f"{resolved_args},"

        resolved_kwargs = []
        for k, v in kwargs.items():
            if isinstance(v, ProxyObject):
                resolved_kwargs.append(f"{k}={get_proxy_object_target_name(v)}")
            else:
                resolved_kwargs.append(f"{k}={v!r}")
        if resolved_kwargs:
            resolved_kwargs = ",".join(resolved_kwargs)
            cmd += f"{resolved_kwargs}"
        cmd = cmd.rstrip(",")
        cmd += ")"

        return device(cmd, proxy=True)


def get_proxy_object_target_name(proxy_object: ProxyObject) -> str:
    target_name = object.__getattribute__(proxy_object, "_belay_target_name")
    return target_name
