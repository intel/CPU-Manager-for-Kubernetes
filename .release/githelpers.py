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

import logging
import re
import subprocess

import requests


version_pattern = re.compile('v\d\.\d\.\d(-rc\d(\d)?)?')
release_branch_base_name = "kcm-release"
release_msg = "KCM release - version"

def execute_git_cmd(cmd):
    git_command = " ".join(["git", cmd])
    return execute_cmd(git_command)


def execute_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, universal_newlines=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        logging.error("Aborting: Got error while calling \"{}\"".format(cmd))
        logging.error("Details: {}".format(err))
        logging.error("Details: {}".format(err.output))
        exit(1)
    return out.strip()


def execute_cmd_visible(cmd):
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                               universal_newlines=True, stderr=subprocess.STDOUT) as proc:
        for line in proc.stdout:
            print(line, end='')
    if proc.returncode != 0:
        logging.error("Aborting: Got error while calling \"{}\"".format(cmd))
        exit(1)


def is_tag_valid(tag):
    tag_pattern = re.compile('^' + version_pattern.pattern + '$')
    return bool(tag_pattern.fullmatch(tag))


def is_tag_present(tag):
    return tag in get_tags()


def validate_master_branch():
    if get_branch_name() != "master":
        logging.error("Aborting: Release can be done only on master branch.")
        exit(1)
    if not is_branch_clean():
        logging.error("Aborting: Branch is not clean.")
        exit(1)

def get_branch_name():
    return execute_git_cmd("rev-parse --abbrev-ref HEAD")


def get_head_sha():
    return execute_git_cmd("rev-parse HEAD")


def is_branch_clean():
    return bool(len(execute_git_cmd("status --porcelain").split("\n")))


def get_last_commit_msg(commit):
    return execute_git_cmd("log --format=%B -n 1 {}".format(commit)).split("\n")


def get_tags():
    return execute_git_cmd("for-each-ref refs/tags --format='%(refname:short)'").split("\n")


def create_and_push_tag(tag):
    execute_git_cmd("tag -a {} -m \"KCM {}\"".format(tag, tag))
    execute_git_cmd("push origin --tags")


def generate_changelog(org, repo, tag_new, previous_release_id):
    pretty = ('\'<li> <a href=\"http://github.com/{}/{}/commit/%H\">'
              'view &bull;</a> %s</li> \''.format(org, repo))

    out = execute_git_cmd("log {}...{} --pretty=format:{}"
                          .format(tag_new, previous_release_id, pretty))
    return out


class GitHubClient:
    def __init__(self, token, org, repo):
        self._token = token
        self.baseUrl = "https://api.github.com/repos/" + org.strip("/") + "/" + repo.strip("/")
        self.authHeader = dict(Authorization='token {}'.format(self._token))
        self._uploadUrl = ''

    def get_all_releases(self):
        url = self.baseUrl + "/releases"
        resp = requests.get(url, headers=self.authHeader)
        return resp.json()

    def get_latest_release(self):
        url = self.baseUrl + "/releases/latest"
        resp = requests.get(url, headers=self.authHeader)
        if resp.status_code == requests.codes.not_found:
            return
        resp.raise_for_status()
        return resp.json()

    def get_release_by_tag(self, tag):
        url = self.baseUrl + "releases/tags"
        resp = requests.get(url, headers=self.authHeader)
        if resp.status_code == requests.codes.not_found:
            return
        resp.raise_for_status()
        return resp.json()

    def make_release(self,release_body):
        url = self.baseUrl + "/releases"
        resp = requests.post(url, json=release_body, headers=self.authHeader)
        resp.raise_for_status()
        self._uploadUrl = resp.json()['upload_url']
        return resp

    def get_login_by_token(self):
        url = "https://api.github.com/user"
        resp = requests.get(url, headers=self.authHeader)
        if resp.status_code == requests.codes.unauthorized:
            return
        resp.raise_for_status()
        return resp.json()["login"]
