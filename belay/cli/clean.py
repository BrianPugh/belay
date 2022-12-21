from belay.project import load_groups


def clean():
    """Remove any downloaded dependencies if they are no longer specified in pyproject."""
    groups = load_groups()

    for group in groups:
        group.clean()
