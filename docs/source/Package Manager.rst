Package Manager
===============

The Belay CLI includes a package manager that downloads MicroPython libraries and syncs them to your device alongside your project code.

Why Use a Package Manager?
^^^^^^^^^^^^^^^^^^^^^^^^^^

MicroPython and CircuitPython devices have their own filesystem where your code and libraries must be stored.
Many MicroPython libraries lack formal versioning and packaging—they're often just Python files in a GitHub
repository rather than published packages on an index. MicroPython's built-in mip_ tool can install
packages, but it doesn't provide a way to record your project's dependencies in a configuration file—you
have to remember which packages to install. It also fetches fresh copies each time, meaning your project
could break if an upstream dependency changes or disappears.

Belay's package manager solves these challenges:

* **Simplified deployment** — Automatically sync your code and dependencies to the device with a single command.
* **Reproducibility** — Downloaded dependencies are cached locally and committed to your git repository.
  Your project will continue to work even if an upstream library changes or goes offline.
* **Consistency** — Every team member and every deployment uses the exact same dependency versions.

How It Works
^^^^^^^^^^^^

The Belay Package Manager follows this workflow:

1. **Configure** — Define your dependencies in ``pyproject.toml`` (commonly from the MicroPython package index,
   GitHub, or GitLab).
2. **Download** — Run ``belay update`` to fetch dependencies into the ``.belay/dependencies/`` folder.
   This folder should be committed to git—think of it as a lock file that captures exact dependency versions.
3. **Sync** — Run ``belay install`` to transfer dependencies and your project code to the device.

Configuration
^^^^^^^^^^^^^

Belay's Package Manager uses ``pyproject.toml`` to define project configurations and dependencies,
following modern Python packaging conventions. A minimal project configuration looks like:

.. code-block:: toml

   [tool.belay]
   name = "my_project_name"

   [tool.belay.dependencies]
   some_dependency = "https://github.com/BrianPugh/some-dependency/blob/main/some_dependency.py"

Belay assumes the project contains a python-package (folder) with the same name as ``tool.belay.name``.
This directory is synced (in addition to dependencies) when ``belay install`` is ran.

Package Index Settings
~~~~~~~~~~~~~~~~~~~~~~
When using MicroPython index packages, Belay uses ``https://micropython.org/pi/v2`` by default.
You can customize this behavior with the following settings:

.. code-block:: toml

   [tool.belay]
   # Custom package index URLs (tried in order)
   package_indices = ["https://micropython.org/pi/v2"]

   # MicroPython version for index lookups
   # "py" for pure Python, "6" for .mpy format version 6, etc.
   mpy_version = "py"

Dependencies
~~~~~~~~~~~~

To add Python dependencies to your project, specify them in the ``tool.belay.dependencies`` section.
Each entry maps a package name to a source location where Belay can fetch it.
Belay supports several source types, from the official MicroPython package index to GitHub repositories and local files:

1. **MicroPython package index** - Packages from the official MicroPython package index.
   Dependencies are automatically resolved recursively:

   .. code-block:: toml

      # Concise syntax (recommended)
      aiohttp = "*"           # latest version
      ntptime = "latest"      # explicit latest
      requests = "1.0.0"      # specific version

      # Explicit syntax (also supported)
      aiohttp = "aiohttp"
      ntptime = "mip:ntptime"
      requests = "requests@1.0.0"

   The ``*`` wildcard or ``"latest"`` fetches the newest version. Exact versions like ``"1.0.0"``
   are also supported. The ``mip:`` prefix and ``@version`` suffix are optional.

   .. note::

      Version ranges (e.g., ``"^1.0.0"``, ``">=1.0"``) are **not** supported.
      Use ``"*"`` for latest or specify an exact version.

2. **GitHub/GitLab** - Either shorthand or full URLs:

   .. code-block:: toml

      # Shorthand syntax
      pathlib = "github:micropython/micropython-lib/python-stdlib/pathlib/pathlib.py"
      mylib = "github:user/repo@v1.0"
      mylib = "gitlab:user/repo/path/to/file.py@develop"

      # Full URLs
      pathlib = "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/pathlib/pathlib.py"

3. **Local file/folder path**:

   .. code-block:: toml

      pathlib = "../micropython-lib/python-stdlib/pathlib/pathlib.py"
      os = "../micropython-lib/python-stdlib/os/os"

4. **Dictionary with detailed specification**:

   .. code-block:: toml

      pathlib = {uri="../micropython-lib/python-stdlib/pathlib/pathlib.py", develop=true}

   Available fields:

   * ``uri`` - local or remote path to fetch data from. **Required**.

   * ``develop`` - Dependency is in "editable" mode. The dependency source is directly used during ``belay install``.
     Primarily used for a local dependency actively under development.
     Defaults to ``False``.

5. **List of sources** for packages requiring multiple files:

   .. code-block:: toml

      os = [
          "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/os/os/__init__.py",
          "https://github.com/micropython/micropython-lib/blob/master/python-stdlib/os-path/os/path.py",
      ]

   This is most common for packages that have optional submodules.

Support for other types can be added. Please open up a GitHub issue if Belay doesn't support a desired file source.

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
See the ``run`` command section below for more details.

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
The typical workflow is:

1. ``belay new my-project`` — Create a new project (one-time setup)
2. ``belay update`` — Download dependencies after editing ``pyproject.toml``
3. ``belay install [PORT]`` — Sync everything to your device

