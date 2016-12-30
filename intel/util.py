from os.path import normpath, realpath, join, pardir


def kcm_root():
    return normpath(realpath(join(__file__, pardir, pardir)))
