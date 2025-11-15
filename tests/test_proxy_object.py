from textwrap import dedent

import pytest

from belay import ProxyObject


@pytest.fixture
def proxy_object(emulated_device):
    emulated_device(
        dedent(
            """\
            class Klass:
                foo = 1
                bar = 2
                some_dict = {"a": 1, "b": 2, "c": 3}
                def some_method(self, value):
                    return 2 * value
            klass = Klass()
            """
        )
    )

    obj = ProxyObject(emulated_device, "klass")
    return obj


def test_proxy_object_basic(proxy_object, emulated_device):
    # Immutable values like int are returned directly, not as ProxyObject
    assert proxy_object.foo == 1
    assert proxy_object.bar == 2

    # Methods return immutable values directly
    assert proxy_object.some_method(3) == 6

    # Test that setting attributes updates the remote object
    proxy_object.foo = 4
    assert proxy_object.foo == 4
    # Verify the remote object was actually updated
    assert emulated_device("klass.foo") == 4

    # Test setting a new attribute
    proxy_object.baz = 100
    assert proxy_object.baz == 100
    assert emulated_device("klass.baz") == 100

    with pytest.raises(AttributeError):
        proxy_object.non_existant_attribute  # noqa: B018


def test_proxy_object_dir(proxy_object, emulated_device):
    # dir() returns a ProxyObject wrapping a list, need to resolve it
    result_proxy = emulated_device("dir(klass)", proxy=True)
    result = emulated_device(result_proxy)  # Resolve to actual list
    result = set(result)
    # MicroPython/CircuitPython don't include __init__ and __new__ in dir() of instances
    expected = {"__module__", "__qualname__", "bar", "foo", "some_method", "some_dict"}
    assert expected.issubset(result)


def test_proxy_object_dict_keys(proxy_object, emulated_device):
    # keys() returns a ProxyObject wrapping dict_keys, need to convert to list
    keys_proxy = proxy_object.some_dict.keys()
    # Resolve the proxy object to get the actual keys
    result = emulated_device(keys_proxy)  # This will return the list of keys
    assert {"a", "b", "c"} == set(result)


def test_proxy_object_dict_values(proxy_object, emulated_device):
    # values() returns a ProxyObject wrapping dict_values, need to convert to list
    values_proxy = proxy_object.some_dict.values()
    # dict_values can't be directly parsed, convert to list first
    from belay.proxy_object import get_proxy_object_target_name

    target_name = get_proxy_object_target_name(values_proxy)
    result = emulated_device(f"list({target_name})")
    assert {1, 2, 3} == set(result)


def test_proxy_object_getitem(emulated_device, proxy_object):
    emulated_device("klass.demo_list = [1,2,3]")
    # demo_list is a mutable list, so it's a ProxyObject
    # But we can compare it directly
    assert proxy_object.demo_list == [1, 2, 3]
    # Accessing elements returns immutable ints directly
    assert proxy_object.demo_list[1] == 2
    assert proxy_object.demo_list[-1] == 3
    # Slicing returns a ProxyObject wrapping a list, but comparison still works
    assert proxy_object.demo_list[:2] == [1, 2]

    # Test that __setitem__ updates the remote object
    proxy_object.demo_list[1] = 99
    assert proxy_object.demo_list[1] == 99
    # Verify the remote object was actually updated
    assert emulated_device("klass.demo_list[1]") == 99
    assert emulated_device("klass.demo_list") == [1, 99, 3]

    with pytest.raises(IndexError):
        proxy_object.demo_list[100]


def test_proxy_object_len(emulated_device, proxy_object):
    emulated_device("klass.demo_list = [1,2,3]")
    assert len(proxy_object.demo_list) == 3


def test_proxy_object_subclassing(emulated_device):
    class CustomProxyObject(ProxyObject):
        def __init__(self, device, name):
            super().__init__(device, name)
            object.__setattr__(self, "fizz", 200)

        def foo(self):
            return 100

    obj = CustomProxyObject(emulated_device, "klass")
    assert obj.foo() == 100
    assert obj.fizz == 200

    # Subsequent setting of a set-attribute should work.
    obj.fizz = 300
    assert object.__getattribute__(obj, "fizz") == 300


