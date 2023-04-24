Package Manager
===============

The Belay CLI provides package manager functionality.
At a high level, the Belay Package Manager does the following:

1. Reads settings from ``pyproject.toml``. Dependencies are defined by URL's where they can be fetched.
   Commonly these are files hosted on github.
2. Downloads dependencies to the ``.belay/dependencies/`` folder. This folder should be committed to the
   project's git repository. This allows for repeatable deployment, even if a remote dependency
   goes missing or changes it's API.
3. Syncs the contents of ``.belay/dependencies/`` to the on-device ``/lib`` folder. This folder is included
   in the on-device ``PATH``.
4. Syncs the contents of the project package directory.

Configuration
^^^^^^^^^^^^^
Belay's Package Manager uses ``pyproject.toml`` to define project configurations and dependencies.
A typical project will look like:

.. code-block:: toml

   [tool.belay]
   name = "my_project_name"

   [tool.belay.dependencies]
   some_dependency = "https://github.com/BrianPugh/some-dependency/blob/main/some_dependency.py"

Belay assumes the project contains a python-package (folder) with the same name as ``tool.belay.name``.
This directory is synced (in addition to dependencies) when ``belay install`` is ran.

Dependencies
------------
To add python dependencies to a project, specify them in the ``tool.belay.dependencies`` section.
This section contains a mapping of package names to URIs where they can be fetched from.
There isn't a strong centralized micropython package repository, so Belay relies on directly specifying python file URLs.
Belay supports several dependency values:

1. A string to a local file/folder path:

   .. code-block:: toml

      pathlib = "../micropython-lib/python-stdlib/pathlib/pathlib.py"
      os = "../micropython-lib/python-stdlib/os/os"

2. A github link to a single file or a folder:

   .. code-block:: toml

      pathlib = "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/pathlib/pathlib.py"
      os = "https://github.com/micropython/micropython-lib/tree/master/python-stdlib/os/os"

3. A dictionary with a detailed specification:

   .. code-block:: toml

      pathlib = {uri="../micropython-lib/python-stdlib/pathlib/pathlib.py", develop=true}

4. A list of any of the above if multiple files are required for a single package:

   .. code-block:: toml

      os = [
          "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/os/os/__init__.py",
          "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/os-path/os/path.py",
      ]

   This is most common for packages that have optional submodules.

Support for other types can be added. Please open up a github issue if Belay doesn't support a desired file source.

If specifying a dependency via dictionary, the following fields are available:

* ``uri`` - local or remote path to fetch data from. **Must** be provided.

* ``develop`` - Dependency is in "editable" mode. The dependency source is directly used during ``belay install``.
  Primarily used for a local dependency actively under development.
  Defaults to ``False``.

Groups
~~~~~~
Belay supports groups of dependencies, allowing subsets of dependencies to be used in different situations.
To declare a new dependency group, use a ``tool.poetry.group.<group>`` section where ``<group>`` is the name of a dependency group.
``dev`` is a common dependency group including packages like ``unittest``.

.. code-block:: toml

   [tool.belay.group.dev.dependencies]
   unittest = [
       "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/unittest/unittest/__init__.py",
       "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/unittest-discover/unittest/__main__.py",
   ]

By default, all dependency groups are installed to device.
A dependency group can be marked as optional, meaning it won't be installed during a ``belay install`` call unless explicitly specified ``belay install --with=dev``.

.. code-block:: toml

   [tool.belay.group.dev]
   optional = true

All dependency groups are available to a host micropython interpreter via ``belay run micropython``.
See the `run`_ command section for more details.

Pytest
~~~~~~
Since micropython and normal python code logic are mostly interoperable, code can be tested using ``pytest`` by adding the Belay dependency folder(s) to pytest's configuration:

.. code-block:: toml

   [tool.pytest.ini_options]
   pythonpath = ".belay/dependencies/main .belay/dependencies/dev"


