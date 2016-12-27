from intel import config, util

import os


data = os.path.join(util.kcm_root(), "tests", "data")


def test_config_pools():
    c = config.Config(os.path.join(data, "config", "ok"))
    with c.lock():
        pools = c.pools()
        assert len(pools) == 3
        assert "controlplane" in pools
        assert "dataplane" in pools
        assert "infra" in pools


def test_pool_name():
    c = config.Config(os.path.join(data, "config", "ok"))
    with c.lock():
        pools = c.pools()
        assert pools["controlplane"].name() == "controlplane"
        assert pools["dataplane"].name() == "dataplane"
        assert pools["infra"].name() == "infra"


def test_pool_exclusive():
    c = config.Config(os.path.join(data, "config", "ok"))
    with c.lock():
        pools = c.pools()
        assert not pools["controlplane"].exclusive()
        assert pools["dataplane"].exclusive()
        assert not pools["infra"].exclusive()


def test_pool_cpu_lists():
    c = config.Config(os.path.join(data, "config", "ok"))
    with c.lock():
        pools = c.pools()
        clists = pools["dataplane"].cpu_lists()
        assert len(clists) == 4
        assert len(clists["4,12"].tasks()) == 1
        assert 2000 in clists["4,12"].tasks()
