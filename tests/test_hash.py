import belay.hash


def test_sync_local_belay_hf(tmp_path):
    """Test local FNV-1a hash implementation.

    Test vector from: http://www.isthe.com/chongo/src/fnv/test_fnv.c
    """
    f = tmp_path / "test_file"
    f.write_text("foobar")
    actual = belay.hash.fnv1a(f)
    assert actual == 0xBF9CF968
