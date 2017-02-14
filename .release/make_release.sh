#!/bin/bash

ssh-keyscan github.com >> ~/.ssh/known_hosts
git config --global url."git@github.com:".insteadOf "https://github.com/"

ls -lah
echo "Hello world!"

git fetch --all
