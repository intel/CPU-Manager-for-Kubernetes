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
  echo "Usage: $0 [option...] {vagrant|aws} {deploy|purge}" >&2
  echo
  exit 1
}


######################################
# The command to deploy vagrant VM's #
######################################
vagrant_deploy() {
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

#####################################
# The command to purge vagrant VM's #
#####################################
vagrant_purge() {
  pushd "./vagrant_env"
  rm -rf ./inventory 2>&1 >/dev/null
  terraform get
  terraform destroy --force
  popd
}

#############################
# Validate AWS requirements #
#############################
aws_shared() {
  if [ "${SSH_AGENT_PID}" == "" ]; then
    echo "ssh-agent isn't running"
    exit 1
  fi

  if [ "${AWS_SECRET_ACCESS_KEY}" == "" ] || [ "${AWS_ACCESS_KEY_ID}" == "" ] || [ "${TF_VAR_agent_seed}" == "" ]; then
    echo "AWS_SECRET_ACCESS_KEY/AWS_ACCESS_KEY_ID/TF_VAR_agent_seed isn't/aren't set"
    exit 1
  fi
}

##################################
# The command to deploy AWS VM's #
##################################
aws_deploy() {
  aws_shared
  pushd "./aws_env"
  terraform get
  terraform apply
  popd
}

#################################
# The command to purge AWS VM's #
#################################
aws_purge(){
  aws_shared
  pushd "./aws_env"
  terraform destroy --force
  git checkout ./workdir/*
  popd
}

main() {
  local target
  local action

  case "$1" in
    aws)
      target="aws"
      ;;
    vagrant)
      target="vagrant"
      ;;
    *)
      display_help
  esac
  case "$2" in
    deploy)
      action="deploy"
      ;;
    purge)
      action="purge"
      ;;
    *)
      display_help
  esac
  ${target}_${action}
}

main "$@"

