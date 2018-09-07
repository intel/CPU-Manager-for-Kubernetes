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

from . import integration
from .. import helpers
from intel import proc, topology
import os
import pytest
import tempfile
import subprocess


# Physical CPU cores on the first socket.
cores = topology.parse(topology.lscpu()).get_socket(0).cores

proc_env_ok = {
    proc.ENV_PROC_FS: helpers.procfs_dir("ok"),
    topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
}


def test_cmk_init():
    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    helpers.execute(integration.cmk(), args, proc_env_ok)


def test_cmk_init_exists():
    args = ["init",
            "--conf-dir={}".format(helpers.conf_dir("minimal"))]

    with pytest.raises(subprocess.CalledProcessError):
        helpers.execute(integration.cmk(), args, proc_env_ok)


def test_cmk_init_wrong_assignment():
    args = ["init",
            "--socket-id=-1",
            "--num-exclusive-cores=1",
            "--num-shared-cores=1",
            "--conf-dir={}".format(helpers.conf_dir("ok"))]

    with pytest.raises(subprocess.CalledProcessError) as e:
        helpers.execute(integration.cmk(), args, proc_env_ok)

    assert "ERROR:root:4 exclusive cores (1 requested)" in str(e.value.output)


def test_cmk_init_insufficient_isolated_cores():
    proc_env_few_isolated = {
        proc.ENV_PROC_FS: helpers.procfs_dir("insufficient_isolated_cores"),
        topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
    }

    args = ["init", "--conf-dir={}".format(
        os.path.join(tempfile.mkdtemp(), "init"))]

    with pytest.raises(subprocess.CalledProcessError) as e:
        helpers.execute(integration.cmk(), args, proc_env_few_isolated)

    assert (
        "ERROR:root:Cannot use isolated cores for "
        "exclusive and shared cores: not enough isolated") in \
        str(e.value.output)


def test_cmk_init_isolated_cores_mismatch():
    proc_env_isolated_mismatch = {
        proc.ENV_PROC_FS: helpers.procfs_dir("isolated_core_mismatch"),
        topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
    }

    args = ["init",
            "--socket-id=-1",
            "--num-exclusive-cores=1",
            "--num-shared-cores=1",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    output = helpers.execute(
        integration.cmk(), args, proc_env_isolated_mismatch)

    assert ("WARNING:root:Not all isolated cores will be used "
            "by exclusive and shared pools") in str(output)


def test_cmk_init_partial_isolation():
    proc_env_partially_isolated = {
        proc.ENV_PROC_FS: helpers.procfs_dir("partially_isolated_cores"),
        topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
    }

    args = ["init",
            "--socket-id=-1",
            "--num-exclusive-cores=1",
            "--num-shared-cores=1",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    output = helpers.execute(
        integration.cmk(), args, proc_env_partially_isolated)

    assert "WARNING:root:Physical core 1 is partially isolated" in str(output)
    assert "WARNING:root:Physical core 2 is partially isolated" in str(output)


def test_cmk_init_insufficient_cores():
    args = ["init",
            "--socket-id=-1",
            "--num-exclusive-cores=10",
            "--num-shared-cores=5",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    with pytest.raises(subprocess.CalledProcessError) as e:
        helpers.execute(integration.cmk(), args, proc_env_ok)

    assert ("ERROR:root:10 cores requested for exclusive. "
            "Only 8 cores available") in str(e.value.output)


def test_cmk_init_isolcpus():
    proc_env_partially_isolated = {
        proc.ENV_PROC_FS: helpers.procfs_dir("correctly_isolated_cores"),
        topology.ENV_LSCPU_SYSFS: helpers.sysfs_dir("xeon_d")
    }

    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    output = helpers.execute(
        integration.cmk(), args, proc_env_partially_isolated)

    print(output)

    assert "INFO:root:Isolated logical cores: 0,1,2,3,4,8,9,10,11,12" \
           in str(output)

    assert "INFO:root:Isolated physical cores: 0,1,2,3,4" in str(output)

    assert "INFO:root:Adding cpu list 0,8 from socket 0 to exclusive pool." \
           in str(output)
    assert "INFO:root:Adding cpu list 1,9 from socket 0 to exclusive pool." \
           in str(output)
    assert "INFO:root:Adding cpu list 2,10 from socket 0 to exclusive pool." \
           in str(output)
    assert "INFO:root:Adding cpu list 3,11 from socket 0 to exclusive pool." \
           in str(output)

    assert "INFO:root:Adding cpu list 4,12 to shared pool." \
           in str(output)

    assert "INFO:root:Adding cpu list 5,13,6,14,7,15 to infra pool." \
           in str(output)