def test_proxy_object_immutable_ergonomics(proxy_object, emulated_device):
    """Test that immutable values are returned directly for better code ergonomics."""
    # Immutable values should be returned directly, not as ProxyObject
    foo_val = proxy_object.foo
    assert isinstance(foo_val, int)
    assert foo_val == 1

    bar_val = proxy_object.bar
    assert isinstance(bar_val, int)
    assert bar_val == 2

    # Arithmetic should work directly
    assert foo_val + 10 == 11
    assert bar_val * 5 == 10

    # Assignment still works
    proxy_object.foo = 42
    assert proxy_object.foo == 42

    # Mutable objects should still be ProxyObject
    assert isinstance(proxy_object.some_dict, ProxyObject)

    # Test edge case: tuples containing mutable objects
    emulated_device("klass.simple_tuple = (1, 2, 3)")
    emulated_device("klass.nested_tuple = (1, 2, [3, 4])")

    # Currently, tuples are NOT treated as immutable by __belay_obj_create
    # This is intentional to preserve remote mutability for nested content
    simple_tuple = proxy_object.simple_tuple
    nested_tuple = proxy_object.nested_tuple

    # Both should be ProxyObjects to maintain remote connection
    assert isinstance(simple_tuple, ProxyObject)
    assert isinstance(nested_tuple, ProxyObject)

    # We can still compare them
    assert simple_tuple == (1, 2, 3)
    assert nested_tuple == (1, 2, [3, 4])

    # And access elements - nested list should also be a ProxyObject
    assert isinstance(nested_tuple[2], ProxyObject)
    assert nested_tuple[2] == [3, 4]


# ========================================================================================
# Comprehensive New Tests for PR #183
# ========================================================================================


def test_proxy_object_lifecycle_delete_true(emulated_device):
    """Test that ProxyObject with delete=True removes remote reference on deletion."""
    # When proxy() is called on an identifier with delete=True, it creates a proxy
    # pointing directly to that variable. When the proxy is deleted, the variable is deleted.
    emulated_device("test_var = [1, 2, 3]")

    # Create a proxy object with delete=True
    proxy = emulated_device.proxy("test_var", delete=True)
    assert proxy == [1, 2, 3]

    # Verify test_var exists
    assert emulated_device("test_var") == [1, 2, 3]

    # Delete the proxy - this should delete test_var since delete=True
    del proxy

    # Verify test_var was deleted
    with pytest.raises(Exception) as exc_info:
        emulated_device("test_var")
    assert "NameError" in str(exc_info.value)


def test_proxy_object_lifecycle_delete_false(emulated_device):
    """Test that ProxyObject with delete=False preserves remote reference."""
    emulated_device("preserved_var = [4, 5, 6]")

    # Create a proxy object with delete=False
    proxy = emulated_device.proxy("preserved_var", delete=False)
    assert proxy == [4, 5, 6]

    # Delete the proxy
    del proxy

    # Verify the remote variable still exists
    assert emulated_device("preserved_var") == [4, 5, 6]


def test_proxy_object_lifecycle_import_auto_delete_false(emulated_device):
    """Test that import statements automatically set delete=False."""
    # Import creates a ProxyObject with delete=False by default
    sys_proxy = emulated_device.proxy("import sys")

    # Should be able to access sys attributes
    platform_proxy = sys_proxy.platform
    assert isinstance(platform_proxy, (str, ProxyObject))

    # Delete the proxy - sys should still be importable/accessible
    del sys_proxy

    # Verify sys is still accessible
    result = emulated_device('"sys" in dir()')
    assert result is True


def test_proxy_object_magic_method_setitem(emulated_device):
    """Test __setitem__ updates remote list/dict elements."""
    emulated_device("my_list = [10, 20, 30]")
    emulated_device("my_dict = {'a': 1, 'b': 2}")

    list_proxy = emulated_device.proxy("my_list")
    dict_proxy = emulated_device.proxy("my_dict")

    # Test list setitem
    list_proxy[0] = 100
    assert emulated_device("my_list[0]") == 100
    assert emulated_device("my_list") == [100, 20, 30]

    # Test dict setitem
    dict_proxy["a"] = 999
    assert emulated_device("my_dict['a']") == 999
    assert emulated_device("my_dict") == {"a": 999, "b": 2}


def test_proxy_object_magic_method_contains(emulated_device):
    """Test __contains__ for membership testing."""
    emulated_device("my_list = [1, 2, 3, 4, 5]")
    emulated_device("my_dict = {'x': 10, 'y': 20}")

    list_proxy = emulated_device.proxy("my_list")
    dict_proxy = emulated_device.proxy("my_dict")

    # Test list contains
    assert 3 in list_proxy
    assert 10 not in list_proxy

    # Test dict contains (keys)
    assert "x" in dict_proxy
    assert "z" not in dict_proxy


