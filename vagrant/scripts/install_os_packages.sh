#!/bin/bash

echo "Refreshing state..."
apt-get update
echo "Updating system..."
apt-get upgrade -y -q
apt-get dist-upgrade -y -q
echo "Installing software dependencies..."
apt-get install -y \
    python-dev \
    python-pip
