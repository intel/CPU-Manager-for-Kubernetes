# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from intel import topology


def test_init_topology_one_core():
    lscpu = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
"""

    sockets = topology.parse(lscpu)
    assert len(sockets.sockets) is 1

    cores = sockets.get_socket(0).cores
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
    assert len(sockets.sockets) == 1

    cores = sockets.get_socket(0).cores
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
    assert len(sockets.sockets) == 1

    cores = sockets.get_socket(0).cores
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
    assert len(sockets.sockets) == 1

    cores = sockets.get_socket(0).cores

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
    assert len(sockets.sockets) is 1
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 0

    # Test case where all discovered cores are isolated.
    isolated_cpus = list(range(8))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) is 1
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4

    # Test case where superset of discovered cores are isolated.
    isolated_cpus = list(range(9))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) is 1
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4