We recommend structuring projects to abstract hardware and micropython-specific features so that the majority
of code can be tested with ``pytest`` using normal desktop CPython or ``unittest`` with desktop micropython.
This will inherently produce better structured, more robust code and improve development iteration speed.

CLI Commands
^^^^^^^^^^^^
This section describes all the commands available via ``belay``.
To get help from the command-line, add ``--help`` to any command for more information.

new
---
Creates a new directory structure suitable as a starting point for most belay projects.

.. code-block:: bash

   belay new my-project

The project structure is as follows:

.. code-block:: text

   my-project/
   ├─ my-project/
   │  └─ __init__.py
   ├─ pyproject.toml
   └─ README.md


update
------
Updates dependencies specified in  ``pyproject.toml``.

.. code-block:: bash

   belay update

By default, the downloaded dependencies are stored in ``.belay/dependencies/<group>/``.
The ``.belay/`` folder **should be committed** to git and can be thought of as a dependency lock file.

Belay **will not** perform any dependency solving.
It will only download the dependencies explicitly specified in the ``pyproject.toml``.
If a dependency itself has dependencies, they must be explicitly added to ``pyproject.toml``.

By default, all dependencies are updated.
To update only specific dependencies, list them as such:

.. code-block:: bash

   belay update pathlib itertools

Previously downloaded dependencies that are no longer referenced in ``tool.belay.dependencies`` are automatically deleted.

install
-------
Syncs the project and dependencies to device.

.. code-block:: bash

   belay install [PORT]

To additionally sync a script to ``/main.py``, specify the script using the ``--main`` option.
After flashing, the device will be reset and the ``main`` script will execute.

.. code-block:: bash

   belay install [PORT] --main main.py

The output of the ``main`` script can be monitored after flashing by including the ``--follow`` flag.
Cancel the running script and exit the monitor via ``ctrl-c``.

.. code-block:: bash

   belay install [PORT] --main main.py --follow

During development, it is often convenient to specify a script to run without actually syncing it to ``/main.py``.
For this, specify the script using the ``--run`` option.
The output will always be monitored.

.. code-block:: bash

   belay install [PORT] --run main.py

To include a dependency group that has been declared optional, add the ``--with`` option.

.. code-block:: bash

   belay install [PORT] --with dev

run
---
The ``run`` command serves 2 purposes:

1. Run a python script on-device.

2. Run a local executable in a pseudo-micropython-virtual-environment.

Running a Script on Device
~~~~~~~~~~~~~~~~~~~~~~~~~~
When developing a script, it is often useful to edit it on-host and then execute it on-device.
This helps circumvent issues with a flaky device filesystem.
In the following command, ``my_script.py`` is executed on-device without explicitly writing it to the device's filesystem.

.. code-block:: bash

   belay run [PORT] my_script.py

Virtual Environment
~~~~~~~~~~~~~~~~~~~
If the first argument after ``run`` is an executable, Belay will instead execute the remainder of the command after setting some environment variables.
Namely, Belay will set the environment variable ``MICROPYPATH`` to all of the dependency groups' folders.
This makes all of the dependencies accessible to a ``micropython`` binary, making it easier to test micropython code on-host.

.. code-block:: bash

   belay run micropython my_script.py

This is not a true virtual environment; currently the ``micropython`` binary must be externally supplied.

clean
-----
Removes any previously downloaded dependencies no longer specified in ``tool.belay.dependecies``.

.. code-block:: bash

   belay clean

``clean`` is automatically invoked at the end of ``belay update``,
so this command will usually **not** be necessary.

cache
-----
Belay keeps a cache of files that aid when downloading and updating dependencies.
The location of this cache depends on the operating system:

* Windows: ``%LOCALAPPDATA%\belay``

* MacOS: ``~/Library/Caches/belay``

* Linux: ``~/.cache/belay``

info
~~~~
Displays Belay's cache location and other metadata.

.. code-block:: bash

   $ belay cache info
   Location: /Users/brianpugh/Library/Caches/belay
   Elements: 1
   Total Size: 3.84MB

