#!/usr/bin/env bash

set -o errexit
set -o pipefail

get_branch_name() {
    echo $(git rev-parse --abbrev-ref HEAD)
}

display_help() {
  echo ""
  echo "============== INFO ========================================================================"
  echo "This script based on KCM_RELEASE_VER variable prepares kcm release"
  echo "KCM_RELEASE_VER variable should follow pattern vX.Y.Z[-rcV] where"
  echo "    X,Y,Z       number between 0 and 9          (required)"
  echo "    -rc         release candidate indicator     (optional)"
  echo "    V           number between 0 and 99         (required only when \"-rc\" is present)"
  echo "Examples: \"v.0.1.9\", \"v4.1.7-rc1\", \"v.7.0.9-rc44\""
  echo ""
  echo "============== USAGE ======================================================================="
  echo "$0 "
  echo "KCM_RELEASE_VER=vX.Y.Z[-rcV] $0 "
  echo ""
  echo "============== IMPORTANT===================================================================="
  echo "Before using this script, read RELEASE.md, TLDR:"
  echo "Make sure that your working branch is clean and up to date(preferably use \"master\")"
  echo "Make sure that there is no local branch named \"kcm-release-KCM_RELEASE_VER\""
  echo "Make sure that there is no remote branch named \"kcm-release-KCM_RELEASE_VER\""
  exit $1
}

validate_release_version() {
    local version=$1
    if ! [[ "$version" =~ ^v[0-9].[0-9].[0-9](-rc[0-9][0-9]?)?$ ]]; then
        echo "ERROR: invalid value in KCM_RELEASE_VER"
        display_help 1
    fi

    local all_tags=$(git for-each-ref refs/tags --format='%(refname:short)')
    for tag in ${all_tags}; do
        if [ "${tag}" = "${version}" ]; then
            echo "ERROR: tag (\"${KCM_RELEASE_VER}\") already exists"
            display_help 1
        fi
    done
}

check_branch_cleanliness() {
    if ! [[ -z $(git status --porcelain) ]]; then
        echo "ERROR: current branch (\"$(get_branch_name)\") is not clean"
        display_help 1
    fi
}

check_branch_names() {
    local local_branches=$(git for-each-ref refs/heads/ --format='%(refname:short)')
    local remote_branches=$(git for-each-ref refs/remotes/origin --format='%(refname:strip=3)')
    for branch_name in ${local_branches}; do
        if [ "${branch_name}" = "${RELEASE_BRANCH_NAME}" ]; then
            echo "ERROR: branch (\"${branch_name}\") already exists locally"
            display_help 1
        fi
    done
    for branch_name in ${remote_branches}; do
        if [ "${branch_name}" = "${RELEASE_BRANCH_NAME}" ]; then
            echo "ERROR: branch (\"${branch_name}\") already exists remotely"
            display_help 1
        fi
    done
}

if [ "$1" == "-h" ]; then
    display_help 0
fi


git fetch --quiet
git remote update --prune

[ -z ${KCM_RELEASE_VER} ] && (echo "ERROR: KCM_RELEASE_VER is not set or empty" && display_help 1)
validate_release_version ${KCM_RELEASE_VER}

CURRENT_BRANCH=$(get_branch_name)
RELEASE_BRANCH_NAME=kcm-release-${KCM_RELEASE_VER}

check_branch_names
check_branch_cleanliness

KCM_PREV_RELEASE_VER=$(git describe --abbrev=0 --tags)

git checkout -b ${RELEASE_BRANCH_NAME}

git ls-files | xargs -I {} sed -i "s/${KCM_PREV_RELEASE_VER}/${KCM_RELEASE_VER}/g" {}
git add -u
git commit -m "Bumped version to ${KCM_RELEASE_VER}."

make docs
git add -u
git commit -m "Regenerated HTML docs for ${KCM_RELEASE_VER}."

git push origin ${RELEASE_BRANCH_NAME}
git checkout ${CURRENT_BRANCH}
