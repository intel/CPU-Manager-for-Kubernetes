from intel import config, util
import os
import tempfile


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
