#!/bin/bash

TOOLBOX_CMD="toolbox -q"

echo "Refreshing state..."
$TOOLBOX_CMD dnf makecache -q
echo "Updating system..."
$TOOLBOX_CMD dnf update -y -q
$TOOLBOX_CMD dnf install -y -q epel-release 
echo "Installing software dependencies..."
$TOOLBOX_CMD dnf install -y \
    python-devel \
    python-pip
