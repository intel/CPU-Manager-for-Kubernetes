#!/bin/bash

echo "Refreshing state..."
toolbox yum makecache -q
echo "Updating system..."
toolbox yum update -y -q
toolbox yum install -y -q epel-release 
echo "Installing software dependencies..."
toolbox yum install -y \
    python-devel \
    python-pip

exit 0
