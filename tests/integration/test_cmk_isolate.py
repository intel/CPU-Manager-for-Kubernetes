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

from .. import helpers
from . import integration
from intel import config
from intel import proc
import os
import psutil
import pytest
import subprocess
import tempfile


proc_env = {proc.ENV_PROC_FS: "/proc"}


def test_cmk_isolate_child_env():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=shared",
            "env | grep CMK"]

    assert helpers.execute(integration.cmk(), args, proc_env) == b"""\
CMK_CPUS_ASSIGNED=0
CMK_CPUS_ASSIGNED_MASK=1
CMK_CPUS_SHARED=0
CMK_PROC_FS=/proc
"""


def test_cmk_isolate_child_env_infra():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal_infra")),
            "--pool=shared",
            "env | grep CMK"]

    assert helpers.execute(integration.cmk(), args, proc_env) == b"""\
CMK_CPUS_ASSIGNED=1
CMK_CPUS_ASSIGNED_MASK=2
CMK_CPUS_SHARED=1
CMK_CPUS_INFRA=0
CMK_PROC_FS=/proc
"""


def test_cmk_isolate_shared():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=shared",
            "echo",
            "--",
            "foo"]

    assert helpers.execute(integration.cmk(), args, proc_env) == b"foo\n"


def test_cmk_isolate_exclusive():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=exclusive",
            "echo",
            "--",
            "foo"]

    assert helpers.execute(integration.cmk(), args, proc_env) == b"foo\n"


def test_cmk_isolate_saturated():
    args = ["isolate",
            "--pool=exclusive",
            "echo",
            "--",
            "foo"]

    with pytest.raises(subprocess.CalledProcessError):
        assert helpers.execute(integration.cmk(), args, proc_env)


"""def test_cmk_isolate_sigkill():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "isolate")
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("minimal"),
         "{}".format(conf_dir)])

    c = config.Config(conf_dir)

    fifo = helpers.rand_str()
    helpers.execute("mkfifo", [fifo])

    p = subprocess.Popen([
            integration.cmk(),
            "isolate",
            "--pool=shared",
            "echo 1 > {} && sleep 300".format(fifo)])
    cmk = psutil.Process(p.pid)
    # Wait for subprocess to exist
    helpers.execute("cat {}".format(fifo))
    clist = c.pool("shared").cpu_list("0", "0")
    assert cmk.pid in clist.tasks()

    # Send sigkill to cmk
    cmk.kill()
    # Wait for cmk process to exit
    cmk.wait()
    assert cmk.pid in clist.tasks()
    helpers.execute("rm {}".format(fifo))


def test_cmk_isolate_sigterm():
    temp_dir = tempfile.mkdtemp()
    conf_dir = os.path.join(temp_dir, "isolate")
    helpers.execute(
        "cp",
        ["-r",
         helpers.conf_dir("minimal"),
         "{}".format(conf_dir)])

    c = config.Config(conf_dir)

    fifo = helpers.rand_str()
    helpers.execute("mkfifo", [fifo])

    p = subprocess.Popen([
            integration.cmk(),
            "isolate",
            "--pool=shared",
            "echo 1 > {} && sleep 300".format(fifo)])
    cmk = psutil.Process(p.pid)
    # Wait for subprocess to exist
    helpers.execute("cat {}".format(fifo))
    clist = c.pool("shared").cpu_list("0", "0")
    assert cmk.pid in clist.tasks()

    # Send sigterm to cmk
    cmk.terminate()
    # Wait for cmk process to terminate
    cmk.wait()
    assert cmk.pid not in clist.tasks()
    helpers.execute("rm {}".format(fifo))"""


def test_cmk_isolate_multiple_cores_exclusive():
    env = {proc.ENV_PROC_FS: "/proc", "CMK_NUM_CORES": "2"}
    args = ["isolate",
            "--pool=exclusive",
            "env | grep CMK"]

    assert helpers.execute(integration.cmk(), args, env) == b"""\
CMK_CPUS_ASSIGNED=0,1
CMK_CPUS_ASSIGNED_MASK=3
CMK_CPUS_SHARED=0
CMK_PROC_FS=/proc
CMK_NUM_CORES=2
"""


def test_cmk_isolate_multiple_cores_shared():
    env = {proc.ENV_PROC_FS: "/proc", "CMK_NUM_CORES": "2"}
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal_multi")),
            "--pool=shared",
            "env | grep CMK"]

    assert helpers.execute(integration.cmk(), args, env) == b"""\
CMK_CPUS_ASSIGNED=0
CMK_CPUS_ASSIGNED_MASK=1
CMK_CPUS_SHARED=0
CMK_PROC_FS=/proc
CMK_NUM_CORES=2
"""


def test_cmk_isolate_multiple_cores_failed():
    env = {proc.ENV_PROC_FS: "/proc", "CMK_NUM_CORES": "3"}
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal_multi")),
            "--pool=exclusive",
            "env | grep CMK"]

    # should fail - there are only 2 cpuslists in that pool
    with pytest.raises(subprocess.CalledProcessError):
        assert helpers.execute(integration.cmk(), args, env)
