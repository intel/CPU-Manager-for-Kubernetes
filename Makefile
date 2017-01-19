.PHONY: docker docs

all: docker

sha=$(shell git describe --tags --dirty --always)

docker:
	docker build --no-cache -t kcm:$(sha) .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm:$(sha) ..."

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
	grip README.md --export docs/html/index.html --title="KCM"
	grip docs/build.md --export docs/html/docs/build.html --title="Building kcm"
	grip docs/cli.md --export docs/html/docs/cli.html --title="Using the kcm command-line tool"
	grip docs/config.md --export docs/html/docs/config.html --title="The kcm configuration directory"
	grip docs/operator.md --export docs/html/docs/operator.html --title="kcm operator manual"
	grip docs/user.md --export docs/html/docs/user.html --title="kcm user manual"
	sed -i "" "s/\.md/\.html/g" docs/html/index.html
	sed -i "" "s/\.md/\.html/g" docs/html/docs/build.html
	sed -i "" "s/\.md/\.html/g" docs/html/docs/cli.html
	sed -i "" "s/\.md/\.html/g" docs/html/docs/config.html
	sed -i "" "s/\.md/\.html/g" docs/html/docs/operator.html
	sed -i "" "s/\.md/\.html/g" docs/html/docs/user.html
