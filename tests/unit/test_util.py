import os

from intel import util


def test_kcm_root():
    result = util.kcm_root()
    assert os.path.isdir(os.path.join(result, "tests", "data"))


def test_discover_topo():
    cpumap = util.discover_topo()
    assert len(cpumap) > 0


def test_parse_topo():
    input1 = """#The following is the parsable format, which can be fed to other
# programs. Each different item in every column has an unique ID
# starting from zero.
# CPU,Core,Socket,Node,,L1d,L1i,L2,L3
0,0,0,0,,0,0,0,0
1,1,0,0,,1,1,1,0
"""
    input2 = """#The following is the parsable format, which can be fed to other
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
    cpumap = util.parse_topo(input1)
    assert len(cpumap) == 2
    assert "0" in cpumap
    assert "1" in cpumap

    cpumap = util.parse_topo(input2)
    assert len(cpumap) == 4
    assert "0" in cpumap
    assert "1" in cpumap
    assert "2" in cpumap
    assert "3" in cpumap
    assert cpumap["0"] == "0,4"
    assert cpumap["1"] == "1,5"
    assert cpumap["2"] == "2,6"
    assert cpumap["3"] == "3,7"
