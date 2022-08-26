# Creates and populates two set[str]: all_files, all_dirs
import os, hashlib, errno
def __belay_hf(fn):
    h = hashlib.sha256()
    try:
        with open(fn, "rb") as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                h.update(data)
    except OSError:
        return b""
    return h.digest()
def __belay_hfs(fns):
    print("_BELAYR" + repr([__belay_hf(fn) for fn in fns]))
def __belay_mkdirs(fns):
    for fn in fns:
        try:
            os.mkdir(fn)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
all_files, all_dirs = set(), []
def __belay_fs(path=""):
    for elem in os.ilistdir(path):
        full_name = path + "/" + elem[0]
        if elem[1] & 0x4000:  # is_dir
            all_dirs.append(full_name)
            __belay_fs(full_name)
        else:
            all_files.add(full_name)
__belay_fs()
all_dirs.sort()
del __belay_fs
