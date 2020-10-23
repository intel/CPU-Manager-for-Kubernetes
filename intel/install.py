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
    cmk_path = os.path.join(util.cmk_root(), "cmk.py")
    # Using pyinstaller: http://www.pyinstaller.org
    # to produce an x86-64 ELF executable named `cmk` in the
    # supplied installation directory.
    subprocess.check_call(
        ["pyinstaller", "--onefile", "--distpath={}"
         .format(install_dir), cmk_path])
    logging.info("Installed cmk to {}".format(install_dir))
