from . import config
import collections
import logging
import subprocess


def init(conf_dir, num_dp_cores, num_cp_cores):
    check_hugepages()
    cpumap = discover_topo()
    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))
    c = config.new(conf_dir)
    with c.lock():
        logging.info("Adding dataplane pool.")
        dp = c.add_pool("dataplane", True)
        for i in range(int(num_dp_cores)):
            if not cpumap:
                raise KeyError("No more cpus left to assign for data plane")
            k, v = cpumap.popitem()
            logging.info("Adding {} cpus to the dataplane pool.".format(v))
            dp.add_cpu_list(v)
        logging.info("Adding controlplane pool.")
        cp = c.add_pool("controlplane", False)
        cpus = ""
        for i in range(int(num_cp_cores)):
            if not cpumap:
                raise KeyError("No more cpus left to assign for control plane")
            k, v = cpumap.popitem()
            if cpus:
                cpus = cpus + "," + v
            else:
                cpus = v
        logging.info("Adding {} cpus to the controlplane pool.".format(cpus))
        cp.add_cpu_list(cpus)
        logging.info("Adding infra pool.")
        infra = c.add_pool("infra", False)
        cpus = ""
        if not cpumap:
            raise KeyError("No more cpus left to assign for infra")
        for k, v in cpumap.items():
            if cpus:
                cpus = cpus + "," + v
            else:
                cpus = v
        logging.info("Adding {} cpus to the infra pool.".format(cpus))
        infra.add_cpu_list(cpus)


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


# Discover cpu topology (physical to logical core mapping).
def discover_topo():
    cmd_out = subprocess.check_output("lscpu -p", shell=True)
    return parse_topo(cmd_out.decode("UTF-8"))


# Returns a map between physical and logical cpu cores using
# `lscpu -p` output.
# `lscpu -p` output has the following format:
# # The following is the parsable format, which can be fed to other
# # programs. Each different item in every column has an unique ID
# # starting from zero.
# # CPU,Core,Socket,Node,,L1d,L1i,L2,L3
# 0,0,0,0,,0,0,0,0
# 1,1,0,0,,1,1,1,0
def parse_topo(topo_output):
    lines = topo_output.split("\n")
    cpumap = collections.OrderedDict()
    for line in lines:
        if not line.startswith("#") and len(line) > 0:
            cpuinfo = line.split(",")
            if cpuinfo[1] in cpumap:
                cpumap[cpuinfo[1]] = cpumap[cpuinfo[1]] + "," + cpuinfo[0]
            else:
                cpumap[cpuinfo[1]] = cpuinfo[0]
    return cpumap
