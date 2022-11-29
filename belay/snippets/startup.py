import os, sys
def __belay(name):
    def inner(f):
        def func_wrapper(*args, **kwargs):
            res = f(*args, **kwargs)
            print("_BELAYR" + repr(res))
            return res
        def gen_wrapper(*args, **kwargs):
            send_val = None
            gen = f(*args, **kwargs)
            try:
                while True:
                    res = gen.send(send_val)
                    print("_BELAYR" + repr(res))
                    send_val = yield res
            except StopIteration:
                pass
        globals()["_belay_" + name] = gen_wrapper if isinstance(f, type(lambda: (yield))) else func_wrapper
        return f
    return inner
def __belay_gen_next(x, val):
    try:
        x.send(val)
    except StopIteration:
        print("_BELAYS")
