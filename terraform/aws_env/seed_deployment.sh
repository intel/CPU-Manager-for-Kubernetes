#!/bin/bash

case "$1" in
    ubuntu)
        apt-get -qq update
        apt-get -qq install -y python-pip libssl-dev;;
    centos)
        yum -q makecache
        yum -q install -y epel-release 
        yum -q install -y python-pip gcc libffi-devel python-devel openssl-devel ;;
    *)
        echo "Cannot spawn seed on this OS"
        exit 1
esac
        

pip install -q ansible==2.2.0.0
pip install -q -r ./terraform/requirements.txt
