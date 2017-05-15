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
