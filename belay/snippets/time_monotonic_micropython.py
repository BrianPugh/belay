import time
def __belay_time_monotonic():
    return time.ticks_ms() / 1000.0
