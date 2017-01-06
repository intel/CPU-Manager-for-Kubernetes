from intel import reconcile, proc


def test_is_cpuset_mismatch_empty_set(monkeypatch):
    p = proc.Process(1)

    def cpus_allowed(): return []
    monkeypatch.setattr(p, 'cpus_allowed', cpus_allowed)

    assert(not reconcile.is_cpuset_mismatch(p, set()))


def test_is_cpuset_mismatch_equal_sets(monkeypatch):
    p = proc.Process(1)

    # Set with one cpu.
    def cpus_allowed(): return [1]
    monkeypatch.setattr(p, 'cpus_allowed', cpus_allowed)

    assert(not reconcile.is_cpuset_mismatch(p, set([1])))

    # Set with two cpus.
    def cpus_allowed(): return [1, 2]
    monkeypatch.setattr(p, 'cpus_allowed', cpus_allowed)

    assert(not reconcile.is_cpuset_mismatch(p, set([1, 2])))


def test_is_cpuset_mismatch_subsets(monkeypatch):
    p = proc.Process(1)

    # Current allowed is a subset of desired allowed cpus.
    def cpus_allowed(): return [2, 3, 4]
    monkeypatch.setattr(p, 'cpus_allowed', cpus_allowed)

    assert(reconcile.is_cpuset_mismatch(p, set([1, 2, 3, 4, 5])))

    # Desired allowed is a subset of current allowed cpus.
    def cpus_allowed(): return [1, 2, 3, 4, 5]
    monkeypatch.setattr(p, 'cpus_allowed', cpus_allowed)

    assert(reconcile.is_cpuset_mismatch(p, set([2, 3, 4])))