To get help from the command-line, add ``--help`` to any command for more information.

new
~~~
Creates a new project structure or adds Belay configuration to an existing project.

.. code-block:: bash

   belay new [PATH]

If ``PATH`` is omitted, defaults to the current directory. If a ``pyproject.toml`` already exists,
Belay adds the necessary ``[tool.belay]`` and ``[tool.belay.dependencies]`` sections to it.
Otherwise, it creates a new project with the following structure:

.. code-block:: text

   my-project/
   ├─ my-project/
   │  └─ __init__.py
   ├─ pyproject.toml
   └─ README.md


update
~~~~~~
Updates dependencies specified in  ``pyproject.toml``.

.. code-block:: bash

   belay update

By default, the downloaded dependencies are stored in ``.belay/dependencies/<group>/``.
The ``.belay/`` folder **should be committed** to git and can be thought of as a dependency lock file.

For MicroPython index packages (plain names or ``mip:`` URIs), Belay automatically resolves and downloads
transitive dependencies recursively. For other URI types (GitHub URLs, local paths, etc.), dependencies
must be explicitly added to ``pyproject.toml``.

By default, all dependencies are updated.
To update only specific dependencies, list them as such:

.. code-block:: bash

   belay update pathlib itertools

Previously downloaded dependencies that are no longer referenced in ``tool.belay.dependencies`` are automatically deleted.

install
~~~~~~~
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
~~~
The ``run`` command serves 2 purposes:

1. Run a python script on-device.

2. Run a local executable in a pseudo-micropython-virtual-environment.

Running a Script on Device
--------------------------
When developing a script, it is often useful to edit it on-host and then execute it on-device.
This helps circumvent issues with a flaky device filesystem.
In the following command, ``my_script.py`` is executed on-device without explicitly writing it to the device's filesystem.

.. code-block:: bash

   belay run [PORT] my_script.py

Virtual Environment
-------------------
If the first argument after ``run`` is an executable, Belay will instead execute the remainder of the command after setting some environment variables.
Namely, Belay will set the environment variable ``MICROPYPATH`` to all of the dependency groups' folders.
This makes all of the dependencies accessible to a ``micropython`` binary, making it easier to test micropython code on-host.

.. code-block:: bash

   belay run micropython my_script.py

This is not a true virtual environment; currently the ``micropython`` binary must be externally supplied.

clean
~~~~~
Removes any previously downloaded dependencies no longer specified in ``tool.belay.dependencies``.

.. code-block:: bash

   belay clean

``clean`` is automatically invoked at the end of ``belay update``,
so this command will usually **not** be necessary.

cache
~~~~~
Belay keeps a cache of files that aid when downloading and updating dependencies.
The location of this cache depends on the operating system:

* Windows: ``%LOCALAPPDATA%\belay``

* MacOS: ``~/Library/Caches/belay``

* Linux: ``~/.cache/belay``

info
----
Displays Belay's cache location and other metadata.

.. code-block:: bash

   $ belay cache info
   Location: /Users/brianpugh/Library/Caches/belay
   Elements: 1
   Total Size: 3.84MB

list
----
Lists all the items Belay is currently caching.

.. code-block:: bash

   $ belay cache list
   git-github-micropython-micropython-lib

clear
-----
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
~~~~~~~~
Opens up an interactive terminal with the device.
Press ``ctrl-]`` to exit the terminal.

.. code-block:: bash

   belay terminal [PORT]

select
~~~~~~
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

This section answers common questions about Belay's package manager design decisions.

How does Belay's package manager compare to ``mip`` and ``mpremote mip``?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MicroPython provides two built-in tools for package management:

* **mip** — Runs directly on the MicroPython device (requires network connectivity).
  Install packages with ``import mip; mip.install("pkgname")``.

* **mpremote mip** — Runs on your desktop and installs packages to a connected device over USB/UART.
  Install packages with ``mpremote mip install pkgname``.

Both tools fetch packages from the micropython-lib_ index
or from GitHub/GitLab URLs, and both support a ``package.json`` format for defining multi-file packages with dependencies.

**Where Belay differs:**

Belay's package manager is designed around **reproducibility** and **offline-first workflows**:

1. **Local dependency caching** — Dependencies are downloaded once to ``.belay/dependencies/`` and committed to git.
   This acts as a lock file: your project continues to work even if upstream packages change or disappear.
   With ``mip``/``mpremote mip``, packages are fetched fresh each time, so your project could break
   if a dependency is updated or removed.

2. **Standard Python tooling** — Belay uses ``pyproject.toml`` for all configuration, following modern Python
   packaging conventions. The MicroPython ecosystem is exploring ``pyproject.toml`` support, but it's not yet available.

3. **Pre-processing options** — Belay can minify or compile (``.mpy``) code before syncing to the device,
   reducing flash usage and improving import times while keeping your source code readable and well-documented.

4. **Integrated project sync** — ``belay install`` syncs both dependencies *and* your project code in one command,
   with smart delta transfers that only send changed files.

Why should I commit ``.belay`` to my git repository?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``.belay/`` folder acts as a lock file, ensuring every team member uses the exact same dependency versions.
It also protects your project from upstream changes or deletions—many MicroPython libraries lack formal versioning.
MicroPython libraries are small, so the repository overhead is negligible.


.. _mip: https://docs.micropython.org/en/latest/reference/packages.html
.. _micropython-lib: https://github.com/micropython/micropython-lib
