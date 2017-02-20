#!/usr/bin/env python3
# Intel License for KCM (version January 2017)
#
# Copyright (c) 2017 Intel Corporation.
#
# Use.  You may use the software (the "Software"), without modification,
# provided the following conditions are met:
#
# * Neither the name of Intel nor the names of its suppliers may be used to
#   endorse or promote products derived from this Software without specific
#   prior written permission.
# * No reverse engineering, decompilation, or disassembly of this Software
#   is permitted.
#
# Limited patent license.  Intel grants you a world-wide, royalty-free,
# non-exclusive license under patents it now or hereafter owns or controls to
# make, have made, use, import, offer to sell and sell ("Utilize") this
# Software, but solely to the extent that any such patent is necessary to
# Utilize the Software alone. The patent license shall not apply to any
# combinations which include this software.  No hardware per se is licensed
# hereunder.
#
# Third party and other Intel programs.  "Third Party Programs" are the files
# listed in the "third-party-programs.txt" text file that is included with the
# Software and may include Intel programs under separate license terms. Third
# Party Programs, even if included with the distribution of the Materials, are
# governed by separate license terms and those license terms solely govern your
# use of those programs.
#
# DISCLAIMER.  THIS SOFTWARE IS PROVIDED "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT ARE
# DISCLAIMED. THIS SOFTWARE IS NOT INTENDED NOR AUTHORIZED FOR USE IN SYSTEMS
# OR APPLICATIONS WHERE FAILURE OF THE SOFTWARE MAY CAUSE PERSONAL INJURY OR
# DEATH.
#
# LIMITATION OF LIABILITY. IN NO EVENT WILL INTEL BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. YOU AGREE TO
# INDEMNIFIY AND HOLD INTEL HARMLESS AGAINST ANY CLAIMS AND EXPENSES RESULTING
# FROM YOUR USE OR UNAUTHORIZED USE OF THE SOFTWARE.
#
# No support.  Intel may make changes to the Software, at any time without
# notice, and is not obligated to support, update or provide training for the
# Software.
#
# Termination. Intel may terminate your right to use the Software in the event
# of your breach of this Agreement and you fail to cure the breach within a
# reasonable period of time.
#
# Feedback.  Should you provide Intel with comments, modifications,
# corrections, enhancements or other input ("Feedback") related to the Software
# Intel will be free to use, disclose, reproduce, license or otherwise
# distribute or exploit the Feedback in its sole discretion without any
# obligations or restrictions of any kind, including without limitation,
# intellectual property rights or licensing obligations.
#
# Compliance with laws.  You agree to comply with all relevant laws and
# regulations governing your use, transfer, import or export (or prohibition
# thereof) of the Software.
#
# Governing law.  All disputes will be governed by the laws of the United
# States of America and the State of Delaware without reference to conflict of
# law principles and subject to the exclusive jurisdiction of the state or
# federal courts sitting in the State of Delaware, and each party agrees that
# it submits to the personal jurisdiction and venue of those courts and waives
# any objections. The United Nations Convention on Contracts for the
# International Sale of Goods (1980) is specifically excluded and will not
# apply to the Software.

"""prepare_release.py

Usage:
  .release/prepare_release.py

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
    if os.path.dirname(sys.argv[0]) != ".release" :
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
    logging.info("Tag \"{}\" is valid".format(release_tag))

    release_branch_name = "kmc-release-{}".format(release_tag)
    logging.info("Release branch name \"kcm-release-{}\"".format(release_tag))
    validate_branch_not_existing(release_branch_name)

    previous_release_tag = githelpers.execute_cmd("cat Makefile | awk -F '=' '/^version=/ {print $2 }'")
    if not githelpers.is_tag_valid(previous_release_tag):
        logging.error("Aborting: Previous tag from Makefile \"={}\" is not valid".format(previous_release_tag))
        exit(1)

    logging.info("All check have passed")

    while True:
        proceed_input = input("Proceed with release(yes/no)?: ")
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

        logging.info("Committing changes")
        githelpers.execute_git_cmd("add -u")
        githelpers.execute_git_cmd("commit -m\"Bumped version to {}\"".format(release_tag))

        logging.info("Rebuilding docs")
        githelpers.execute_cmd_visible("make docs")

        logging.info("Committing changes")
        githelpers.execute_git_cmd("add -u")
        githelpers.execute_git_cmd("commit -m\"Regenerated HTML docs for {}\"".format(release_tag))

        logging.info("Pushing release branch to origin")
        githelpers.execute_git_cmd("push origin {}".format(release_branch_name))

        githelpers.execute_git_cmd("checkout master")
        logging.info("All done - release branch is ready")
    else:
        logging.info("Aborting on user request")
        exit(0)

if __name__ == "__main__":
    main()
