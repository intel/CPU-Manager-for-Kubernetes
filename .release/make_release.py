#!/usr/bin/env python
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


import logging
import os
import re

import githelpers


def validate_commit_msg_get_tag():
    commit_msg_pattern = re.compile('^{} '.format(githelpers.release_msg)
                                    + githelpers.version_pattern.pattern + '\.$')

    latest_commit_msg = githelpers.get_last_commit_msg("HEAD^0")[0]
    logging.info("Latest commit message is: {}".format(latest_commit_msg))

    # Latest commit should have "KCM release - version vX.Y.Z(-rcV)in commit msg"
    if not commit_msg_pattern.fullmatch(latest_commit_msg):
        logging.warning("Aborting: Commit message on HEAD~0 is not release commit")
        exit(0)

    logging.info("Commit HEAD~0 message is release commit")
    release_tag = githelpers.version_pattern.search(latest_commit_msg).group(0)
    githelpers.is_tag_valid(release_tag)

    logging.info("Last commit is \"release commits\".")

    if githelpers.is_tag_present(release_tag):
        logging.error("Aborting: Tag \"{}\" already exists.".format(release_tag))
        exit(1)

    logging.info("Release version/tag is \"{}\".".format(release_tag))

    return release_tag


def get_org_and_repo_name():
    origin_url = githelpers.execute_git_cmd("config --get remote.origin.url").strip(".git").split(":")
    repo_info = origin_url[-1].split("/")
    return repo_info[0], repo_info[1]


def main():

    logging.basicConfig(level=logging.DEBUG)
    try:
        github_token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        logging.error("Missing environment variable GITHUB_TOKEN")
        exit(1)

    githelpers.is_branch_clean()
    release_tag = validate_commit_msg_get_tag()
    org_name, repo_name = get_org_and_repo_name()

    github_client = githelpers.GitHubClient(token=github_token, org=org_name, repo=repo_name)

    if github_client.get_login_by_token() != "snapbot-private":
        logging.error("This script can only be run by snapbot-private user on relase VM")
        exit(1)

    if github_client.get_release_by_tag(release_tag):
        logging.error("Aborting: Release with tag \"{}\" already exists.".format(release_tag))
        exit(1)

    previous_release = github_client.get_latest_release()

    if not previous_release:
        previous_release_id = githelpers.execute_git_cmd("rev-list --max-parents=0 HEAD")
    else:
        previous_release_id = previous_release["tag_name"]

    logging.info("Creating tag \"{}\" and pushing to origin".format(release_tag))
    githelpers.create_and_push_tag(release_tag)

    change_log = githelpers.generate_changelog(org_name, repo_name, release_tag, previous_release_id)
    pre_release = bool("-rc" in release_tag)

    release_body = {
        "tag_name": release_tag,
        "name": "KCM release {}".format(release_tag),
        "body": change_log,
        "prerelease": pre_release
    }

    logging.info("Creating release".format(release_tag))
    logging.info("Release details: {}".format(release_body))

    github_client.make_release(release_body)


if __name__ == "__main__":
    main()
