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
        print(pools["dataplane"].cpu_lists())
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
