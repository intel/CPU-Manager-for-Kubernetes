#!/usr/bin/env bash
KARGO_REPO="https://github.com/kubernetes-incubator/kargo.git"
KARGO_TAG="v2.1.0"

get_kargo() {
  if [ ! -d ./.kargo ]; then
    git clone --branch ${KARGO_TAG} ${KARGO_REPO} ./.kargo
  fi
}

setup_playbook() {
    ln -sf ./.kargo/cluster.yml ./cluster.yml
}
