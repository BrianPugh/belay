import os, sys
def __belay_gen_next(x, val):
    try:
        return x.send(val)
    except StopIteration:
        print("_BELAYS")
