from functools import wraps


def decorator(f=None, **kwargs):
    if f is None:
        return decorator

    @wraps(f)
    def inner(*args, **kwargs):
        return f(*args, **kwargs)

    return inner


def foo(arg1, arg2):
    return arg1 + arg2


@decorator
def foo_decorated_1(arg1, arg2):
    return arg1 + arg2


@decorator()
def foo_decorated_2(arg1, arg2):
    return arg1 + arg2


@decorator(some_kwarg="test")
def foo_decorated_3(arg1, arg2):
    return arg1 + arg2


@decorator()
def foo_decorated_4(
    arg1,
    arg2,
):
    return arg1 + arg2


if True:

    @decorator
    def foo_decorated_5(arg1, arg2):
        return arg1 + arg2


@decorator
@decorator
def foo_decorated_6(arg1, arg2):
    return arg1 + arg2


@decorator
def foo_decorated_7(arg1, arg2):
    return """This
    is
a
  multiline
             string.
"""
