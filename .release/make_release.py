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


import logging
import os
import re

import githelpers


def validate_env():
    try:
        os.environ["JENKINS_HOME"]
        os.environ["JENKINS_URL"]
        os.environ["BUILD_DISPLAY_NAME"]
        os.environ["JENKINS_HOME"]
    except KeyError:
        logging.error("Aborting: This scrip should be run only on release VM.")
        exit(1)


def validate_commit_msg_get_tag():
    commit_msg_pattern = re.compile('^(Regenerated HTML docs for |Bumped version to )'
                                    + githelpers.version_pattern.pattern + '\.$')

    commit_msg = [githelpers.get_last_commit_msg(0)[0], githelpers.get_last_commit_msg(1)[0]]
    version_from_commits = []

    for idx, msg in enumerate(commit_msg):
        if not commit_msg_pattern.fullmatch(msg):
            logging.warning("Aborting: Commit message on HEAD~{} is not release commit".format(idx))
            logging.warning("Skipping release process")
            exit(0)
        version_from_commits.append(githelpers.version_pattern.search(msg).group(0))
    logging.info("Last 2 commits are \"release commits\".")

    if len(set(version_from_commits)) != 1:
        logging.error("Aborting: Commit release messages have different versions:\n{}".format(commit_msg))
        exit(1)

    release_tag = version_from_commits[0]
    logging.info("Release version/tag is \"{}\".".format(release_tag))

    if githelpers.is_tag_present(release_tag):
        logging.error("Aborting: Tag \"{}\" already exists.".format(release_tag))
        exit(1)

    return release_tag


def main():

    logging.basicConfig(level=logging.DEBUG)
    try:
        github_token = os.environ["GITHUB_TOKEN"]
    except KeyError:
        logging.error("Missing environment variable GITHUB_TOKEN")
        exit(1)

    validate_env()
    githelpers.validate_master_branch()
    release_tag = validate_commit_msg_get_tag()

    #org = "intelsdi-x"
    org = "squall0gd"
    repo = "kubernetes-comms-mvp"

    gClient = githelpers.GitHubClient(token=github_token, org=org, repo=repo)
    if gClient.get_release_by_tag(release_tag):
        logging.error("Aborting: Release with tag \"{}\" already exists.".format(release_tag))
        exit(1)

    previous_release = gClient.get_latest_release()
    if not previous_release:
        previous_release_id = githelpers.execute_git_cmd("rev-list --max-parents=0 HEAD")
    else:
        previous_release_id = previous_release["tag_name"]

    logging.info("Creating tag \"{}\" and pushing to origin".format(release_tag))
    githelpers.create_and_push_tag(release_tag)

    change_log = githelpers.generate_changelog(org, repo, release_tag, previous_release_id)
    pre_release = bool("-rc" in release_tag)

    release_body = {
        "tag_name": release_tag,
        "name": "KCM release {}".format(release_tag),
        "body": change_log,
        "prerelease": pre_release
    }

    logging.info("Creating release".format(release_tag))
    logging.info("Release details: {}".format(release_body))
    print(gClient.make_release(release_body).json())

if __name__ == "__main__":
    main()
