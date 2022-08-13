# Creates and populates two set[str]: all_files, all_dirs
import os, hashlib, binascii
def __belay_hash_file(fn):
    hasher = hashlib.sha256()
    try:
        with open(fn, "rb") as f:
            while True:
                data = f.read(4096)
                if not data:
                    break
                hasher.update(data)
    except OSError:
        return "0" * 64
    return str(binascii.hexlify(hasher.digest()))
all_files, all_dirs = set(), []
def enumerate_fs(path=""):
    for elem in os.ilistdir(path):
        full_name = path + "/" + elem[0]
        if elem[1] & 0x4000:  # is_dir
            all_dirs.append(full_name)
            enumerate_fs(full_name)
        else:
            all_files.add(full_name)
enumerate_fs()
all_dirs.sort()
del enumerate_fs
