import logging
import subprocess
import collections
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
                logging.warning("No hugepages are free")
                return


# Returns a map between physical and logical cpu cores using
# `lscpu -p` output.
# `lscpu -p` output has the following format:
# # The following is the parsable format, which can be fed to other
# # programs. Each different item in every column has an unique ID
# # starting from zero.
# # CPU,Core,Socket,Node,,L1d,L1i,L2,L3
# 0,0,0,0,,0,0,0,0
# 1,1,0,0,,1,1,1,0
def discover_topo():
    cmd_out = subprocess.check_output("lscpu -p", shell=True)
    out = cmd_out.decode("UTF-8")
    lines = out.split("\n")
    cpumap = collections.OrderedDict()
    for line in lines:
        if not line.startswith("#") and len(line) > 0:
            cpuinfo = line.split(",")
            if cpuinfo[1] in cpumap:
                cpumap[cpuinfo[1]] = cpumap[cpuinfo[1]] + "," + cpuinfo[0]
            else:
                cpumap[cpuinfo[1]] = cpuinfo[0]

    return cpumap
