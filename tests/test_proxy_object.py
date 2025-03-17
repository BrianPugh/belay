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


def test_proxy_object_basic(proxy_object):
    assert proxy_object.foo == 1
    assert proxy_object.bar == 2

    assert proxy_object.some_method(3) == 6
    proxy_object.foo = 4
    assert proxy_object.foo == 4

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
