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
    assert proxy_object.foo == 1
    assert proxy_object.bar == 2

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


def test_proxy_object_dir(proxy_object):
    result = dir(proxy_object)
    result = set(result)
    expected = {"__init__", "__module__", "__new__", "__qualname__", "bar", "foo", "some_method", "some_dict"}
    assert expected.issubset(result)


def test_proxy_object_dict_keys(proxy_object):
    result = proxy_object.some_dict.keys()
    assert {"a", "b", "c"} == set(result)


def test_proxy_object_dict_values(proxy_object):
    result = proxy_object.some_dict.values()
    assert {1, 2, 3} == set(result)


def test_proxy_object_getitem(emulated_device, proxy_object):
    emulated_device("klass.demo_list = [1,2,3]")
    assert proxy_object.demo_list == [1, 2, 3]
    assert proxy_object.demo_list[1] == 2
    assert proxy_object.demo_list[-1] == 3
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
