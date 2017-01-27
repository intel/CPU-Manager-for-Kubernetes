# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the “Software”), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell (“Utilize”) this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  “Third Party Programs” are the files
# listed in the “third-party-programs.txt” text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input (“Feedback”) related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.

from . import config
import logging
import subprocess


class Socket:
    def __init__(self, socket_id, cores={}):
        self.socket_id = socket_id
        self.cores = cores

    def __str__(self):
        out = "socket %d has %d cores\n" % (self.socket_id, len(self.cores))

        for core in self.cores.values():
            out += str(core)

        return out


class Core:
    def __init__(self, core_id, cpus={}):
        self.core_id = core_id
        self.cpus = cpus
        self.pool = None

    def is_isolated(self):
        num_isolated_cpus = len(self.isolated_cpus())
        return num_isolated_cpus > 0 and num_isolated_cpus == len(self.cpus)

    def isolated_cpus(self):
        cpus = {}
        for cpu_id in self.cpus:
            if self.cpus[cpu_id].isolated:
                cpus[cpu_id] = self.cpus[cpu_id]

        return cpus

    def cpu_ids(self):
        cpus = []
        for cpu_id in self.cpus:
            cpus.append(cpu_id)

        return cpus

    def __str__(self):
        isolated_string = ""
        if self.is_isolated():
            isolated_string = " and is isolated"

        assigned_string = ""
        if self.pool is not None:
            assigned_string += " is assigned to the %s pool" % self.pool

        out = "core %d%s has %d cpus%s\n" % (
              self.core_id, assigned_string, len(self.cpus), isolated_string)

        for cpu in self.cpus.values():
            out += str(cpu)

        return out


class CPU:
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        self.isolated = False

    def __str__(self):
        isolated_string = "is not isolated"
        if self.isolated:
            isolated_string = "is isolated"

        return "cpu %d %s\n" % (self.cpu_id, isolated_string)


def dfilter(func, d):
    out = {}
    for k, v in d.items():
        if func(v):
            out[k] = v
    return out


def assign_cores(cores, pool, num_cores):
    free_cores = dfilter(lambda core: core.pool is None, cores)
    if len(free_cores) < num_cores:
        logging.fatal("Isolated cores exhausted. "
                      "could not assign %s cores" % pool)

    allocated = 0
    for free_core in free_cores.values():
        free_core.pool = pool

        allocated += 1
        if allocated == num_cores:
            break


def init(conf_dir, num_dp_cores, num_cp_cores):
    check_hugepages()

    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))

    num_dp_cores = int(num_dp_cores)
    num_cp_cores = int(num_cp_cores)

    # TODO: Consider moving into own function.
    sockets = topology(lscpu(), cmdline())

    # We only support one socket for now.
    if len(sockets) != 1:
        logging.fatal("Only single socket systems are supported for now. "
                      "Found %d sockets" % len(sockets))

    socket = sockets[0]
    isolated_cores = dfilter(lambda core: core.is_isolated(), socket.cores)
    num_isolated_cores = len(isolated_cores)
    cores = socket.cores

    if num_isolated_cores > 0:
        if num_isolated_cores < (num_dp_cores + num_cp_cores):
            logging.fatal(
                "Cannot use isolated cores for data plane and control plane "
                "cores: not enough isolated cores %d compared to requested %d"
                % num_isolated_cores, (num_dp_cores + num_cp_cores))

        # Allocate cores for data plane
        assign_cores(isolated_cores, "dp", num_dp_cores)

        # Allocate cores for control plane
        assign_cores(isolated_cores, "cp", num_cp_cores)

        # Allocate non isolated cores for infra
        regular_cores = dfilter(lambda core: not core.is_isolated(),
                                socket.cores)

        assign_cores(regular_cores, "infra", len(regular_cores))

    elif num_isolated_cores == 0:
        # Allocate cores for data plane
        assign_cores(cores, "dp", num_dp_cores)

        # Allocate cores for control plane
        assign_cores(cores, "cp", num_cp_cores)

        # Allocate all free cores for infra
        free_cores = dfilter(lambda core: core.pool is None, socket.cores)
        assign_cores(cores, "infra", len(free_cores))

    def pool_cpu_ids(cores, pool):
        cores = dfilter(lambda core: core.pool == pool, cores)
        core_ids = []
        for core in cores:
            for cpu_id in cores[core].cpu_ids():
                core_ids.append(str(cpu_id))

        return core_ids

    # Write configuration.
    c = config.new(conf_dir)
    with c.lock():
        logging.info("Adding dataplane pool")
        dp = c.add_pool("dataplane", True)
        dp_cores = pool_cpu_ids(cores, "dp")
        dp.add_cpu_list(",".join(dp_cores))

        logging.info("Adding controlplane pool")
        cp = c.add_pool("controlplane", False)
        cp_cores = pool_cpu_ids(cores, "cp")
        cp.add_cpu_list(",".join(cp_cores))

        logging.info("Adding infra pool")
        infra = c.add_pool("infra", False)
        infra_cores = pool_cpu_ids(cores, "infra")
        infra.add_cpu_list(",".join(infra_cores))


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


# Returns output in format:
# ["#", "CPU", "Core", Socket,Node,,L1d,L1i,L2,L3]
# 0,0,0,0,,0,0,0,0
# 1,1,0,0,,1,1,1,0
def lscpu():
    cmd_out = subprocess.check_output("lscpu -p", shell=True)
    lines = cmd_out.decode("UTF-8").split("\n")
    return lines


def cmdline(cmdline_file="/proc/cmdline"):
    cmdline_contents = []

    with open(cmdline_file, "r") as cmdline:
        cmdline_contents = cmdline.readlines()

    return cmdline_contents


def isolcpus(cmdlines=[]):
    cpus = []

    if len(cmdlines) == 0:
        return cpus

    cmdline_fields = cmdlines[0].split(" ")
    for cmdline_field in cmdline_fields:
        pair = cmdline_field.split("=")
        if len(pair) != 2:
            continue

        key = pair[0]
        value = pair[1]

        if key == "isolcpus":
            cpus_str = value.split(",")
            for cpu_id in cpus_str:
                cpus.append(int(cpu_id))

    return cpus


def topology(lscpu_lines=[], cmdlines=[]):
    isolated_cpus = set(isolcpus(cmdlines))

    sockets = {}
    for line in lscpu_lines:
        if not line.startswith("#") and len(line) > 0:
            cpuinfo = line.split(",")

            socket_id = int(cpuinfo[2])
            core_id = int(cpuinfo[1])
            cpu_id = int(cpuinfo[0])

            if socket_id not in sockets:
                logging.info("socket %d not found: adding" % socket_id)
                sockets[socket_id] = Socket(socket_id)

            if core_id not in sockets[socket_id].cores:
                logging.info("core %d not found in socket %d: adding" %
                             (core_id, socket_id))
                sockets[socket_id].cores[core_id] = Core(core_id)

            if cpu_id not in sockets[socket_id].cores[core_id].cpus:
                logging.info("cpu %d not found in core %d: adding" %
                             (cpu_id, core_id))
                sockets[socket_id].cores[core_id].cpus[cpu_id] = CPU(cpu_id)

            if cpu_id in isolated_cpus:
                sockets[socket_id].cores[core_id].cpus[cpu_id].isolated = True

            logging.info("topology: %s", sockets[0])

    return sockets
