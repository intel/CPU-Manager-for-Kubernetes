from intel import proc
import pytest
import os


def test_procfs_must_be_set():
    # Without the environment set for the proc file system, the call should
    # fail.
    with pytest.raises(SystemExit):
        proc.procfs()

    # Setting the variable.
    os.environ[proc.ENV_PROC_FS] = "/proc"

    # And calling again, and should not fail.
    proc.procfs()
