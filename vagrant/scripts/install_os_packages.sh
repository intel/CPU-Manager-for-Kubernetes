#!/bin/bash


TOOLBOX_CMD="toolbox -q"

echo "Updating system..."
$TOOLBOX_CMD dnf update -y
echo "Installing software dependencies..."
$TOOLBOX_CMD dnf install -y \
    python-devel
    python-pip
