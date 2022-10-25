Package Manager
===============

The Belay CLI provides functionality for a simple package manager.

Q&A
^^^

How does Belay's package manager compare to ``mip``?
----------------------------------------------------
Mip requires either:

1. An internet connection on the target board.

2. ``mpremote`` to install from a remote url.

With ``mip``, a project could easily break due to upstream changes.
Belay aims to address the following issues:

1. Options to minify or compile code prior to sending it to device.
   This encourages more comments and docstrings.
2. Make project robust to third-party changes.
   Your project won't become non-functional due to a dependency gone missing.
   Your project won't unexpectedly break due to a dependency change
   unless ``belay update`` is ran to update dependencies.
3. Use ``pyproject.toml`` for configuration instead of a json file.
4. Improve development cycles with simpler pytest integration.


TOML
^^^^

.. code-block:: toml

   [tool.belay]
   name = "my_project_name"
   packages = [
      {include = "my_project_name"}
   ]

   [tool.belay.dependencies]
   some_dependency = "https://github.com/BrianPugh/some-dependency/blob/main/some_dependency.py"

   [pytest.ini_options]
   pythonpath = ".belay-lib"


Commands
^^^^^^^^

update
------
``belay update`` iterates over and downloads the dependencies defined in the
``[tool.belay.dependencies]`` of ``pyproject.toml``.
This command should be ran from the root of your project.
The downloaded dependencies are stored in ``.belay-lib/`` of the current working directory.
``.belay-lib/`` can be committed to your git repo and can be thought of as a dependency
lock file.

This decision is made because:
1. Micropython libraries are inherently small due to their operating conditions.
2. Your project will still work even if an upstream dependency goes missing.
3. A lot of micropython libraries don't implement versioning.

Belay **will not** perform any dependency solving.
It will only download the dependencies specified in the ``pyproject.toml``.
If a dependency itself has dependencies, you must add it to your ``pyproject.toml`` yourself.
Proper dependency solving is hard due to lack of versioning and a central host.
