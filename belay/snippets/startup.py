import os, sys
def __belay(name):
    def inner(f):
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
        if isinstance(f, type(lambda: (yield))):
            globals()["_belay_" + name] = gen_wrapper
        return f
    return inner
def __belay_gen_next(x, val):
    try:
        x.send(val)
    except StopIteration:
        print("_BELAYS")
