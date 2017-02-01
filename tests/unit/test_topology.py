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

from intel import topology


def test_init_topology_one_core():
    lscpu = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
"""

    sockets = topology.parse(lscpu)
    assert len(sockets) is 1

    cores = sockets[0].cores
    assert len(cores) is 1
    assert 0 in cores
    assert cores[0].cpu_ids() == [0]


def test_init_topology_two_cores():
    lscpu = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
"""

    sockets = topology.parse(lscpu)
    assert len(sockets) == 1

    cores = sockets[0].cores
    assert len(cores) == 2
    assert 0 in cores
    assert 1 in cores
    assert cores[0].cpu_ids() == [0]
    assert cores[1].cpu_ids() == [1]


def test_init_topology_one_socket():
    lscpu = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
2,2,0,0,,2,2,2,0
3,3,0,0,,3,3,3,0
4,0,0,0,,0,0,0,0
5,1,0,0,,1,1,1,0
6,2,0,0,,2,2,2,0
7,3,0,0,,3,3,3,0
"""

    sockets = topology.parse(lscpu)
    assert len(sockets) == 1

    cores = sockets[0].cores
    assert len(cores) == 4
    assert 0 in cores
    assert 1 in cores
    assert 2 in cores
    assert 3 in cores
    assert cores[0].cpu_ids() == [0, 4]
    assert cores[1].cpu_ids() == [1, 5]
    assert cores[2].cpu_ids() == [2, 6]
    assert cores[3].cpu_ids() == [3, 7]


def test_parse_isolcpus_invalid_input():
    assert topology.parse_isolcpus("") == []
    assert topology.parse_isolcpus("a") == []
    assert topology.parse_isolcpus("a b") == []
    assert topology.parse_isolcpus("a b\n") == []
    assert topology.parse_isolcpus("a b c\nA B C") == []
    assert topology.parse_isolcpus("a b=7 c\nA B C") == []
    assert topology.parse_isolcpus("a b=7 c=7,8,9\nA B C") == []
    assert topology.parse_isolcpus("a b=7 c=7, 8,9\nA B C") == []


def test_parse_isolcpus_valid_input():
    cmdline = ("BOOT_IMAGE=/boot/vmlinuz-4.4.14-040414-generic "
               "root=/dev/md2 ro net.ifnames=0 isolcpus=0,1,2,3,8,9,10,11")

    assert topology.parse_isolcpus(cmdline) == [0, 1, 2, 3, 8, 9, 10, 11]


def test_topology_isolated_one_socket():
    lscpu = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
2,2,0,0,,2,2,2,0
3,3,0,0,,3,3,3,0
4,0,0,0,,0,0,0,0
5,1,0,0,,1,1,1,0
6,2,0,0,,2,2,2,0
7,3,0,0,,3,3,3,0
"""

    isolated_cpus = [0, 4, 1, 5]
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets) == 1

    cores = sockets[0].cores

    assert len(cores) == 4
    assert 0 in cores
    assert 1 in cores
    assert 2 in cores
    assert 3 in cores
    assert cores[0].cpu_ids() == [0, 4]
    assert cores[0].is_isolated()
    assert cores[1].cpu_ids() == [1, 5]
    assert cores[1].is_isolated()
    assert cores[2].cpu_ids() == [2, 6]
    assert not cores[2].is_isolated()
    assert cores[3].cpu_ids() == [3, 7]
    assert not cores[3].is_isolated()

    # Verify that partially isolated physical cores (where only a subset of
    # the physical core's hyperthreads are in the isolated list) are not
    # reported as isolated.
    isolated_cpus = [0, 1]
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets) is 1
    cores = sockets[0].cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 0

    # Test case where all discovered cores are isolated.
    isolated_cpus = list(range(8))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets) is 1
    cores = sockets[0].cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4

    # Test case where superset of discovered cores are isolated.
    isolated_cpus = list(range(9))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets) is 1
    cores = sockets[0].cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4
