import _belay_fnv1a32
def __belay_hf(fn, buf):
    try:
        with open(fn, "rb") as f:
            h = _belay_fnv1a32.fnv1a32(f, buffer=buf)
    except OSError:
        h = 0
    return h
