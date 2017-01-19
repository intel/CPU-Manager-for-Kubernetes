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

from .. import helpers
from intel import config
import os
import pytest
import tempfile
import time


def test_config_max_lock_seconds(monkeypatch):
    monkeypatch.setenv(config.ENV_LOCK_TIMEOUT, 1)
    assert config.max_lock_seconds() == 1
    monkeypatch.setenv(config.ENV_LOCK_TIMEOUT, 5)
    assert config.max_lock_seconds() == 5
    monkeypatch.delenv(config.ENV_LOCK_TIMEOUT)
    assert config.max_lock_seconds() == 30


def test_config_lock_timeout(monkeypatch):
    max_wait = 2
    monkeypatch.setenv(config.ENV_LOCK_TIMEOUT, 0.1)
    with pytest.raises(KeyboardInterrupt):
        with config.Config(helpers.conf_dir("ok")).lock():
            time.sleep(max_wait)


def test_config_pools():
    c = config.Config(helpers.conf_dir("ok"))
    with c.lock():
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools


def test_pool_name():
    c = config.Config(helpers.conf_dir("ok"))
    with c.lock():
        pools = c.pools()
        assert pools["controlplane"].name() == "controlplane"
        assert pools["dataplane"].name() == "dataplane"
        assert pools["infra"].name() == "infra"


def test_pool_exclusive():
    c = config.Config(helpers.conf_dir("ok"))
    with c.lock():
        pools = c.pools()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()


def test_pool_cpu_lists():
    c = config.Config(helpers.conf_dir("ok"))
    with c.lock():
        pools = c.pools()
        clists = pools["dataplane"].cpu_lists()
        assert len(clists) == 4
        assert len(clists["4,12"].tasks()) == 1
        assert 2000 in clists["4,12"].tasks()


def test_write_config():
    c = config.new(os.path.join(tempfile.mkdtemp(), "conf"))
    with c.lock():
        assert len(c.pools()) == 0
        foo = c.add_pool("foo", False)
        bar = c.add_pool("bar", True)
        assert len(c.pools()) == 2
        c0 = foo.add_cpu_list("0-3")
        c1 = bar.add_cpu_list("4-7")
        assert c0.cpus() == "0-3"
        assert c1.cpus() == "4-7"
        c0.add_task(5)
        assert 5 in c0.tasks()
        c0.add_task(6)
        assert 5 in c0.tasks()
        assert 6 in c0.tasks()
        c0.remove_task(5)
        assert 5 not in c0.tasks()
        assert 6 in c0.tasks()
