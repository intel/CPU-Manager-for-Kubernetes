.PHONY: docker

all: docker

sha=$(shell git describe --tags --dirty --always)

docker:
	docker build --no-cache -t kcm:$(sha) .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm:$(sha) ..."
