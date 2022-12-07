import os, sys
def __belay_next(x, val):
    try:
        return x.send(val)
    except StopIteration:
        print("_BELAYS")
