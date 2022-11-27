# Creates and populates two set[str]: all_files, all_dirs
def __belay_hfs(fns):
    buf = memoryview(bytearray(4096))
    return [__belay_hf(fn, buf) for fn in fns]
def __belay_mkdirs(fns):
    for fn in fns:
        try:
            os.mkdir(fn)
        except OSError:
            pass
def __belay_del_fs(path="/", keep=(), check=True):
    if not path:
        path = "/"
    elif not path.endswith("/"):
        path += "/"
    if check:
        try:
            os.stat(path)
        except OSError:
            return
    for name, mode, *_ in __belay_ilistdir(path):
        full_name = path + name
        if full_name in keep:
            continue
        if mode & 0x4000:  # is_dir
            __belay_del_fs(full_name, keep, check=False)
            try:
                os.rmdir(full_name)
            except OSError:
                pass
        else:
            os.remove(full_name)