list
~~~~
Lists all the items Belay is currently caching.

.. code-block:: bash

   $ belay cache list
   git-github-micropython-micropython-lib

clear
~~~~~
Deletes all cached items that begin with the provided prefix

.. code-block:: bash

   belay cache clear

For example, to delete all ``git`` caches, use the command:

.. code-block:: bash

   belay cache clear git


To clear **all** caches, specify the ``--all`` flag.

.. code-block:: bash

   belay cache clear --all

By default, Belay will display an interactive prompt to confirm the clearing action.
This confirmation prompt can be bypassed by specifying the ``--yes`` flag.

.. code-block:: bash

   belay cache clear --all --yes

terminal
--------
Opens up an interactive terminal with the device.
Press ``ctrl-]`` to exit the terminal.

.. code-block:: bash

   belay terminal [PORT]

select
------
Interactive menu for selecting a usb-connected micropython board.
Helps identify and appropriate `UsbSpecifier`; particularly useful when interacting with multiple boards.

.. code-block:: bash

   belay select

Example output:

.. code-block:: bash

   $ belay select
   ? Select USB Device (Use arrow keys):
      vid    pid    serial_number      manufacturer       product            location
    » 11914  5      e6614c311b137637   MicroPython        Board in FS mode   0-1.1.3.1

   Implementation(name='micropython', version=(1, 19, 1), platform='rp2', emitters=('native', 'viper'))
   ? Blink LED Pin Number [skip]?


   Either set the BELAY_DEVICE environment variable:
       export BELAY_DEVICE='{"vid": 11914, "pid": 5, "serial_number": "e6614c311b137637", "manufacturer": "MicroPython", "product": "Board in FS mode", "location": "0-1.1.3.1"}'
   And in python code, instantiate Device without arguments:
       device = belay.Device()

   Or, add the following (or a subset) to your python code:
       spec = belay.UsbSpecifier(vid=11914, pid=5, serial_number='e6614c311b137637', manufacturer='MicroPython', product='Board in FS mode', location='0-1.1.3.1')
       device = belay.Device(spec)

Q&A
^^^

How does Belay's package manager compare to ``mip``?
----------------------------------------------------
Mip and Belay have different design goals and associated restrictions.
Mip is designed to be ran on micropython, and is thusly restricted by available libraries.
Belay is designed to be ran on full desktop python (e.g. cpython) to provide support to a micropython environment.
The closest tool to Belay's Package Manager would actually be ``mpremote mip``.
With this tool you can specify remote files via a json configuration file.

Belay aims to provide a more robust, friendly experience by the following:

1. Use the standard ``pyproject.toml`` file for configurations and dependency specifications.

2. Make project robust to third-party changes by caching dependencies in-project.
   Your project won't become non-functional due to a remote dependency gone missing.
   Your project won't unexpectedly break due to a dependency change
   unless ``belay update`` is ran to update dependencies.
   Changes can be easily revertted due to git versioning.

3. Options to minify or compile code prior to sending it to device.
   This encourages more comments and docstrings.

What limitations does Belay's package manager have?
---------------------------------------------------
* Belay currently does not currently support manifest.py_, but that may
  change in the future.

* Dependencies are not recursively searched/solved; if a dependency
  has it's own dependencies, you must add them yourself to your
  ``pyproject.toml``.

Why should I commit ``.belay`` to my git repository?
----------------------------------------------------
The ``.belay/`` folder primarily contains cached micropython dependencies.

Cached dependencies are to be included in your git repo because:

1. Micropython libraries are inherently small due to their operating conditions.
   Adding them to the git repo is not an unreasonable burden.

2. The project will continue to work, even if an upstream dependency goes missing.

3. A lot of micropython libraries don't implement versioning, so more complicated
   dependency solving isn't feasible. Caching "known working" versions is the only
   convenient way of guaranteeing a repeatable deployment.


.. _manifest.py: https://docs.micropython.org/en/latest/reference/manifest.html
