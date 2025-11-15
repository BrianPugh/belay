from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Union

from belay.pyboard import PyboardException

if TYPE_CHECKING:
    from belay.device import Device


def _is_magic(name) -> bool:
    return name.startswith("__") and name.endswith("__")


def _resolve_value(value) -> str:
    return get_proxy_object_target_name(value) if isinstance(value, ProxyObject) else repr(value)


@contextmanager
def _promote_exceptions():
    """Context manager that promotes PyboardException to more specific exception types."""
    try:
        yield
    except PyboardException as e:
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
        raise


class ProxyObject:
    r"""Proxy object for interacting with remote MicroPython/CircuitPython objects.

    :class:`ProxyObject` provides a transparent wrapper around remote objects,
    allowing you to interact with them as if they were local Python objects.
    Operations on the proxy are forwarded to the device, and results are automatically
    retrieved and wrapped as needed.

    .. note::
       ProxyObjects are typically created using :meth:`Device.proxy` rather than
       instantiating this class directly. The :meth:`Device.proxy` method provides
       convenient automatic detection of imports and expressions.

    Return Value Behavior
    ---------------------
    When accessing proxy attributes or calling methods:
        - **Immutable types** (int, float, str, bool, None, bytes) are returned **directly**
        - **Mutable types** (list, dict, custom objects) are returned as :class:`ProxyObject`

    Examples
    --------
    Basic attribute and method access::

        # Create a remote sensor object
        device("sensor = TemperatureSensor()")

        # Create proxy to interact with it
        sensor = device.proxy("sensor")

        # Access attributes - immutable values returned directly
        temp = sensor.temperature  # Returns actual float
        print(f"Temperature: {temp}°C")

        # Call methods
        sensor.calibrate()  # Calls "sensor.calibrate()" on the micropython device.
        sensor.set_threshold(25.0)

    Working with collections::

        # Create remote list
        device("data = [1, 2, 3, 4, 5]")
        data_proxy = device.proxy("data")

        # Access elements - immutable ints returned directly
        print(data_proxy[0])  # 1
        print(data_proxy[-1])  # 5

        # Slice - returns ProxyObject wrapping the slice
        subset = data_proxy[1:3]  # ProxyObject for [2, 3]

        # Modify elements
        data_proxy[0] = 100
        print(device("data"))  # [100, 2, 3, 4, 5]

        # Iterate
        for item in data_proxy:
            print(item)

    Importing and using modules::

        # Import module
        machine = device.proxy("import machine")

        # Use imported module
        pin = machine.Pin(25, machine.Pin.OUT)
        pin.on()

    Nested object access::

        # Create nested structure
        device(\"\"\"
        class Config:
            def __init__(self):
                self.settings = {'brightness': 10, 'mode': 'auto'}
        config = Config()
        \"\"\")

        # Access nested objects
        config = device.proxy("config")
        settings = config.settings  # Returns ProxyObject for dict
        brightness = settings['brightness']  # Returns 10 (int)

        # Modify nested values
        settings['brightness'] = 20

    See Also
    --------
    Device.proxy : Recommended method for creating ProxyObjects
    Device.__call__ : Lower-level method for executing code with proxy support
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
        with _promote_exceptions():
            return device(full_name, proxy=True, delete=True)

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

        # Resolve ProxyObject values to their remote target names
        value_repr = _resolve_value(value)
        device(f"{target_name}.{name} = {value_repr}")

    def __getitem__(self, key):
        """Get item from remote object by key or index.

        Supports indexing (``proxy[0]``) and slicing (``proxy[1:3]``).
        Returns immutable values directly, mutable values as :class:`ProxyObject`.
        """
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)

        # Handle slice objects specially since MicroPython doesn't support slice() constructor
        if isinstance(key, slice):
            start = "" if key.start is None else str(key.start)
            stop = "" if key.stop is None else str(key.stop)
            step = "" if key.step is None else f":{key.step}"
            expression = f"{target_name}[{start}:{stop}{step}]"
        else:
            # Resolve ProxyObject keys to their remote target names
            key_repr = _resolve_value(key)
            expression = f"{target_name}[{key_repr}]"

        with _promote_exceptions():
            return device(expression, proxy=True, delete=True)

    def __setitem__(self, key, value):
        """Set item in remote object by key or index.

        Supports setting list elements (``proxy[0] = value``) and dict keys (``proxy['key'] = value``).
        """
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)

        # Resolve ProxyObject keys and values to their remote target names
        key_repr = _resolve_value(key)
        value_repr = _resolve_value(value)

        expression = f"{target_name}[{key_repr}]={value_repr}"
        with _promote_exceptions():
            device(expression)

    def __len__(self) -> int:
        """Return the length of the remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        expression = f"len({target_name})"
        with _promote_exceptions():
            return device(expression)  # Do not proxy; we want the integer value.

    def __del__(self):
        """Delete reference to micropython object."""
        delete = object.__getattribute__(self, "_belay_delete")
        if not delete:
            return
        device = object.__getattribute__(self, "_belay_device")
        target_name = object.__getattribute__(self, "_belay_target_name")
        cmd = f"del {target_name}"
        with suppress(Exception):
            device(cmd)

    def __str__(self):
        """String representation of remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        with _promote_exceptions():
            return device(f"str({target_name})")

    def __repr__(self):
        """Return repr showing this is a ProxyObject wrapping a remote object.

        Format: ``<ProxyObject {remote_repr}>`` where ``remote_repr`` is the
        representation of the remote object.
        """
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        remote_repr = device(f"repr({target_name})")
        with _promote_exceptions():
            return f"<{type(self).__name__} {remote_repr}>"

    def __contains__(self, item):
        """Test membership in remote object.

        Supports the ``in`` operator: ``item in proxy``.
        Works with lists, dicts, tuples, sets, and other containers.
        """
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        item_repr = _resolve_value(item)
        expression = f"{item_repr} in {target_name}"
        with _promote_exceptions():
            res = device(expression)
        return res

    def __eq__(self, other):
        """Equality comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} == {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __ne__(self, other):
        """Inequality comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} != {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __lt__(self, other):
        """Less than comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} < {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __le__(self, other):
        """Less than or equal comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} <= {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __gt__(self, other):
        """Greater than comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} > {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __ge__(self, other):
        """Greater than or equal comparison with remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        other_repr = _resolve_value(other)
        expression = f"{target_name} >= {other_repr}"
        with _promote_exceptions():
            return device(expression)

    def __iter__(self):
        """Return an iterator over the remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        # Convert the remote iterable to a list and return its iterator
        with _promote_exceptions():
            result = device(f"list({target_name})")
        return iter(result)

    def __hash__(self):
        """Return hash of the remote object."""
        device = object.__getattribute__(self, "_belay_device")
        target_name = get_proxy_object_target_name(self)
        with _promote_exceptions():
            return device(f"hash({target_name})")

    def __call__(self, *args, **kwargs):
        """Call the remote object as a function or method.

        Supports calling remote functions/methods with arguments.
        ProxyObject arguments are automatically resolved to their remote equivalents.
        Returns immutable values directly, mutable values as :class:`ProxyObject`.

        Note: Generator functions are not fully supported yet.
        """
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

        with _promote_exceptions():
            return device(cmd, proxy=True)


def get_proxy_object_target_name(proxy_object: ProxyObject) -> str:
    target_name = object.__getattribute__(proxy_object, "_belay_target_name")
    return target_name
