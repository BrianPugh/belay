import os, sys
__belay_obj_counter=0
def __belay_next(x, val):
    try:
        return x.send(val)
    except StopIteration:
        print("_BELAYS")
def __belay_obj_create(result):
    global __belay_obj_counter
    globals()["__belay_obj_" + str(__belay_obj_counter)] = result
    print("_BELAYR"+str(__belay_obj_counter)+"|")
    __belay_obj_counter += 1
