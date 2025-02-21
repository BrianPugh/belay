from belay.device import Device
from belay.pyboard import PyboardException


class ProxyObject:
    """Proxy object for interacting/mimicking a remote micropythonobject."""

    def __init__(self, device: Device, name: str):
        object.__setattr__(self, "_belay_device", device)
        object.__setattr__(self, "_belay_target_name", name)

    def __getattribute__(self, name):
        device = object.__getattribute__(self, "_belay_device")
        target_obj = object.__getattribute__(self, "_belay_target_name")
        full_name = f"{target_obj}.{name}"
        try:
            return device(full_name)
        except SyntaxError:
            # It could be a method; create another proxy object
            return ProxyObject(device, full_name)
        except PyboardException as e:
            # semi-jank way of promoting to an AttributeError
            if "AttributeError: " in e.args[0]:
                raise AttributeError from e
            raise

    def __setattr__(self, name, value):
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        return device(f"{target_name}.{name} = {value!r}")

    def __call__(self, *args, **kwargs):
        # TODO: this won't handle generators properly
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        cmd = f"{target_name}(*{args!r}, **{kwargs!r})"
        return device(cmd)
