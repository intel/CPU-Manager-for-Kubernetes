# Copyright (c) 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

.PHONY: docker docs release test

all: docker

version=v1.5.2

# TODO: This target should be changed, when e2e tests will be ready and test
# entrypoint will be defined.
jenkins: docker

docker:
	docker build -t cmk:$(version) .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it cmk:$(version) ..."

test: docker
	docker run --rm cmk:$(version) tox -e lint,unit,integration,coverage


# Output neatly formatted HTML docs to `docs/html`.
#
# This target uses `grip` (see https://github.com/joeyespo/grip).
#
# The files are passed securely to the GitHub rendering API.
# GitHub imposes a limit of 60 unauthorized requests per hour.
# To authenticate, create a personal access token and add it to a file
# named `~/grip/settings.py` as described in the project README.
docs:
	pip install grip
	mkdir -p docs/html/docs
	cp -R docs/images docs/html/docs/
	grip README.md --export docs/html/index.html --title="CMK"
	grip docs/build.md --export docs/html/docs/build.html --title="Building cmk"
	grip docs/cli.md --export docs/html/docs/cli.html --title="Using the cmk command-line tool"
	grip docs/config.md --export docs/html/docs/config.html --title="The cmk configuration directory"
	grip docs/operator.md --export docs/html/docs/operator.html --title="cmk operator manual"
	grip docs/user.md --export docs/html/docs/user.html --title="cmk user manual"
	grip docs/architecture.md --export docs/html/docs/architecture.html --title="cmk architecture"
	sed -i"" "s/\.md/\.html/g" docs/html/index.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/build.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/cli.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/config.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/operator.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/user.html
	sed -i"" "s/\.md/\.html/g" docs/html/docs/architecture.html

# Trigger for github release used by travis.yml
release:
	.release/make_release.py
