Package Manager
===============

The Belay CLI provides functionality for a simple package manager.
In a nutshell, the Belay Package Manager does the following:

1. Reads settings from ``pyproject.toml``. Dependencies are defined by URL's where they can be fetched.
   Commonly these are files hosted on github.
2. Downloads dependencies to the ``.belay/dependencies/main`` folder. This folder should be committed to your
   project's git repository. This allows for repeatable deployment, even if a remote dependency
   goes missing or changes it's API.
3. Syncs the contents of ``.belay/dependencies/main`` to the on-device ``/lib`` folder. This folder is included
   in the on-device ``PATH``.
4. Syncs the contents of your project directory.

Configuration
^^^^^^^^^^^^^
Belay's Package Manager uses ``pyproject.toml`` to define project configurations and dependencies.
A typical project will look like:

.. code-block:: toml

   [tool.belay]
   name = "my_project_name"

   [tool.belay.dependencies]
   some_dependency = "https://github.com/BrianPugh/some-dependency/blob/main/some_dependency.py"

   [tool.pytest.ini_options]
   pythonpath = ".belay/dependencies/main"

Belay assumes your project contains a python-package with the same name as ``tool.belay.name`` located in the root of your project.

If you want to add dependencies to your project, you can specify them in the ``tool.belay.dependencies`` section.
This section contains a mapping of package names to URLs.
There isn't a strong centralized micropython library repository, so Belay relies on directly specifying python file URLs.
A local file may be specified instead of a URL.

The ``tool.pytest.ini_options.pythonpath`` configuration makes cached dependencies available to ``pytest``.
We recommend structuring your project to abstract hardware and micropython-specific features so that the majority
of code can be tested with ``pytest`` using normal desktop CPython. This will inherently produce better structured,
more robust code and improve development iteration speed.

Commands
^^^^^^^^

New
---
``belay new belay-micropython-demo`` creates a new micropython project structure.

Update
------
``belay update`` iterates over and downloads the dependencies defined
in ``tool.belay.dependencies`` of ``pyproject.toml``.
This command should be ran from the root of your project, and is ran when new upstream library changes want to be pulled.
The downloaded dependencies are stored in ``.belay/dependencies/main/`` of the current working directory.
``.belay/dependencies/main/`` should be committed to your git repo and can be thought of as a dependency lock file.

This decision is made because:

1. Micropython libraries are inherently small due to their operating conditions.
   Adding them to the git repo is not an unreasonable burden.

2. The project will still work even if an upstream dependency goes missing.

3. A lot of micropython libraries don't implement versioning, so more complicated
   dependency solving isn't feasible. Caching "known working" versions is the only
   convenient way of guaranteeing a repeatable deployment.

Belay **will not** perform any dependency solving.
It will only download the dependencies specified in the ``pyproject.toml``.
If a dependency itself has dependencies, you must add it to your ``pyproject.toml`` yourself.

By default, all dependencies are updated.
To update only specific dependencies, specify their name(s) as additional argument(s).
Dependencies that are no longer referenced in ``tool.belay.dependencies`` are deleted.
See ``belay update --help`` for more information.

Install
-------
To actually sync your project and dependencies on-device, invoke the ``belay install [PORT]`` command.

To additionally sync a script to ``/main.py``, specify the script using the ``--main`` option.

During development, it is convenient to specify a script to run without actually syncing it to ``/main.py``.
For this, specify the script using the ``--run`` option.

See ``belay install --help`` for more information.

Clean
-----
``belay clean`` will remove any downloaded dependencies if they are no longer specified in ``tool.belay.dependecies``.
``clean`` is automatically invoked at the end of ``belay update``, so you will usually not need to explicitly use this
command.

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
* Currently, only single-file dependencies are allowed.
  Luckily, this appears to be most micropython packages.

* Dependencies are not recursively searched; if a dependency
  has it's own dependencies, you must add them yourself to your
  ``pyproject.toml``.
