for file in all_files:
    os.remove(file)
for folder in reversed(all_dirs):
    try:
        os.rmdir(folder)
    except OSError:
        pass
del all_files, all_dirs, __belay_hf, __belay_hfs, __belay_mkdirs
