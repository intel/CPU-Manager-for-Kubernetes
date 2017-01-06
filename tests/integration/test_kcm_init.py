from . import integration
from .. import helpers
from intel import init
import os
import pytest
import tempfile
import subprocess


@pytest.mark.skipif(len(init.discover_topo()) >= 6,
                    reason="""skipping negative test if enough physical
                              cores are available""")
def test_kcm_init_insufficient_cores():
    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    # Expect to fail if system has insufficient number of cores.
    with pytest.raises(subprocess.CalledProcessError):
        helpers.execute(integration.kcm(), args)


@pytest.mark.skipif(len(init.discover_topo()) < 6,
                    reason="""skipping test if system has insufficient
                              number of physical cores""")
def test_kcm_init():
    args = ["init",
            "--conf-dir={}".format(os.path.join(tempfile.mkdtemp(), "init"))]

    helpers.execute(integration.kcm(), args)
