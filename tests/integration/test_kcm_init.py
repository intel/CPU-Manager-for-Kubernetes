from . import integration
import os
import pytest
import tempfile
import subprocess


def test_kcm_init():
    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]
    with pytest.raises(subprocess.CalledProcessError):
        integration.execute(integration.kcm(), args)
