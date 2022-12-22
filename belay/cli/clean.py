import shutil

from belay.project import find_dependencies_folder, load_groups


def clean():
    """Remove any downloaded dependencies if they are no longer specified in pyproject."""
    groups = load_groups()
    dependencies_folder = find_dependencies_folder()

    existing_group_folders = {x for x in dependencies_folder.glob("*") if x.is_dir()}

    # Remove missing dependencies in each group
    for group in groups:
        group.clean()
        existing_group_folders.discard(group.folder)

    # Remove missing group folders
    for group_folder in existing_group_folders:
        shutil.rmtree(group_folder)
