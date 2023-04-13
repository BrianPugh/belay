class BelayException(Exception):  # noqa: N818
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


class DeviceNotFoundError(BelayException):
    """Unable to find specified device."""


class InsufficientSpecifierError(BelayException):
    """Specifier wasn't unique enough to determine a single device."""


class ConnectionFailedError(BelayException):
    """Unable to connect to specified device."""


class ConnectionLost(ConnectionFailedError):  # noqa: N818
    """Lost connection to device."""


class InternalError(BelayException):
    """Internal to Belay logic error."""


class NotBelayResponseError(BelayException):
    """Parsed response wasn't for Belay."""


class NoMatchingExecuterError(BelayException):
    """No valid executer found for the given board Implementation."""
