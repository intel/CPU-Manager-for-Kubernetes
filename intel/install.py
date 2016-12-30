from . import util
import logging
import os
import subprocess


def install(install_dir):
    kcm_path = os.path.join(util.kcm_root(), "kcm.py")
    # Using pyinstaller: http://www.pyinstaller.org
    # to produce an x86-64 ELF executable named `kcm` in the
    # supplied installation directory.
    subprocess.check_call(
        "pyinstaller --onefile --distpath={} {}".format(
            install_dir,
            kcm_path),
        shell=True)
    logging.info("Installed kcm to {}".format(install_dir))
