from . import integration
from .. import helpers
import os
import tempfile


def test_kcm_install():
    # Install kcm to a temporary directory.
    install_dir = tempfile.mkdtemp()
    helpers.execute(integration.kcm(),
                    ["install",
                     "--install-dir={}".format(install_dir)])
    installed_kcm = os.path.join(install_dir, "kcm")

    # Check installed kcm executable output against the original script.
    assert (helpers.execute(installed_kcm, ["--help"]) ==
            helpers.execute(integration.kcm(), ["--help"]))
    assert (helpers.execute(installed_kcm, ["--version"]) ==
            helpers.execute(integration.kcm(), ["--version"]))

    helpers.execute("rm", [installed_kcm])
