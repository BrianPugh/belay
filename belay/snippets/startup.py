def __belay(f):
    def belay_interface(*args, **kwargs):
        print("_BELAY_R" + repr(f(*args, **kwargs)))
    globals()["_belay_" + f.__name__] = belay_interface
    return f
