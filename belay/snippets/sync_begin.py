# Creates and populates two set[str]: all_files, all_dirs
import os
import micropython
@micropython.native
def __belay_hf(fn, buf):
    # inherently is inherently modulo 32-bit arithmetic
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
def __belay_hfs(fns):
    buf = memoryview(bytearray(4096))
    print("_BELAYR" + repr([__belay_hf(fn, buf) for fn in fns]))
def __belay_mkdirs(fns):
    for fn in fns:
        try:
            os.mkdir(fn)
        except OSError:
            pass
all_files, all_dirs = set(), []
def __belay_fs(path="/", check=True):
    if not path:
        path = "/"
    elif not path.endswith("/"):
        path += "/"
    if check:
        try:
            os.stat(path)
        except OSError:
            return
    for elem in os.ilistdir(path):
        full_name = path + elem[0]
        if elem[1] & 0x4000:  # is_dir
            all_dirs.append(full_name)
            __belay_fs(full_name, check=False)
        else:
            all_files.add(full_name)
