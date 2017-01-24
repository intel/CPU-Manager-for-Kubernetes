#!/usr/bin/env bash
set -o errexit
set -o pipefail

SCRIPT_DIR="$(dirname ${BASH_SOURCE[0]})"
USED_OS="${1}"
WORK_DIR="${SCRIPT_DIR}/../workdir"

. ${SCRIPT_DIR}/install_kargo.sh
. ${SCRIPT_DIR}/install_kubectl.sh


tweak_group_vars() {
  sed -i.old "s/bootstrap_os: .*/bootstrap_os: ${USED_OS}/" ./mvp_inventory/group_vars/all.yml
}

pushd ${WORK_DIR}
get_kargo
setup_playbook
tweak_group_vars ${USED_OS}

ansible_verbosity=""
if [ "${DEBUG}" == "true" ]; then
    ansible_verbosity="-vvv"
fi
ansible-playbook --connection=ssh --timeout=30 --limit=all --inventory-file=./mvp_inventory/ --sudo ${ansible_verbosity} cluster.yml
get_kubectl
popd
