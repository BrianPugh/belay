class AuthenticationError(Exception):
    """Invalid password or similar."""


class FeatureUnavailableError(Exception):
    """Feature unavailable for your board's implementation."""


class SpecialFunctionNameError(Exception):
    """Reserved function name that may impact Belay functionality.

    Currently limited to:

        * Names that start and end with double underscore, ``__``.

        * Names that start with ``_belay`` or ``__belay``
    """


class ReconstructionError(Exception):
    """Too many commands were given."""


class ConnectionLost(Exception):
    """Lost connection to device."""
