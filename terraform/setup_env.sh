#!/usr/bin/env bash
set -o errexit
set -o pipefail

DEBUG=false
WORK_DIR="./workdir"
SCRIPT_DIR="./scripts"

. ${SCRIPT_DIR}/install_kargo.sh
. ${SCRIPT_DIR}/install_kubectl.sh


#########################
# The command line help #
#########################
display_help() {
  echo "Usage: $0 [option...] {deploy|purge}" >&2
  echo
  exit 1
}


#############################
# The command to deploy VM's#
#############################
deploy() {
  # Terraform deploying
  pushd "./vagrant_env"
  terraform get
  terraform apply
  USED_OS=$(terraform output used_os)
  popd

  cp ./vagrant_env/inventory ./${WORK_DIR}/mvp_inventory/ansible_inventory

  # Kargo deploying
  exec ${SCRIPT_DIR}/ansible_provisioner.sh ${USED_OS}
}

############################
# The command to purge VM's#
############################
purge() {
  pushd "./vagrant_env"
  rm -rf ./inventory 2>&1 >/dev/null
  terraform get
  terraform destroy --force
  popd
}

main() {
  case "$1" in
    deploy)
      deploy
      ;;
    purge)
      purge
      ;;
    *)
      display_help
  esac
}

main "$@"

