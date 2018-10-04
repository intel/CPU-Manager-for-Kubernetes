#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import os
import re

import githelpers


def validate_commit_msg_get_tag():
    commit_msg_pattern = re.compile('^{} '.format(githelpers.release_msg)
                                    + githelpers.version_pattern.pattern + '\.$')

    latest_commit_msg = githelpers.get_last_commit_msg("HEAD^0")[0]
    logging.info("Latest commit message is: {}".format(latest_commit_msg))

    # Latest commit should have "CMK release - version vX.Y.Z(-rcV)in commit msg"
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
    origin_url = githelpers.execute_git_cmd("config --get remote.origin.url").rstrip(".git")
    repo_info = re.split(':|\/', origin_url)
    return repo_info[-2], repo_info[-1]


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

    if not github_client.get_login_by_token():
        logging.error("Aborting: Provided GITHUB_TOKEN does not have access to {}/{}".format(org_name, repo_name))
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
        "name": "CMK release {}".format(release_tag),
        "body": change_log,
        "prerelease": pre_release,
        "target_commitish": githelpers.get_head_sha()
    }

    logging.info("Creating release".format(release_tag))
    logging.info("Release details: {}".format(release_body))

    github_client.make_release(release_body)


if __name__ == "__main__":
    main()
