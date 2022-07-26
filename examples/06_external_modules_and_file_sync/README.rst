Example 06: External Modules and File Sync
==========================================

This example introduces the ``sync`` method.
``sync`` takes in a string path to a local folder, and will synchronize the contents to the root of the device's filesystem.
For example, if the local filesystem looks like:

::

    project
    ├── main.py
    └── board
        ├── foo.py
        └── bar
            └── baz.py

Then, after ``device.sync("board")`` is ran, the root of the remote filesystem will look like:

::

    foo.py
    bar
    └── baz.py


``sync`` only pushes files who's hash has changed since the last sync.
At the end of ``sync``, all files and folders that exist in the device's filesystem that do not have a corresponding file/folder in the local path will be deleted.

Now that files have been synced, we can import python modules like normal, and we can read synced-in files.
