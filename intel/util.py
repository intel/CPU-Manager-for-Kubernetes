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

import logging
import re

from os.path import normpath, realpath, join, pardir


def cmk_root():
    return normpath(realpath(join(__file__, pardir, pardir)))


def ldh_convert_check(name):
    name_con = re.sub(r'[^-a-z0-9]', '-', name.lower())
    logging.info("Converted \"{}\" to \"{}\" for"
                 " TPR name".format(name, name_con))
    if not re.fullmatch('[a-z0-9]([-a-z0-9]*[a-z0-9])?', name_con):
        logging.error("Cant create valid TPR name using "
                      "\"{}\" - must match regex "
                      "[a-z0-9]([-a-z0-9]*[a-z0-9])?".format(name_con))
        exit(1)
    return name_con
