# Creates and populates two set[str]: all_files, all_dirs
import os
def __belay_hf(fn):
    h = 0xcbf29ce484222325
    size = 1 << 64
    try:
        with open(fn, "rb") as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                for byte in data:
                    h = h ^ byte
                    h = (h * 0x100000001b3) % size
    except OSError:
        return 0
    return h
def __belay_hfs(fns):
    print("_BELAYR" + repr([__belay_hf(fn) for fn in fns]))
def __belay_mkdirs(fns):
    for fn in fns:
        try:
            os.mkdir(fn)
        except OSError:
            pass
all_files, all_dirs = set(), []
def __belay_fs(path=""):
    for elem in os.listdir(path):
        full_name = path + "/" + elem
        try:
            if os.stat(elem)[0] & 0x4000:  # is_dir
                all_dirs.append(full_name)
                __belay_fs(full_name)
            else:
                all_files.add(full_name)
        except OSError:
            pass
__belay_fs()
all_dirs.sort()
del __belay_fs
