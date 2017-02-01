# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
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
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
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
# corrections, enhancements or other input ("Feedback") related to the Software
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
import collections
import logging
import subprocess
import sys


def init(conf_dir, num_dp_cores, num_cp_cores):
    check_hugepages()
    cpumap = discover_topo()

    logging.info("Writing config to {}.".format(conf_dir))
    logging.info("Requested data plane cores = {}.".format(num_dp_cores))
    logging.info("Requested control plane cores = {}.".format(num_cp_cores))

    try:
        c = config.new(conf_dir)
    except FileExistsError:
        logging.info("Configuration directory already exists.")
        c = config.Config(conf_dir)

        num_dp_lists = len(c.pools("dataplane").cpu_lists())
        num_cp_lists = len(c.pools("controlplane").cpu_lists())

        alloc_error = None

        if num_dp_lists is not num_dp_cores:
            alloc_error = True
            logging.error("{} dataplane cores ({} requested)".format(
                num_dp_lists, num_dp_cores))
        if num_cp_lists is not num_cp_cores:
            alloc_error = True
            logging.error("{} controlplane cores ({} requested)".format(
                num_cp_lists, num_cp_cores))

        if alloc_error:
            sys.exit(1)

        return

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
