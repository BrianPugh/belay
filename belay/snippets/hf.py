def __belay_hf(fn, buf):
    # inherently is inherently modulo 32-bit arithmetic
    mod = (1 << 32)
    h = 0x811c9dc5
    try:
        f = open(fn, "rb")
        while True:
            n = f.readinto(buf)
            if n == 0:
                break
            for b in buf[:n]:
                h = ((h ^ b) * 0x01000193) % mod  # todo: investigate fast mm
        f.close()
    except OSError:
        h = 0
    return h
