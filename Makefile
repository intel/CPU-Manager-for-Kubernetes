.PHONY: docker

all: docker

docker:
	docker build -t kcm .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm ..."

deps:
	pip install -r requirements.txt && chmod +x ./kcm.py
test_lint: deps
	tox -e lint
test_unit: deps
	tox -e unit
test_integration: deps
	tox -e integration
