# Creates and populates two set[str]: all_files, all_dirs
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
    for elem in __belay_ilistdir(path):
        full_name = path + elem[0]
        if elem[1] & 0x4000:  # is_dir
            all_dirs.append(full_name)
            __belay_fs(full_name, check=False)
        else:
            all_files.add(full_name)
