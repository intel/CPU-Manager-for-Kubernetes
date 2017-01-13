#!/bin/bash

echo "Refreshing state..."
yum makecache -q
echo "Updating system..."
yum update -y -q
yum install -y -q epel-release
echo "Installing software dependencies..."
yum groupinstall -y -q "Development tools"
yum install -y \
    python34-devel
echo "Installing pip3..."
curl https://bootstrap.pypa.io/get-pip.py | sudo python3
