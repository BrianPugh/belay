All commands are to be ran at this root of this project.

To build the integration tester image:

.. code-block:: bash

   make integration-build

Alternatively, simply clone the rp2040js repo into the root of this project
and follow it's readme. In summary:

.. code-block:: bash

   # in the root Belay directory.
   git clone https://github.com/wokwi/rp2040js.git
   cd rp2040js
   curl -OJ https://micropython.org/resources/firmware/rp2-pico-20210902-v1.17.uf2
   npm install

Once built, run:

.. code-block:: bash

   make integration-test

or, more explicitly:

.. code-block:: bash

   poetry run python -m pytest tests/integration
