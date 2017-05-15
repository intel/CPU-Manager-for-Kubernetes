#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""prepare_release.py

Usage:
  .release/prepare_release.py
  .release/prepare_release.py -h
  .release/prepare_release.py --help

Information:
  This script based on KCM_RELEASE_VER variable prepares kcm release
  KCM_RELEASE_VER variable should follow pattern vX.Y.Z[-rcV] where
    X,Y,Z       number between 0 and 9          (required)
    -rc         release candidate indicator     (optional)
    V           number between 0 and 99         (required only when \"-rc\" is present)
  Examples: v.0.1.9, v4.1.7-rc1, v.7.0.9-rc44

  Before using this script, read RELEASE.md
  Make sure that your working branch is:
   - "master" branch
   - up to date with origin/master
   - clean
  Make sure that there is no local branch named "kcm-release-KCM_RELEASE_VER"
  Make sure that there is no remote branch named "kcm-release-KCM_RELEASE_VER"
  Make sure that there is no tag KCM_RELEASE_VER present (locally or remotely)
  Make sure that there is no release with tag KCM_RELEASE_VER present

  ======= IMPORTANT NOTE =======
  After RP with release is reviewed, use "Rebase and merge" in Github PR webpage.
  Jenkins CI/CD is triggered to make release based on specific commit message
  that is setup by this script.


Options:
  -h --help             Show this screen.
"""
import logging
import os
import sys

from docopt import docopt
from distutils.util import strtobool

import githelpers


def validate_branch_not_existing(branch_name):
    local_branches = githelpers.execute_git_cmd("for-each-ref refs/heads/ --format='%(refname:short)'")
    remote_branches = githelpers.execute_git_cmd("for-each-ref refs/remotes/origin --format='%(refname:strip=3)'")

    if branch_name in local_branches:
        logging.error("Aborting: Local branch \"{}\" already exists".format(branch_name))
        exit(1)
    if branch_name in remote_branches:
        logging.error("Aborting: Remote branch \"{}\" already exists".format(branch_name))
        exit(1)


def validate_run_path():
    if os.path.dirname(sys.argv[0]) != ".release":
        logging.error("This script can only be run from main repo directory")
        exit(1)


def main():
    docopt(__doc__)
    logging.basicConfig(level=logging.DEBUG)

    validate_run_path()
    githelpers.validate_master_branch()

    logging.info("Update local repo")
    githelpers.execute_git_cmd("fetch --quiet")
    githelpers.execute_git_cmd("remote update --prune")

    try:
        release_tag = os.environ["KCM_RELEASE_VER"]
    except KeyError:
        logging.error("Missing environment variable KCM_RELEASE_VER")
        exit(1)

    if not githelpers.is_tag_valid(release_tag):
        logging.error("Aborting: Tag \"KCM_RELEASE_VER={}\" is not valid tag".format(release_tag))
        exit(1)
    if githelpers.is_tag_present(release_tag):
        logging.error("Aborting: Tag \"{}\" is already present".format(release_tag))
        exit(1)

    logging.info("Tag \"{}\" will be used".format(release_tag))
    release_branch_name = "{}-{}".format(githelpers.release_branch_base_name, release_tag)
    logging.info("Release branch name \"{}\"".format(release_branch_name))
    validate_branch_not_existing(release_branch_name)

    previous_release_tag = githelpers.execute_cmd("cat Makefile | awk -F '=' '/^version=/ {print $2 }'")
    if not githelpers.is_tag_valid(previous_release_tag):
        logging.error("Aborting: Previous tag from Makefile \"{}\" is not valid".format(previous_release_tag))
        exit(1)

    if previous_release_tag == release_tag:
        logging.error("Aborting: Previous tag from Makefile \"{}\" is the same as new tag \"{}\""
                      .format(previous_release_tag, release_tag))
        exit(1)

    logging.info("All check have passed")

    while True:
        proceed_input = input("Proceed with preparing the release(yes/no)?: ")
        try:
            if proceed_input in ["yes", "no"]:
                break
        except ValueError:
            print("'Please respond with \'yes\' or \'no\'.")

    if strtobool(proceed_input):
        logging.info("Checking out release branch")
        githelpers.execute_git_cmd("checkout -b {}".format(release_branch_name))

        logging.info("Replacing \"{}\" with new tag \"{}\" in repo files".format(previous_release_tag, release_tag))
        githelpers.execute_cmd("git ls-files | xargs -I {{}} sed  --follow-symlinks -i 's/{}/{}/g' {{}}"
                               .format(previous_release_tag, release_tag))

        logging.info("Rebuilding docs")
        githelpers.execute_cmd_visible("make docs")

        logging.info("Committing changes")
        githelpers.execute_git_cmd("add -u")
        githelpers.execute_git_cmd("commit -m\"{} {}.\"".format(githelpers.release_msg, release_tag))

        logging.info("Pushing release branch to origin")
        githelpers.execute_git_cmd("push origin {}".format(release_branch_name))

        githelpers.execute_git_cmd("checkout master")
        logging.info("All done - release branch is ready")
        logging.info("Go to github.com and create PR")
        logging.info("============================ IMPORTANT ====================")
        logging.info("After PR review is good to go - Choose \"Rebase and merge\"")
        logging.info("Jenkins CI/CD searches for \"{} vX.Y.Z[-rcV].\"".format(githelpers.release_msg))
        logging.info("string in commit message")
    else:
        logging.info("Aborting on user request")
        exit(0)

if __name__ == "__main__":
    main()
