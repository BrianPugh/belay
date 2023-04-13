"""Metaclass to allow executer overloading.

Inspired by mCoding example::

    https://github.com/mCodingLLC/VideosSampleCode/blob/master/videos/077_metaclasses_in_python/overloading.py

"""
from typing import Callable

from autoregistry import RegistryMeta

from .exceptions import NoMatchingExecuterError

_MISSING = object()


class _ExecuterList(list):
    """To separate user-lists from a list of overloaded methods."""


class _OverloadDict(dict):
    """Dictionary where a key can be written to multiple times."""

    def __setitem__(self, key, value):
        # Key: method name
        # Value: method

        if not isinstance(key, str):
            raise TypeError

        prior_val = self.get(key, _MISSING)
        method_metadata = getattr(value, "__belay__", False)

        if prior_val is _MISSING:
            # Register a new method name
            insert_val = _ExecuterList([value]) if method_metadata else value
            super().__setitem__(key, insert_val)
        elif isinstance(prior_val, _ExecuterList):
            # Add to a previously overloaded method.
            if not method_metadata:
                raise ValueError(f"Cannot mix non-executer and executer methods: {key}")

            # Check for a previous "catchall" method
            for f in prior_val:
                if not f.__belay__.implementation:
                    raise ValueError(
                        f"Cannot define another executor after catchall: {key}."
                    )
            prior_val.append(value)
        else:
            # Overwrite a previous vanilla method
            if method_metadata:
                raise ValueError(f"Cannot mix non-executer and executer methods: {key}")
            super().__setitem__(key, value)


class _Overload:
    def __set_name__(self, owner, name):
        self.owner = owner
        self.name = name

    def __init__(self, overload_list):
        if not isinstance(overload_list, _ExecuterList):
            raise TypeError("must use OverloadList")
        if not overload_list:
            raise ValueError("empty overload list")
        self.overload_list = overload_list

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.overload_list!r})"

    def __get__(self, instance, _owner=None):
        if instance is None:
            return self
        # don't use owner == type(instance)
        # we want self.owner, which is the class from which get is being called
        return BoundOverloadDispatcher(
            instance, self.owner, self.name, self.overload_list
        )


class BoundOverloadDispatcher:
    def __init__(self, instance, owner_cls, name, overload_list):
        self.instance = instance
        self.owner_cls = owner_cls
        self.name = name
        self.overload_list = overload_list

    def best_match(self, *args, **kwargs):
        target = self.instance.implementation.name

        for f in self.overload_list:
            imp = f.__belay__.implementation

            if not imp or imp == target:
                return f

        raise NoMatchingExecuterError()

    def __call__(self, *args, **kwargs):
        try:
            f = self.best_match(*args, **kwargs)
        except NoMatchingExecuterError:
            pass
        else:
            # All executers are static methods, so don't pass in ``self.instance``
            return f(*args, **kwargs)

        # no matching overload in owner class, check next in line
        super_instance = super(self.owner_cls, self.instance)
        super_call = getattr(super_instance, self.name, _MISSING)
        if super_call is not _MISSING:
            return super_call(*args, **kwargs)  # type: ignore[reportGeneralTypeIssues]
        else:
            raise NoMatchingExecuterError()


class DeviceMeta(RegistryMeta):
    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        return _OverloadDict()

    def __new__(cls, name, bases, namespace, **kwargs):
        overload_namespace = {
            key: _Overload(val) if isinstance(val, _ExecuterList) else val
            for key, val in namespace.items()
        }
        return super().__new__(cls, name, bases, overload_namespace, **kwargs)
