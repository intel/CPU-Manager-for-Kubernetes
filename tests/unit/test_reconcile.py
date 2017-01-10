from .. import helpers
from intel import config, reconcile, proc


def test_set_equals_empty():
    assert reconcile.set_equals([], [])
    assert not reconcile.set_equals([], ["foo"])
    assert not reconcile.set_equals(["foo"], [])


def test_set_equals_same():
    assert reconcile.set_equals(["foo"], ["foo"])
    assert reconcile.set_equals([1, 3, 5], [1, 3, 5])


def test_set_equals_subsets():
    assert reconcile.set_equals(["foo"], ["foo"])
    assert not reconcile.set_equals([1, 2, 3, 4, 5], [1, 3, 5])
    assert not reconcile.set_equals([1, 3, 5], [1, 2, 3, 4, 5])


def test_set_equals_disjoint():
    assert not reconcile.set_equals(["foo", "bar"], ["baz", "buzz"])
    assert not reconcile.set_equals([1, 3, 5], [2, 4, 6])


def test_is_cpuset_mismatch_empty_set(monkeypatch):
    p = proc.Process(1)

    monkeypatch.setattr(p, "cpus_allowed", lambda: [])

    assert(not reconcile.is_cpuset_mismatch(p, []))


def test_is_cpuset_mismatch_equal_sets(monkeypatch):
    p = proc.Process(1)

    # Set with one cpu.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1])

    assert(not reconcile.is_cpuset_mismatch(p, [1]))

    # Set with two cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1, 2])

    assert(not reconcile.is_cpuset_mismatch(p, [1, 2]))


def test_is_cpuset_mismatch_subsets(monkeypatch):
    p = proc.Process(1)

    # Current allowed is a subset of desired allowed cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [2, 3, 4])

    assert(reconcile.is_cpuset_mismatch(p, [1, 2, 3, 4, 5]))

    # Desired allowed is a subset of current allowed cpus.
    monkeypatch.setattr(p, "cpus_allowed", lambda: [1, 2, 3, 4, 5])

    assert(reconcile.is_cpuset_mismatch(p, [2, 3, 4]))


def test_generate_report(monkeypatch):
    monkeypatch.setenv(proc.ENV_PROC_FS, helpers.procfs_dir("cpuset_mismatch"))
    conf = config.Config(helpers.conf_dir("cpuset_mismatch"))
    report = reconcile.generate_report(conf)

    assert report.reclaimed_cpu_lists() == []

    expected_mismatches = [
        reconcile.Mismatch(1003, "pool2", "4,5", [4, 5, 6]),
        reconcile.Mismatch(1010, "pool3", "9,10", [7, 8]),
        reconcile.Mismatch(1040, "pool3", "9,10", [9, 10, 11, 20]),
        reconcile.Mismatch(1005, "pool3", "7,8", [7])]

    for e in expected_mismatches:
        assert e in report.mismatched_cpu_masks()
