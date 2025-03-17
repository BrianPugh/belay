from typing import TYPE_CHECKING

from belay.pyboard import PyboardException

if TYPE_CHECKING:
    from belay.device import Device


def _is_magic(name) -> bool:
    return name.startswith("__") and name.endswith("__")


class ProxyObject:
    """Proxy object for interacting/mimicking a remote micropython object.

    If subclassing :class:`ProxyObject`:

    1. Be sure to call ``super().__init__(device, name)`` first.
    2. Use ``object.__setattr__(self, "some_attribute_name", value)`` to create/set a local attribute.
       Attributes created this way will *only* be stored locally in CPython and will not interact
       with the micropython board. Subsequent writes to this attribute can be done "normally"
       (without ``object.__setattr__``).
    """

    def __init__(self, device: "Device", name: str):
        """Create a :class:`ProxyObject`.

        Parameters
        ----------
        device: belay.Device
            Belay :class:`Device` object for interacting with the micropython board.
        name: str
            Name of the remote object for the proxy-object to interact with.
        """
        object.__setattr__(self, "_belay_device", device)
        object.__setattr__(self, "_belay_target_name", name)

    def __getattribute__(self, name):
        device = object.__getattribute__(self, "_belay_device")
        target_obj = object.__getattribute__(self, "_belay_target_name")

        if not _is_magic(name):
            # If it's not a magic-method, try to see if
            # this class directly has the attribute.
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                pass

        full_name = f"{target_obj}.{name}"
        try:
            return device(full_name)
        except SyntaxError:
            # It could be a method; create another proxy object
            return type(self)(device, full_name)
        except PyboardException as e:
            # semi-jank way of promoting to an AttributeError
            if "AttributeError: " in e.args[0]:
                raise AttributeError from e
            raise

    def __setattr__(self, name, value):
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")

        if not _is_magic(name):
            # If it's not a magic-method, try to see if
            # this class directly has the attribute.
            try:
                object.__getattribute__(self, name)
            except AttributeError:
                pass
            else:
                object.__setattr__(self, name, value)
                return

        device(f"{target_name}.{name} = {value!r}")

    def __getitem__(self, key):
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        expression = f"{target_name}[{key!r}]"
        try:
            return device(expression)
        except SyntaxError:
            # It could be a method; create another proxy object
            return type(self)(device, expression)

    def __len__(self) -> int:
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        expression = f"len({target_name})"
        return device(expression)

    def __call__(self, *args, **kwargs):
        # TODO: this won't handle generators properly
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        cmd = f"{target_name}(*{args!r}, **{kwargs!r})"
        return device(cmd)
