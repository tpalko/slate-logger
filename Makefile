PACKAGE_NAME = cowpy
SHELL=/bin/bash
CHANGES = $(shell git status -s -- src/$(PACKAGE_NAME) | wc -l)
INVENV := $(if $(VIRTUAL_ENV),1,0)
PYTHONINT = $(shell which python3)
WORKON_HOME=~/.virtualenv
VENV_WRAPPER=/usr/share/virtualenvwrapper/virtualenvwrapper.sh

venv:	
	@. $(VENV_WRAPPER) && (workon $(PACKAGE_NAME) 2>/dev/null || mkvirtualenv -p $(PYTHONINT) $(PACKAGE_NAME))	
	@pip install --extra-index-url https://test.pypi.org/simple -t $(WORKON_HOME)/$(PACKAGE_NAME)/lib/python3.9/site-packages -r requirements.txt 

test:
	@cd tests && python test.py

build-deps:
	@$(PYTHONINT) -m pip install --upgrade pip build twine 

version:
ifeq ($(CHANGES), 0)
ifeq ($(INVENV), 0)
	@echo "Versioning ($(CHANGES) changes)"
	standard-version
else 
	@echo "No versioning today (in virtual env $(VIRTUAL_ENV))"
endif
else
	@echo "No versioning today ($(CHANGES) changes)"
endif

version-dry:
ifeq ($(CHANGES), 0)
	standard-version --dry-run
else
	@echo "No versioning today ($(CHANGES) changes)"
endif

build: build-deps version
ifeq ($(INVENV), 0)
	python3 -m build
else 
	@echo "No building today (in virtualenv $(VIRTUAL_ENV))"
endif 

build-dry: version-dry

release-test: build 
	python3 -m twine upload --repository testpypi dist/*

release-test-dry: build-dry

install-test:
	pip install -i https://test.pypi.org/simple/ $(PACKAGE_NAME)

release: build 
	python3 -m twine upload --repository pypi dist/*
	
clean:
	rm -rf dist 
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ | xargs rm -rvf 
