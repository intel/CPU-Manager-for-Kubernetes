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

import subprocess


class Socket:
    def __init__(self, socket_id, cores=None):
        if not cores:
            cores = {}
        self.socket_id = socket_id
        self.cores = cores

    def as_dict(self):
        return {
            "id": self.socket_id,
            "cores": [c.as_dict() for c in self.cores.values()]
        }


class Core:
    def __init__(self, core_id, cpus=None):
        if not cpus:
            cpus = {}
        self.core_id = core_id
        self.cpus = cpus
        self.pool = None

    def cpu_ids(self):
        cpus = []
        for cpu_id in self.cpus:
            cpus.append(cpu_id)

        return cpus

    def is_isolated(self):
        if len(self.cpus) == 0:
            return False

        for cpu_id in self.cpus:
            if not self.cpus[cpu_id].isolated:
                return False

        return True

    def as_dict(self):
        return {
            "id": self.core_id,
            "pool": self.pool,
            "cpus": [c.as_dict() for c in self.cpus.values()]
        }


class CPU:
    def __init__(self, cpu_id):
        self.cpu_id = cpu_id
        self.isolated = False

    def as_dict(self):
        return {
            "id": self.cpu_id,
            "isolated": self.isolated,
        }


# Returns of map of socket id (integer) to sockets (Socket type).
# lscpu has the following format:
# # The following is the parsable format, which can be fed to other
# # programs. Each different item in every column has an unique ID
# # starting from zero.
# # CPU,Core,Socket,Node,,L1d,L1i,L2,L3
# 0,0,0,0,,0,0,0,0
# 1,1,0,0,,1,1,1,0
def parse(lscpu_output, isolated_cpus=[]):
    sockets = {}
    for line in lscpu_output.split("\n"):
        if not line.startswith("#") and len(line) > 0:
            cpuinfo = line.split(",")

            socket_id = int(cpuinfo[2])
            core_id = int(cpuinfo[1])
            cpu_id = int(cpuinfo[0])

            if socket_id not in sockets:
                sockets[socket_id] = Socket(socket_id)

            socket = sockets[socket_id]

            if core_id not in socket.cores:
                socket.cores[core_id] = Core(core_id)

            core = socket.cores[core_id]

            if cpu_id not in core.cpus:
                core.cpus[cpu_id] = CPU(cpu_id)

            cpu = core.cpus[cpu_id]

            if cpu_id in isolated_cpus:
                cpu.isolated = True

    return sockets


# Returns list of isolated cpu ids from content in /proc/cmdline.
def isolcpus(cmdline):
    cpus = []

    # Ensure that newlines are removed.
    cmdline_stripped = cmdline.rstrip()

    cmdline_fields = cmdline_stripped.split()
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


def lscpu():
    cmd_out = subprocess.check_output("lscpu -p", shell=True)
    return cmd_out.decode("UTF-8")
