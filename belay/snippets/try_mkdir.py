import os, errno
try:
    os.mkdir('%s')
except OSError as e:
    if e.errno != errno.EEXIST:
        raise
