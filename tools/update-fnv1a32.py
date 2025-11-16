"""
Script to update FNV1A32 native module files from GitHub releases.

Downloads .mpy files from a specified release of micropython-fnv1a32
and copies them to belay/nativemodule_fnv1a32/ with the correct naming convention.
"""

import argparse
import shutil
import tempfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve


def get_release_assets(version: str) -> list[dict]:
    """Get release assets from GitHub API."""
    if not version.startswith("v"):
        version = f"v{version}"

    url = f"https://api.github.com/repos/BrianPugh/micropython-fnv1a32/releases/tags/{version}"

    try:
        with urlopen(url) as response:
            import json

            data = json.loads(response.read())
            return data.get("assets", [])
    except Exception as e:
        print(f"Error fetching release data: {e}")
        return []


def download_and_extract_mpy_files(assets: list[dict], temp_dir: Path) -> list[Path]:
    """Download and extract .mpy files from release assets."""
    mpy_files = []

    for asset in assets:
        name = asset["name"]
        download_url = asset["browser_download_url"]

        if name.endswith(".mpy"):
            print(f"Downloading {name}...")
            file_path = temp_dir / name
            urlretrieve(download_url, file_path)
            mpy_files.append(file_path)

    return mpy_files


def convert_filename(original_name: str) -> str:
    """Convert GitHub release filename to belay naming convention.

    From: fnv1a32-v2.1.0-mpy1.22-armv6m.mpy
    To:   mpy1.22-armv6m.mpy
    """
    parts = original_name.split("-")
    if len(parts) >= 4 and parts[0] == "fnv1a32":
        # Extract mpy version and architecture
        mpy_version = parts[2]  # e.g., "mpy1.22"
        architecture = parts[3].replace(".mpy", "")  # e.g., "armv6m"
        return f"{mpy_version}-{architecture}.mpy"

    return original_name


def copy_files_to_destination(mpy_files: list[Path], dest_dir: Path):
    """Copy .mpy files to the destination directory with proper naming."""
    dest_dir.mkdir(parents=True, exist_ok=True)

    for mpy_file in mpy_files:
        new_name = convert_filename(mpy_file.name)
        dest_path = dest_dir / new_name

        print(f"Copying {mpy_file.name} -> {new_name}")
        shutil.copy2(mpy_file, dest_path)


def main():
    parser = argparse.ArgumentParser(description="Update FNV1A32 native module files from GitHub releases")
    parser.add_argument("version", help="Release version to download (e.g., 'v2.1.0' or '2.1.0')")

    args = parser.parse_args()

    dest_dir = Path(__file__).parent.parent / "belay" / "nativemodule_fnv1a32"

    print(f"Fetching release information for version {args.version}...")
    assets = get_release_assets(args.version)

    if not assets:
        print("No assets found for this release or release does not exist.")
        return 1

    # Filter for .mpy files
    mpy_assets = [asset for asset in assets if asset["name"].endswith(".mpy")]

    if not mpy_assets:
        print("No .mpy files found in this release.")
        return 1

    print(f"Found {len(mpy_assets)} .mpy files:")
    for asset in mpy_assets:
        old_name = asset["name"]
        new_name = convert_filename(old_name)
        print(f"  {old_name} -> {new_name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        print("\nDownloading files to temporary directory...")
        mpy_files = download_and_extract_mpy_files(mpy_assets, temp_path)

        if mpy_files:
            print(f"\nCopying files to {dest_dir}...")
            copy_files_to_destination(mpy_files, dest_dir)
            print(f"\nSuccessfully updated {len(mpy_files)} .mpy files!")
        else:
            print("No files were downloaded.")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
