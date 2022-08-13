API
===

.. autoclass:: belay.Device
   :members:

   .. method:: task(f: Optional[Callable[..., None]] = None, /, minify: bool = True, register: bool = True)

      Decorator that send code to device that executes when decorated function is called on-host.

      :param Callable f: Function to decorate. Can only accept and return python literals.
      :param bool minify: Minify ``cmd`` code prior to sending. Defaults to ``True``.
      :param bool register: Assign an attribute to ``self.task`` with same name as ``f``. Defaults to ``True``.

   .. method:: thread(f: Optional[Callable[..., None]] = None, /, minify: bool = True, register: bool = True)

      Decorator that send code to device that spawns a thread when executed.

      :param Callable f: Function to decorate. Can only accept python literals as arguments.
      :param bool minify: Minify ``cmd`` code prior to sending. Defaults to ``True``.
      :param bool register: Assign an attribute to ``self.thread`` with same name as ``f``. Defaults to ``True``.



.. automodule:: belay
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: Device
