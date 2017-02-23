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
