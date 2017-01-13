#!/bin/bash

echo "Installing project deps..."
pushd /kcm
make deps
popd
