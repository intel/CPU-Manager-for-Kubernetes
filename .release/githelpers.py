#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
