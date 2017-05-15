# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
