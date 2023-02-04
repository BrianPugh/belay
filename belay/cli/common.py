help_port = "Port (like /dev/ttyUSB0) or WebSocket (like ws://192.168.1.100) of device."
help_password = (  # nosec
    "Password for communication methods (like WebREPL) that require authentication."
)

yes_terms = {"y", "yes"}
no_terms = {"n", "no"}


def confirm_action() -> bool:
    """Ask user `[y/N]` to confirm action before proceeding."""
    while True:
        resp = input("Do you want to continue [y/N]? ")
        resp = resp.lower()

        if resp in yes_terms:
            return True
        elif resp in no_terms:
            return False
        else:
            print(f'Invalid response: "{resp}"')
