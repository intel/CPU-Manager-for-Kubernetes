from . import integration
from intel import init
import os
import pytest
import tempfile


@pytest.mark.skipif(len(init.discover_topo()) < 6,
                    reason="requires at least 6 physical cores to pass")
def test_kcm_init():
    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    integration.execute(integration.kcm(), args)
