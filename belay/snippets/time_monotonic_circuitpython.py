import supervisor
__belay_monotonic = supervisor.ticks_ms

_BELAY_TICKS_MAX = (1<<29)-1
_BELAY_TICKS_HALFPERIOD = (1<<28)

def __belay_ticks_add(ticks, delta):
    return (ticks + delta) & _BELAY_TICKS_MAX

def __belay_ticks_diff(ticks1, ticks2):
    diff = (ticks1 - ticks2) & _BELAY_TICKS_MAX
    diff = ((diff + _BELAY_TICKS_HALFPERIOD) & _BELAY_TICKS_MAX) - _BELAY_TICKS_HALFPERIOD
    return diff
