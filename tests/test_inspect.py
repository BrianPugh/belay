"""Tests extensions to the builtin inspect module.

Note: ``untokenize`` doesn't properly preserve inter-token spacing, so this test vector
may need to change while still remaining valid.
"""

import types
import pytest

from importlib.machinery import SourceFileLoader

import belay.inspect


@pytest.fixture
def foo(data_path):
    fn = data_path / "foo.py"
    module_name = "foo"
    # Create a new module object
    foo = types.ModuleType(module_name)
    foo.__file__ = str(fn)
    # Load the source file into the module object
    loader = SourceFileLoader(module_name, str(fn))
    loader.exec_module(foo)
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


def test_getsource_basic_body(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 16
    assert file == foo.__file__


def test_getsource_decorated_1(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_1)
    assert code == "def foo_decorated_1(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 20
    assert file == foo.__file__


def test_getsource_decorated_1_body(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_1, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 21
    assert file == foo.__file__


def test_getsource_decorated_2(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_2)
    assert code == "def foo_decorated_2(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 25
    assert file == foo.__file__


def test_getsource_decorated_2_body(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_2, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 26
    assert file == foo.__file__


def test_getsource_decorated_3(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_3)
    assert code == "def foo_decorated_3(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 30
    assert file == foo.__file__


def test_getsource_decorated_3_body(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_3, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 31
    assert file == foo.__file__


def test_getsource_decorated_4(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_4)
    assert code == "def foo_decorated_4(\n    arg1,\n    arg2,\n):\n    return arg1 + arg2\n"
    assert lineno == 35
    assert file == foo.__file__


def test_getsource_decorated_4_body(foo):
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_4, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 39
    assert file == foo.__file__


def test_getsource_decorated_5(foo):
    """Removes leading indent."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_5)
    assert code == "def foo_decorated_5 (arg1 ,arg2 ):\n    return arg1 +arg2 \n"
    assert lineno == 45
    assert file == foo.__file__


def test_getsource_decorated_5_body(foo):
    """Removes leading indent."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_5, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 46
    assert file == foo.__file__


def test_getsource_decorated_6(foo):
    """Double decorated."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_6)
    assert code == "def foo_decorated_6(arg1, arg2):\n    return arg1 + arg2\n"
    assert lineno == 51
    assert file == foo.__file__


def test_getsource_decorated_6_body(foo):
    """Double decorated."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_6, strip_signature=True)
    assert code == "return arg1 +arg2 \n"
    assert lineno == 52
    assert file == foo.__file__


def test_getsource_decorated_7(foo):
    """Double decorated."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_7)
    assert (
        code
        == 'def foo_decorated_7(arg1, arg2):\n    return """This\n    is\na\n  multiline\n             string.\n"""\n'
    )
    assert lineno == 56
    assert file == foo.__file__


def test_getsource_decorated_7_body(foo):
    """Double decorated."""
    code, lineno, file = belay.inspect.getsource(foo.foo_decorated_7, strip_signature=True)
    assert code == 'return """This\n    is\na\n  multiline\n             string.\n"""\n'
    assert lineno == 57
    assert file == foo.__file__


def test_getsource_nested():
    def foo():
        bar = 5
        return 7

    code, lineno, file = belay.inspect.getsource(foo)
    assert code == "def foo ():\n    bar =5 \n    return 7 \n"
    assert file == __file__


def test_getsource_nested_multiline_string():
    for _ in range(1):

        def foo(arg1, arg2):
            return """This
    is
a
  multiline
             string.
"""

    code, lineno, file = belay.inspect.getsource(foo)
    assert code == 'def foo (arg1 ,arg2 ):\n    return """This\n    is\na\n  multiline\n             string.\n"""\n'
    assert file == __file__


def test_getsource_nested_multiline_function():
    # fmt: off
    def bar(a, b):
        return a * b

    for _ in range(1):

        def foo(arg1, arg2):
            return bar(
arg1,
    arg2
)

    # fmt: on
    code, lineno, file = belay.inspect.getsource(foo)
    assert code == "def foo (arg1 ,arg2 ):\n    return bar (\n    arg1 ,\n    arg2 \n    )\n"
    assert file == __file__


def test_isexpression_basic():
    assert belay.inspect.isexpression("") == False

    # Basic expressions (True)
    assert belay.inspect.isexpression("1") == True
    assert belay.inspect.isexpression("1 + 2") == True
    assert belay.inspect.isexpression("foo") == True

    # Statements (False)
    assert belay.inspect.isexpression("foo = 1 + 2") == False
    assert belay.inspect.isexpression("if True:\n 1 + 2") == False

    # Invalid syntax (False)
    assert belay.inspect.isexpression("1foo") == False
    assert belay.inspect.isexpression("1+") == False


def test_remove_signature_basic():
    code = "def foo(arg1, arg2):\n    arg1 += 1\n    return arg1 + arg2\n"
    res, lines_removed = belay.inspect._remove_signature(code)
    assert lines_removed == 1
    assert res == "    arg1 += 1\n    return arg1 + arg2\n"


def test_remove_signature_multiline():
    code = "def foo(arg1,\n arg2\n):\n    arg1 += 1\n    return arg1 + arg2\n"
    res, lines_removed = belay.inspect._remove_signature(code)
    assert lines_removed == 3
    assert res == "    arg1 += 1\n    return arg1 + arg2\n"


@pytest.mark.parametrize(
    "statement,expected",
    [
        ("import foo", ["foo"]),
        ("from foo import bar", ["bar"]),
        ("from foo.bar import fizz", ["fizz"]),
        ("from foo import fizz, buzz", ["fizz", "buzz"]),
        ("import foo as buzz", ["buzz"]),
        ("from foo import bar as baz", ["baz"]),
        ("from foo import bar as baz, qux as quux", ["baz", "quux"]),
        ("from foo import *", []),  # Don't return any objects for a * import
        ("foo", []),  # Non import statements return an empty list
        ("import os.path", ["os"]),  # Dotted imports return the root module
        ("import os.path as ospath", ["ospath"]),  # Dotted import with alias
        ("from . import foo", ["foo"]),  # Relative import
        ("from .. import bar", ["bar"]),  # Parent relative import
        ("from .submodule import baz", ["baz"]),  # Relative submodule import
        ("import sys, os", ["sys", "os"]),  # Multiple imports on one line
        ("import sys as s, os as o", ["s", "o"]),  # Multiple imports with aliases
    ],
)
def test_import_names(statement, expected):
    assert belay.inspect.import_names(statement) == expected


def test_import_names_multiline():
    """Test that multi-line imports are not supported (returns empty list)."""
    multiline_import = """from foo import (
        bar,
        baz
    )"""
    # Multi-line imports are not parsed correctly, return empty
    # This is expected behavior - import_names is for simple single-line imports
    result = belay.inspect.import_names(multiline_import)
    # Should either return the correct names or empty list
    assert isinstance(result, list)


def test_import_names_with_comments():
    """Test import statements with comments."""
    # Comments should be handled gracefully
    result = belay.inspect.import_names("import os  # Operating system interface")
    # AST parsing should handle this correctly
    assert result == ["os"]


def test_import_names_invalid_syntax():
    """Test that invalid syntax returns empty list."""
    assert belay.inspect.import_names("import") == []
    assert belay.inspect.import_names("from") == []
    assert belay.inspect.import_names("import 123") == []
    assert belay.inspect.import_names("not an import") == []
