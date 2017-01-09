.PHONY: docker

all: docker

test_code: deps test_lint test_unit test_integration
test_docker: docker

docker:
	docker build -t kcm .
	@echo ""
	@echo "To run the docker image, run command:"
	@echo "docker run -it kcm ..."

deps:
	pip install -r requirements.txt && chmod +x ./kcm.py
test_lint:
	tox -e lint
test_unit:
	tox -e unit
test_integration:
	tox -e integration
