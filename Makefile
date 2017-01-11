.PHONY: docker

all: docker

docker:
	docker build --no-cache -t kcm .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm ..."
