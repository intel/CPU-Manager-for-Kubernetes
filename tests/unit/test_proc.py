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
