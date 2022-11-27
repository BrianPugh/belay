@micropython.native
def __belay_hf(fn, buf):
    # is inherently modulo 32-bit arithmetic
    @micropython.viper
    def xor_mm(data, state: uint, prime: uint) -> uint:
        for b in data:
            state = uint((state ^ uint(b)) * prime)
        return state

    h = 0x811c9dc5
    try:
        f = open(fn, "rb")
        while True:
            n = f.readinto(buf)
            if n == 0:
                break
            h = xor_mm(buf[:n], h, 0x01000193)
        f.close()
    except OSError:
        h = 0
    return h
