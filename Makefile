MODULE_NAME = cowpy
SHELL=/bin/bash
CHANGES = $(shell git status -s -- src/$(MODULE_NAME) | wc -l)

test:
	@echo "write tests"

version:
ifeq ($(CHANGES), 0)
	standard-version
else
	@echo "No versioning today ($(CHANGES) changes)"
endif

version-dry:
ifeq ($(CHANGES), 0)
	standard-version --dry-run
else
	@echo "No versioning today ($(CHANGES) changes)"
endif

build: version
	python3 -m build

build-dry: version-dry

release-test: build 
	python3 -m twine upload --repository testpypi dist/*

release-test-dry: build-dry

install-test:
	pip install -i https://test.pypi.org/simple/ $(MODULE_NAME)
	
clean:
	rm -rf dist 
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ | xargs rm -rvf 
