import sys
def __belay(name):
    def inner(f):
        def func_wrapper(*args, **kwargs):
            res = f(*args, **kwargs)
            print("_BELAYR" + repr(res))
            return res
        def gen_wrapper(*args, **kwargs):
            for res in f(*args, **kwargs):
                print("_BELAYR" + repr(res))
                yield res
        globals()["_belay_" + name] = gen_wrapper if isinstance(f, type(lambda: (yield))) else func_wrapper
    return inner
def __belay_gen_next(x):
    try:
        next(x)
    except StopIteration:
        print("_BELAYS")
