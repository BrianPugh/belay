def __belay_ilistdir(x):
    for name in os.listdir(x):
        stat = os.stat(x + "/" + name)  # noqa: PL116
        yield (name, stat[0], stat[1])
