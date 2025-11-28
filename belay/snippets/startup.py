import os, sys, time
__belay_obj_counter=0
def __belay_next(x, val):
    try:
        return x.send(val)
    except StopIteration:
        print("_BELAYS")
def __belay_timed_repr(expr):
    t1=__belay_monotonic()
    result=repr(expr)
    t2=__belay_monotonic()
    diff=__belay_ticks_diff(t2,t1)
    avg=__belay_ticks_add(t1,diff>>1)
    return str(avg)+"|"+result
def __belay_obj_create(result):
    t = str(__belay_monotonic())
    if isinstance(result, (int, float, str, bool, bytes, type(None))):
        print("_BELAYR|"+t+"|"+repr(result))
    else:
        global __belay_obj_counter
        globals()["__belay_obj_" + str(__belay_obj_counter)] = result
        print("_BELAYR"+str(__belay_obj_counter)+"|"+t+"|")
        __belay_obj_counter += 1
