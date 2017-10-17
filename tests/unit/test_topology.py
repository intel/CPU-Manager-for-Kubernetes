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

    cmdline = ("BOOT_IMAGE=/boot/vmlinuz-4.4.14-040414-generic "
               "root=/dev/md2 ro net.ifnames=0 "
               "isolcpus=0,1,2,3,8,9,10,11,15-18")

    assert topology.parse_isolcpus(cmdline) == [0, 1, 2, 3, 8, 9, 10, 11, 15,
                                                16, 17, 18]

    cmdline = ("BOOT_IMAGE=/boot/vmlinuz-4.4.14-040414-generic "
               "root=/dev/md2 ro net.ifnames=0 "
               "isolcpus=0,1,2,3,8,9,10,11,10-13")

    assert topology.parse_isolcpus(cmdline) == [0, 1, 2, 3, 8, 9, 10, 11, 12,
                                                13]


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


def test_topology_isolated_two_sockets():
    lscpu = """# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2
0,0,0,,,0,0,0
1,1,0,,,1,1,1
2,2,0,,,2,2,2
3,3,0,,,3,3,3
4,0,0,,,4,4,4
5,1,0,,,5,5,5
6,2,0,,,6,6,6
7,3,0,,,7,7,7
8,0,1,,,8,8,8
9,1,1,,,9,9,9
10,2,1,,,10,10,10
11,3,1,,,11,11,11
12,0,1,,,12,12,12
13,1,1,,,13,13,13
14,2,1,,,14,14,14
15,3,1,,,15,15,15
"""

    isolated_cpus = [0, 4, 1, 5, 8, 12, 10, 14]
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) == 2

    cores = sockets.get_cores()

    assert len(cores) == 8
    for core in cores:
        assert core.core_id >= 0
        assert core.core_id < 16
    assert cores[0].cpu_ids() == [0, 4]
    assert cores[0].is_isolated()
    assert cores[1].cpu_ids() == [1, 5]
    assert cores[1].is_isolated()
    assert cores[2].cpu_ids() == [2, 6]
    assert not cores[2].is_isolated()
    assert cores[3].cpu_ids() == [3, 7]
    assert not cores[3].is_isolated()
    assert cores[4].cpu_ids() == [8, 12]
    assert cores[4].is_isolated()
    assert cores[5].cpu_ids() == [9, 13]
    assert not cores[5].is_isolated()
    assert cores[6].cpu_ids() == [10, 14]
    assert cores[6].is_isolated()
    assert cores[7].cpu_ids() == [11, 15]
    assert not cores[7].is_isolated()

    isolated_cores = sockets.get_isolated_cores()
    assert len(isolated_cores) == 4
    for core in isolated_cores:
        assert core.cpu_ids() in [[0, 4], [1, 5], [8, 12], [10, 14]]
        assert core.cpu_ids() not in [[2, 6], [3, 7], [9, 13], [11, 15]]

    # Verify that partially isolated physical cores (where only a subset of
    # the physical core's hyperthreads are in the isolated list) are not
    # reported as isolated.
    isolated_cpus = [0, 1]
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) is 2
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 0

    # Test case where all discovered cores are isolated.
    isolated_cpus = list(range(8))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) is 2
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4

    # Test case where superset of discovered cores are isolated.
    isolated_cpus = list(range(9))
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) is 2
    cores = sockets.get_socket(0).cores.values()
    assert len(cores) is 4
    assert len([c for c in cores if c.is_isolated()]) is 4

    assert sockets.get_socket(3) is None


def test_topology_cores_get_modes():
    lscpu = """# The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2
0,0,0,0,,0,0,0
1,0,0,0,,1,1,0
2,1,0,0,,2,2,1
3,1,0,0,,3,3,1
4,2,0,0,,4,4,2
5,2,0,0,,5,5,2
6,3,0,0,,6,6,3
7,3,0,0,,7,7,3
8,4,1,0,,8,8,4
9,4,1,0,,9,9,4
10,5,1,0,,10,10,5
11,5,1,0,,11,11,5
12,6,1,0,,12,12,6
13,6,1,0,,13,13,6
14,7,1,0,,14,14,7
15,7,1,0,,15,15,7
"""

    isolated_cpus = [0, 1, 2, 3, 8, 9, 10, 11]
    sockets = topology.parse(lscpu, isolated_cpus)
    assert len(sockets.sockets) == 2

    cores = sockets.get_cores(mode="spread")

    assert cores[0].core_id == 0
    assert cores[1].core_id == 4
    assert cores[2].core_id == 1
    assert cores[3].core_id == 5

    cores = sockets.get_cores(mode="packed")
    assert cores[0].core_id == 0
    assert cores[1].core_id == 1
    assert cores[2].core_id == 2
    assert cores[3].core_id == 3

    cores = sockets.get_cores(mode="unknown")
    assert cores[0].core_id == 0
    assert cores[1].core_id == 1
    assert cores[2].core_id == 2
    assert cores[3].core_id == 3

    cores = sockets.get_isolated_cores(mode="spread")
    for core in cores:
        print(core.cpu_ids())
    assert cores[0].core_id == 0
    assert cores[1].core_id == 4
    assert cores[2].core_id == 1
    assert cores[3].core_id == 5

    cores = sockets.get_isolated_cores(mode="packed")
    for core in cores:
        print(core.cpu_ids())
    assert cores[0].core_id == 0
    assert cores[1].core_id == 1
    assert cores[2].core_id == 4
    assert cores[3].core_id == 5

    cores = sockets.get_isolated_cores(mode="unknown")
    for core in cores:
        print(core.cpu_ids())
    assert cores[0].core_id == 0
    assert cores[1].core_id == 1
    assert cores[2].core_id == 4
    assert cores[3].core_id == 5
