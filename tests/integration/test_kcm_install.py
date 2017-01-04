from . import integration
import os
import tempfile


def test_kcm_install():
    # Install kcm to a temporary directory.
    install_dir = tempfile.mkdtemp()
    integration.execute(integration.kcm(),
                        ["install",
                         "--install-dir={}".format(install_dir)])
    installed_kcm = os.path.join(install_dir, "kcm")

    # Check installed kcm executable output against the original script.
    assert (integration.execute(installed_kcm, ["--help"]) ==
            integration.execute(integration.kcm(), ["--help"]))
    assert (integration.execute(installed_kcm, ["--version"]) ==
            integration.execute(integration.kcm(), ["--version"]))

    integration.execute("rm", [installed_kcm])