def test_proxy_object_magic_method_iter(emulated_device):
    """Test __iter__ converts remote iterable to local list."""
    emulated_device("my_list = [10, 20, 30]")

    list_proxy = emulated_device.proxy("my_list")

    # Should be able to iterate
    result = list(iter(list_proxy))
    assert result == [10, 20, 30]

    # Can use in for loop
    collected = []
    for item in list_proxy:
        collected.append(item)
    assert collected == [10, 20, 30]


def test_proxy_object_magic_method_hash(emulated_device):
    """Test __hash__ returns hash from remote object."""
    emulated_device("my_tuple = (1, 2, 3)")
    emulated_device("my_str = 'hello'")

    tuple_proxy = emulated_device.proxy("my_tuple")
    str_proxy = emulated_device.proxy("my_str")

    # Should be able to hash
    tuple_hash = hash(tuple_proxy)
    str_hash = hash(str_proxy)

    # Hashes should match the remote hashes
    assert tuple_hash == emulated_device("hash(my_tuple)")
    assert str_hash == emulated_device("hash(my_str)")


def test_proxy_object_comparison_operators(emulated_device):
    """Test comparison operators (__eq__, __ne__, __lt__, __le__, __gt__, __ge__)."""
    emulated_device("val_5 = 5")
    emulated_device("val_10 = 10")
    emulated_device("list_a = [1, 2, 3]")
    emulated_device("list_b = [1, 2, 3]")

    val_5_proxy = emulated_device.proxy("val_5")
    val_10_proxy = emulated_device.proxy("val_10")
    list_a_proxy = emulated_device.proxy("list_a")
    list_b_proxy = emulated_device.proxy("list_b")

    # Test equality
    assert val_5_proxy == 5
    assert val_10_proxy == 10
    assert list_a_proxy == [1, 2, 3]
    assert list_a_proxy == list_b_proxy

    # Test inequality
    assert val_5_proxy != 10
    assert val_5_proxy != val_10_proxy

    # Test less than
    assert val_5_proxy < 10
    assert val_5_proxy < val_10_proxy

    # Test less than or equal
    assert val_5_proxy <= 5
    assert val_5_proxy <= 10
    assert val_5_proxy <= val_10_proxy

    # Test greater than
    assert val_10_proxy > 5
    assert val_10_proxy > val_5_proxy

    # Test greater than or equal
    assert val_10_proxy >= 10
    assert val_10_proxy >= 5
    assert val_10_proxy >= val_5_proxy


def test_proxy_object_str_and_repr(emulated_device):
    """Test __str__ and __repr__ methods."""
    emulated_device("my_value = 42")
    emulated_device("my_list = [1, 2, 3]")

    value_proxy = emulated_device.proxy("my_value")
    list_proxy = emulated_device.proxy("my_list")

    # Test __str__
    assert str(value_proxy) == "42"
    assert str(list_proxy) == "[1, 2, 3]"

    # Test __repr__ - should include "ProxyObject" wrapper
    value_repr = repr(value_proxy)
    list_repr = repr(list_proxy)
    assert "ProxyObject" in value_repr
    assert "42" in value_repr
    assert "ProxyObject" in list_repr
    assert "[1, 2, 3]" in list_repr


def test_proxy_object_call_with_proxy_args(emulated_device):
    """Test calling proxy methods with other ProxyObjects as arguments."""
    emulated_device(
        dedent(
            """\
        class Container:
            def __init__(self):
                self.items = []

            def add(self, item):
                self.items.append(item)
                return len(self.items)

        container = Container()
        item1 = [1, 2, 3]
        item2 = {'key': 'value'}
    """
        )
    )

    container_proxy = emulated_device.proxy("container")
    item1_proxy = emulated_device.proxy("item1")
    item2_proxy = emulated_device.proxy("item2")

    # Call method with ProxyObject arguments
    result1 = container_proxy.add(item1_proxy)
    assert result1 == 1

    result2 = container_proxy.add(item2_proxy)
    assert result2 == 2

    # Verify the items were added correctly
    items = emulated_device("container.items")
    assert len(items) == 2
    assert items[0] == [1, 2, 3]
    assert items[1] == {"key": "value"}


