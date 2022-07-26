Example 04: Thread
==================

The REPL loop that Belay interacts with is constantly blocking, waiting for new code.
If you wish to run a loop in the background, and if your board supports it, you can use the ``thread`` decorator to run a single function in the background.

Like the ``task`` decorator, the ``thread`` decorator sends the function's code over to the device.
Explicitly invoking the function, ``run_led_loop(0.5)``, will spawn the thread on-device and execute the function.
``run_led_loop`` will return immediately for the host, and other tasks like ``read_temeprature`` can still be executed.

Functions decorated with ``thread`` are more difficult to debug, since their exceptions won't be caught be Belay.
