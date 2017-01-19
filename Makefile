.PHONY: docker

all: docker

sha=$(shell git rev-parse --short HEAD)

docker:
	docker build --no-cache -t kcm:$(sha) .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm:$(sha) ..."