def test_proxy_object_slicing(emulated_device):
    """Test slicing operations on ProxyObjects."""
    emulated_device("my_list = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]")

    list_proxy = emulated_device.proxy("my_list")

    # Test basic slicing
    assert list_proxy[2:5] == [2, 3, 4]
    assert list_proxy[:3] == [0, 1, 2]
    assert list_proxy[7:] == [7, 8, 9]

    # Test step slicing
    assert list_proxy[::2] == [0, 2, 4, 6, 8]
    assert list_proxy[1::2] == [1, 3, 5, 7, 9]
    assert list_proxy[2:8:2] == [2, 4, 6]

    # Test negative indices
    assert list_proxy[-3:] == [7, 8, 9]
    assert list_proxy[:-3] == [0, 1, 2, 3, 4, 5, 6]
    assert list_proxy[-5:-2] == [5, 6, 7]


def test_proxy_object_nested_proxy_objects(emulated_device):
    """Test accessing nested mutable objects returns nested ProxyObjects."""
    emulated_device(
        dedent(
            """\
        nested_structure = {
            'list': [1, 2, [3, 4]],
            'dict': {'inner': {'value': 42}},
            'tuple': (1, 2, [3, 4])
        }
    """
        )
    )

    root_proxy = emulated_device.proxy("nested_structure")

    # Accessing dict returns ProxyObject (dict is mutable)
    list_proxy = root_proxy["list"]
    assert isinstance(list_proxy, ProxyObject)

    # Accessing list element that's immutable returns value directly
    assert list_proxy[0] == 1

    # Accessing list element that's mutable returns ProxyObject
    inner_list_proxy = list_proxy[2]
    assert isinstance(inner_list_proxy, ProxyObject)
    assert inner_list_proxy == [3, 4]

    # Accessing nested dict
    dict_proxy = root_proxy["dict"]
    assert isinstance(dict_proxy, ProxyObject)

    inner_dict_proxy = dict_proxy["inner"]
    assert isinstance(inner_dict_proxy, ProxyObject)

    # Immutable value from nested dict
    assert inner_dict_proxy["value"] == 42


def test_proxy_object_error_promotion_attribute_error(emulated_device):
    """Test that AttributeError is properly promoted from PyboardException."""
    emulated_device("my_obj = {'a': 1}")

    obj_proxy = emulated_device.proxy("my_obj")

    # Accessing non-existent attribute should raise AttributeError, not PyboardException
    with pytest.raises(AttributeError):
        obj_proxy.nonexistent_attribute  # noqa: B018


def test_proxy_object_error_promotion_key_error(emulated_device):
    """Test that KeyError is properly promoted from PyboardException."""
    emulated_device("my_dict = {'a': 1, 'b': 2}")

    dict_proxy = emulated_device.proxy("my_dict")

    # Accessing non-existent key should raise KeyError
    with pytest.raises(KeyError):
        dict_proxy["nonexistent_key"]  # noqa: B018


def test_proxy_object_error_promotion_index_error(emulated_device):
    """Test that IndexError is properly promoted from PyboardException."""
    emulated_device("my_list = [1, 2, 3]")

    list_proxy = emulated_device.proxy("my_list")

    # Accessing out-of-bounds index should raise IndexError
    with pytest.raises(IndexError):
        list_proxy[100]  # noqa: B018


def test_proxy_object_error_promotion_type_error(emulated_device):
    """Test that TypeError is properly promoted from PyboardException."""
    emulated_device("my_value = 42")

    value_proxy = emulated_device.proxy("my_value")

    # Trying to call a non-callable should raise TypeError
    with pytest.raises(TypeError):
        value_proxy()


def test_device_proxy_method_import_detection(emulated_device):
    """Test that device.proxy() correctly detects and handles import statements."""
    # Single import
    os_proxy = emulated_device.proxy("import os")
    assert isinstance(os_proxy, ProxyObject)
    # Should be delete=False by default for imports
    assert object.__getattribute__(os_proxy, "_belay_delete") is False

    # From import
    sin_proxy = emulated_device.proxy("from math import sin")
    assert isinstance(sin_proxy, ProxyObject)
    # Can call the imported function
    result = sin_proxy(0)
    assert result == 0

    # Multiple imports
    result = emulated_device.proxy("from math import cos, pi")
    assert isinstance(result, tuple)
    assert len(result) == 2
    cos_proxy, pi_value = result
    assert isinstance(cos_proxy, ProxyObject)
    # pi is an immutable float, so it's returned directly, not as ProxyObject
    assert isinstance(pi_value, float)
    assert abs(pi_value - 3.14159) < 0.001


