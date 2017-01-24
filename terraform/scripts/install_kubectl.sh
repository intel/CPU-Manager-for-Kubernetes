#!/usr/bin/env bash

[ -z "${KUBECTL_VERSION}" ] && KUBECTL_VERSION="v1.5.1"

get_kubectl() {
  if [ ! -x ./kubectl ] || [[ $(./kubectl version --client | awk '{print $5}') != *"$KUBECTL_VERSION"* ]]; then
    echo "Downloading kubectl $KUBECTL_VERSION"
    curl -LO  https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl
    chmod +x ./kubectl
  fi
}
