from intel import proc
import pytest


def test_procfs_must_be_set(monkeypatch):
    # Without the environment set for the proc file system, the call should
    # fail.
    with pytest.raises(SystemExit):
        proc.procfs()

    # Setting the variable.
    monkeypatch.setenv(proc.ENV_PROC_FS, "/proc")

    # And calling again, and should not fail.
    proc.procfs()


def test_unfold_empty_cpu_list():
    assert(proc.unfold_cpu_list("") == [])


def test_unfold_valid_cpu_lists():
    assert(proc.unfold_cpu_list("0") == [0])
    assert(proc.unfold_cpu_list("0-1") == [0, 1])
    assert(proc.unfold_cpu_list("0-1,4") == [0, 1, 4])
    assert(proc.unfold_cpu_list("0-1,4-6") == [0, 1, 4, 5, 6])
    assert(proc.unfold_cpu_list("0-1,4-6,9") == [0, 1, 4, 5, 6, 9])
    assert(proc.unfold_cpu_list("0-1,4-6,9-10") == [0, 1, 4, 5, 6, 9, 10])
    assert(proc.unfold_cpu_list("0,1,4,5,6,9,10") == [0, 1, 4, 5, 6, 9, 10])


def test_unfold_invalid_cpu_lists():
    with pytest.raises(ValueError):
        proc.unfold_cpu_list(",")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,1-")

    with pytest.raises(ValueError):
        proc.unfold_cpu_list("0,1-2,")
