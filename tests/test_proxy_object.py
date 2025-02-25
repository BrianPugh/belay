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
                def some_method(self, value):
                    return 2 * value
            klass = Klass()
            """
        )
    )

    obj = ProxyObject(emulated_device, "klass")
    return obj


def test_proxy_class_basic(proxy_object):
    assert proxy_object.foo == 1
    assert proxy_object.bar == 2

    assert proxy_object.some_method(3) == 6
    proxy_object.foo = 4
    assert proxy_object.foo == 4

    with pytest.raises(AttributeError):
        proxy_object.non_existant_attribute  # noqa: B018


def test_proxy_class_dir(proxy_object):
    result = dir(proxy_object)
    result = set(result)
    expected = {"__init__", "__module__", "__new__", "__qualname__", "bar", "foo", "some_method"}
    assert expected.issubset(result)


def test_proxy_class_getitem(emulated_device, proxy_object):
    emulated_device("klass.demo_list = [1,2,3]")
    assert proxy_object.demo_list == [1, 2, 3]
    assert proxy_object.demo_list[1] == 2
    assert proxy_object.demo_list[-1] == 3
    assert proxy_object.demo_list[:2] == [1, 2]

    with pytest.raises(IndexError):
        proxy_object.demo_list[100]


def test_proxy_class_len(emulated_device, proxy_object):
    emulated_device("klass.demo_list = [1,2,3]")
    assert len(proxy_object.demo_list) == 3
