import os, sys
def __belay_next(x, val):
    try:
        return x.send(val)
    except StopIteration:
        print("_BELAYS")
def __belay_get_obj_by_id(id_):
    for v in globals().values():
        if id_ == id(v):
            return v
    raise ValueError
def __belay_print(result):
    print("_BELAYR"+str(id(result))+"|"+repr(result))
