#!/bin/bash

usage()
{
    cat << EOF
e2e - Runs end to end tests against a running kubernetes cluster

Usage:
    e2e -s <Kubernetes API server address e.g. http://localhost:8080
EOF
}

while getopts ":s:" opt; do
  case $opt in
    s)
      server=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      usage
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      usage
      exit 1
      ;;
  esac
done

if [ -z "$server" ]; then
    echo "Address to Kubernetes API server is needed" >&2
    usage
    exit 1
fi

docker run -e "KCM_E2E_APISERVER=$server" --entrypoint=/bin/bash kcm -c "tox -e e2e"
