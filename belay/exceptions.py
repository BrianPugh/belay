class BelayException(Exception):
    """Root Belay exception class."""


class AuthenticationError(BelayException):
    """Invalid password or similar."""


class FeatureUnavailableError(BelayException):
    """Feature unavailable for your board's implementation."""


class SpecialFunctionNameError(BelayException):
    """Attempted to use a reserved Belay function name.

    The following name rules are reserved:

        * Names that start and end with double underscore, ``__``.

        * Names that start with ``_belay`` or ``__belay``
    """


class MaxHistoryLengthError(BelayException):
    """Too many commands were given."""


class ConnectionLost(BelayException):
    """Lost connection to device."""
