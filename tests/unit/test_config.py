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
        foo.add_socket("0")
        bar.add_socket("0")
        assert len(c.pools()) == 2
        c0 = foo.add_cpu_list("0", "0-3")
        c1 = bar.add_cpu_list("0", "4-7")
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


def test_write_config_already_exists_error():
    fake_path = os.path.join(tempfile.mkdtemp(), "fake_conf")
    config.new(fake_path)
    with pytest.raises(FileExistsError):
        config.new(fake_path)


def test_add_pool_already_exists_error():
    c = config.new(os.path.join(tempfile.mkdtemp(), "fake_conf"))
    with c.lock():
        assert len(c.pools()) == 0
        c.add_pool("foo", True)
        assert len(c.pools()) == 1
        with pytest.raises(KeyError):
            c.add_pool("foo", True)
        assert len(c.pools()) == 1


def test_add_cpu_list_already_exists():
    c = config.new(os.path.join(tempfile.mkdtemp(), "fake_conf"))
    with c.lock():
        foo = c.add_pool("foo", True)
        foo.add_socket("0")
        foo.add_cpu_list("0", "0-3")
        assert len(foo.cpu_lists("0")) == 1
        with pytest.raises(KeyError):
            foo.add_cpu_list("0", "0-3")
        # TODO: what about 0,1,2,3?
        # with pytest.raises(KeyError):
        #     foo.add_cpu_list("0", "0,1,2,3")
        assert len(foo.cpu_lists("0")) == 1


def test_pool_as_dict():
    path = os.path.join(tempfile.mkdtemp(), "fake_conf")
    c = config.new(path)
    exp_result = {
        'cpuLists': {
            '0-3': {
                'cpus': '0-3',
                'tasks': [10]
            },
            '4-7': {
                'cpus': '4-7',
                'tasks': [11]
            }
        },
        'exclusive': True,
        'name': 'foo'
    }
    with c.lock():
        foo = c.add_pool("foo", True)
        foo.add_socket("0")
        foo.add_socket("1")
        c0 = foo.add_cpu_list("0", "0-3")
        c1 = foo.add_cpu_list("1", "4-7")
        c0.add_task(10)
        c1.add_task(11)
    assert exp_result == foo.as_dict()


def test_config_as_dict():
    path = os.path.join(tempfile.mkdtemp(), "fake_conf")
    exp_result = {
        'path': path,
        'pools': {
            'bar': {
                'cpuLists': {
                    '4-7': {
                        'cpus': '4-7',
                        'tasks': [6]
                    }
                },
                'exclusive': True,
                'name': 'bar'
            },
            'foo': {
                'cpuLists': {
                    '0-3': {
                        'cpus': '0-3',
                        'tasks': [5]
                    }
                },
                'exclusive': False,
                'name': 'foo'
            }
        }
    }
    c = config.new(path)
    with c.lock():
        foo = c.add_pool("foo", False)
        bar = c.add_pool("bar", True)
        foo.add_socket("0")
        bar.add_socket("0")
        c0 = foo.add_cpu_list("0", "0-3")
        c1 = bar.add_cpu_list("0", "4-7")
        c0.add_task(5)
        c1.add_task(6)
    assert exp_result == c.as_dict()
