from importlib.machinery import SourceFileLoader

import pytest

import belay.inspect


@pytest.fixture
def foo(data_path):
    fn = data_path / "foo.py"
    foo = SourceFileLoader("foo", str(fn)).load_module()
    assert foo.__file__ == str(fn)
    return foo


def test_getsource_pattern_match():
    pat = belay.inspect._pat_no_decorators
    assert not pat.match("@device.task")
    assert not pat.match("@device.task()")
    assert not pat.match("@device.task(")
    assert not pat.match("")
    assert not pat.match("\n")

    assert pat.match("def foo")
    assert pat.match("def foo()")
    assert pat.match("def foo(")
    assert pat.match("def foo(\n\n")

    assert pat.match("async def foo")
    assert pat.match("async def foo()")
    assert pat.match("async def foo(")
    assert pat.match("async def foo(\n\n")


def test_getsource_basic(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo)
    assert code == "def foo(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 15
    assert file == foo.__file__


def test_getsource_decorated_1(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_1)
    assert code == "def foo_decorated_1(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 20
    assert file == foo.__file__


def test_getsource_decorated_2(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_2)
    assert code == "def foo_decorated_2(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 25
    assert file == foo.__file__


def test_getsource_decorated_3(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_3)
    assert code == "def foo_decorated_3(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 30
    assert file == foo.__file__


def test_getsource_decorated_4(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_4)
    assert (
        code
        == "def foo_decorated_4(\n    arg1,\n    arg2,\n):\n    return arg1 + arg2\n"
    )
    assert lineno == 35
    assert file == foo.__file__
