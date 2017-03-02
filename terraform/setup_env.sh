#!/usr/bin/env bash
set -o errexit
set -o pipefail

DEBUG=false

#########################
# The command line help #
#########################
display_help() {
  echo ""
  echo "Usage: $0 {vagrant|aws} {deploy|purge} [option...] " >&2
  echo "Valid options:"
  echo "    -d      enable debug to stdout"
  echo "    -h      view help"
  echo "    -f      force (valid only for purge removes: kargo, terraform files, kubectl and credentials)"
  exit $1
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
  exec ./scripts/ansible_provisioner.sh ${USED_OS}
}

#####################################
# The command to purge vagrant VM's #
#####################################
vagrant_purge() {
  pushd "./vagrant_env"
  rm -rf ./inventory 2>&1 >/dev/null
  terraform get
  terraform destroy --force
  [[ ${FORCE} = "true" ]] && rm -rf .terraform terraform.tfstate terraform.tfstate.backup
  popd
  [[ ${FORCE} = "true" ]] && pushd "./workdir" && rm -rf .kargo credentials *.retry kubectl config.yml cluster.yml 2>&1 >/dev/null && popd
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
  USED_OS=$(terraform output used_os)
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
  local target="invalid"
  local action="invalid"


  if [ $# -lt 2 ]; then
    display_help 1
  fi

  options=$(getopt -o dfh --long debug,force,help -- "$@")
  [ $? -eq 0 ] || {
    echo "Incorrect options provided"
    display_help 1
  }

  while true ; do
    case "$1" in
        -d|--debug)
            DEBUG=true ; shift ;;
        -f|--force)
            FORCE=true ; shift ;;
        -h|--help)
            display_help 0 ;;
        "aws"|"vagrant")
            target=$1 ; shift ;;
        "deploy"|"purge")
            action=$1 ; shift ;;
        --)
            shift ; break ;;
        *)
            break ;;
    esac
  done

  if [ "$target" = "invalid" ] || [ "$action" == "invalid" ]; then
    display_help 1
  fi

  # terraform logs
  [[ ${DEBUG} = "true" ]] && export TF_LOG=DEBUG || unset TF_LOG
  export TF_VAR_skip_deploy=true
  export DEBUG

  ${target}_${action}
}

main "$@"

