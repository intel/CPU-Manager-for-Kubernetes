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


def test_kcm_isolate_child_env():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=shared",
            "env | grep KCM"]

    assert helpers.execute(integration.kcm(), args, proc_env) == b"""\
KCM_PROC_FS=/proc
KCM_CPUS_ASSIGNED=0
"""


def test_kcm_isolate_shared():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=shared",
            "echo",
            "--",
            "foo"]

    assert helpers.execute(integration.kcm(), args, proc_env) == b"foo\n"


def test_kcm_isolate_exclusive():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("minimal")),
            "--pool=exclusive",
            "echo",
            "--",
            "foo"]

    assert helpers.execute(integration.kcm(), args, proc_env) == b"foo\n"


def test_kcm_isolate_saturated():
    args = ["isolate",
            "--conf-dir={}".format(helpers.conf_dir("saturated")),
            "--pool=dataplane",
            "echo",
            "--",
            "foo"]

    with pytest.raises(subprocess.CalledProcessError):
        assert helpers.execute(integration.kcm(), args, proc_env)
    # with pytest.raises(subprocess.CalledProcessError) as exinfo:
    #     assert b"No free cpu lists in pool dataplane" in exinfo.value.output


def test_kcm_isolate_pid_bookkeeping():
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
            integration.kcm(),
            "isolate",
            "--conf-dir={}".format(conf_dir),
            "--pool=shared",
            "echo 1 > {} && cat {}".format(fifo, fifo)])
    kcm = psutil.Process(p.pid)
    # Wait for subprocess to exist
    helpers.execute("cat {}".format(fifo))
    clist = c.pool("shared").cpu_list("0")
    assert kcm.pid in clist.tasks()
    # Signal subprocess to exit
    helpers.execute("echo 1 > {}".format(fifo))
    # Wait for kcm process to terminate
    kcm.wait()
    assert kcm.pid not in clist.tasks()
    helpers.execute("rm {}".format(fifo))


def test_kcm_isolate_sigkill():
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
            integration.kcm(),
            "isolate",
            "--conf-dir={}".format(conf_dir),
            "--pool=shared",
            "echo 1 > {} && sleep 300".format(fifo)])
    kcm = psutil.Process(p.pid)
    # Wait for subprocess to exist
    helpers.execute("cat {}".format(fifo))
    clist = c.pool("shared").cpu_list("0")
    assert kcm.pid in clist.tasks()

    # Send sigkill to kcm
    kcm.kill()
    # Wait for kcm process to exit
    kcm.wait()
    assert kcm.pid in clist.tasks()
    helpers.execute("rm {}".format(fifo))


def test_kcm_isolate_sigterm():
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
            integration.kcm(),
            "isolate",
            "--conf-dir={}".format(conf_dir),
            "--pool=shared",
            "echo 1 > {} && sleep 300".format(fifo)])
    kcm = psutil.Process(p.pid)
    # Wait for subprocess to exist
    helpers.execute("cat {}".format(fifo))
    clist = c.pool("shared").cpu_list("0")
    assert kcm.pid in clist.tasks()

    # Send sigterm to kcm
    kcm.terminate()
    # Wait for kcm process to terminate
    kcm.wait()
    assert kcm.pid not in clist.tasks()
    helpers.execute("rm {}".format(fifo))