def test_device_proxy_method_expression_vs_identifier(emulated_device):
    """Test device.proxy() behavior with identifiers vs expressions."""
    emulated_device("simple_var = 123")
    emulated_device("my_list = [1, 2, 3]")

    # Identifier - delete should default to False
    var_proxy = emulated_device.proxy("simple_var")
    assert object.__getattribute__(var_proxy, "_belay_delete") is False

    # Expression - delete should default to True
    expr_proxy = emulated_device.proxy("[1, 2, 3]")
    assert object.__getattribute__(expr_proxy, "_belay_delete") is True

    # Can explicitly override
    var_proxy_delete = emulated_device.proxy("simple_var", delete=True)
    assert object.__getattribute__(var_proxy_delete, "_belay_delete") is True

    expr_proxy_no_delete = emulated_device.proxy("[4, 5, 6]", delete=False)
    assert object.__getattribute__(expr_proxy_no_delete, "_belay_delete") is False


def test_device_call_with_proxy_argument(emulated_device):
    """Test that Device.__call__ can resolve ProxyObjects."""
    emulated_device("my_list = [1, 2, 3]")

    # Create a proxy
    list_proxy = emulated_device.proxy("my_list")

    # Should be able to resolve the proxy to get the actual value
    resolved = emulated_device(list_proxy)
    assert resolved == [1, 2, 3]
    assert not isinstance(resolved, ProxyObject)


def test_device_call_with_proxy_parameter(emulated_device):
    """Test Device.__call__ with proxy=True parameter."""
    emulated_device("result_value = 42")
    emulated_device("result_list = [1, 2, 3]")

    # Immutable expression with proxy=True should still return immutable value directly
    # because __belay_obj_create detects immutable types
    value = emulated_device("result_value", proxy=True)
    assert value == 42  # Immutable, returned directly

    # Mutable expression with proxy=True returns ProxyObject
    list_proxy = emulated_device("result_list", proxy=True)
    assert isinstance(list_proxy, ProxyObject)
    assert list_proxy == [1, 2, 3]


def test_proxy_object_setattr_with_proxy_value(emulated_device):
    """Test setting a ProxyObject attribute to another ProxyObject (Issue #182)."""
    emulated_device(
        dedent(
            """\
            class Container:
                def __init__(self):
                    self.config = None
                    self.data = None

            container = Container()
            config_dict = {'setting': 42, 'enabled': True}
            data_list = [1, 2, 3, 4, 5]
        """
        )
    )

    container_proxy = emulated_device.proxy("container")
    config_proxy = emulated_device.proxy("config_dict")
    data_proxy = emulated_device.proxy("data_list")

    # Test setting attribute to a ProxyObject representing a mutable object
    container_proxy.config = config_proxy
    result = emulated_device("container.config")
    assert result == {"setting": 42, "enabled": True}

    # Test setting attribute to another ProxyObject
    container_proxy.data = data_proxy
    result = emulated_device("container.data")
    assert result == [1, 2, 3, 4, 5]

    # Verify we can access through the proxy
    assert container_proxy.config == {"setting": 42, "enabled": True}
    assert container_proxy.data == [1, 2, 3, 4, 5]


def test_proxy_object_setitem_with_proxy_value(emulated_device):
    """Test setting a ProxyObject list/dict item to another ProxyObject."""
    emulated_device(
        dedent(
            """\
            my_list = [None, None, None]
            my_dict = {'a': None, 'b': None}
            obj1 = {'value': 1}
            obj2 = {'value': 2}
        """
        )
    )

    list_proxy = emulated_device.proxy("my_list")
    dict_proxy = emulated_device.proxy("my_dict")
    obj1_proxy = emulated_device.proxy("obj1")
    obj2_proxy = emulated_device.proxy("obj2")

    # Test setting list item to ProxyObject
    list_proxy[0] = obj1_proxy
    result = emulated_device("my_list[0]")
    assert result == {"value": 1}

    # Test setting dict item to ProxyObject
    dict_proxy["a"] = obj2_proxy
    result = emulated_device("my_dict['a']")
    assert result == {"value": 2}

    # Verify we can access through the proxy
    assert list_proxy[0] == {"value": 1}
    assert dict_proxy["a"] == {"value": 2}
