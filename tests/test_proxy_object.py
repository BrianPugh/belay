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


def test_proxy_class(proxy_object):
    assert proxy_object.foo == 1
    assert proxy_object.bar == 2

    assert proxy_object.some_method(3) == 6
    proxy_object.foo = 4
    assert proxy_object.foo == 4

    with pytest.raises(AttributeError):
        proxy_object.non_existant_attribute  # noqa: B018
