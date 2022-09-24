PACKAGE_NAME = cowpy
SHELL=/bin/bash
CHANGES = $(shell git status -s -- src/$(PACKAGE_NAME) | wc -l)
PYTHONINT = $(shell which python3)
WORKON_HOME=~/.virtualenv
VENV_WRAPPER=/usr/share/virtualenvwrapper/virtualenvwrapper.sh

venv:	
	@. $(VENV_WRAPPER) && (workon $(PACKAGE_NAME) 2>/dev/null || mkvirtualenv -p $(PYTHONINT) $(PACKAGE_NAME))	
	@pip install --extra-index-url https://test.pypi.org/simple -t $(WORKON_HOME)/$(PACKAGE_NAME)/lib/python3.9/site-packages -r requirements.txt 

test:
	@cd tests && python test.py

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
	pip install -i https://test.pypi.org/simple/ $(PACKAGE_NAME)
	
clean:
	rm -rf dist 
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ | xargs rm -rvf 
