from distutils import dir_util
from pathlib import Path

import pytest


@pytest.fixture
def data_path(tmp_path, request):
    """Temporary copy of folder with same name as test module.

    Fixture responsible for searching a folder with the same name of test
    module and, if available, copying all contents to a temporary directory so
    tests can use them freely.
    """
    filename = Path(request.module.__file__)
    test_dir = filename.parent / filename.stem
    if test_dir.is_dir():
        dir_util.copy_tree(str(test_dir), str(tmp_path))

    return tmp_path
