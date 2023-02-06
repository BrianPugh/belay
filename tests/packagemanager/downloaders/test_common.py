from belay.packagemanager.downloaders.common import _download_generic, downloaders


def test_download_registry():
    assert set(downloaders) == {
        "github",
    }


def test_download_generic_local_single(tmp_path):
    src = tmp_path / "src" / "foo.py"
    dst = tmp_path / "dst"

    src.parent.mkdir()
    dst.mkdir()

    src.write_text("a = 5")

    _download_generic(dst, str(src))

    assert (dst / "foo.py").read_text() == "a = 5"


def test_download_generic_local_folder(tmp_path):
    src_folder = tmp_path / "src"
    src_folder.mkdir()

    dst_folder = tmp_path / "dst"
    dst_folder.mkdir()

    src_init = src_folder / "__init__.py"
    src_foo = src_folder / "foo.py"
    src_bar = src_folder / "bar.py"

    src_init.touch()
    src_foo.write_text("a = 5")
    src_bar.write_text("b = 6")

    _download_generic(dst_folder, str(src_folder))

    assert (dst_folder / "__init__.py").exists()
    assert (dst_folder / "foo.py").read_text() == "a = 5"
    assert (dst_folder / "bar.py").read_text() == "b = 6"
