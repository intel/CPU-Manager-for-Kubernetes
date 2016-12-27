import logging
from os.path import normpath, realpath, join, pardir


def kcm_root():
    return normpath(realpath(join(__file__, pardir, pardir)))


def check_hugepages():
    fd = open("/proc/meminfo", "r")
    content = fd.read()
    lines = content.split("\n")
    for line in lines:
        if line.startswith("HugePages_Free"):
            parts = line.split()
            num_free = int(parts[1])
            if num_free == 0:
                logging.warning("Warning: no hugepages are free")
