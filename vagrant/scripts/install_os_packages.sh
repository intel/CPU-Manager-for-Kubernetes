#!/bin/bash

echo "Refreshing state..."
yum makecache -q
echo "Updating system..."
yum update -y -q
yum install -y -q epel-release
echo "Installing software dependencies..."
yum groupinstall -y -q "Development tools"
yum install -y \
    python-devel \
    python-pip
