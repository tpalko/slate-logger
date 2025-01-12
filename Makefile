PACKAGE_NAME := cowpy
SHELL := /bin/bash
CHANGES := $(shell git status -s -- src/$(PACKAGE_NAME) | wc -l)
INVENV := $(if $(VIRTUAL_ENV),1,0)
PYTHONINT := $(shell which python3)
WORKON_HOME := ~/.virtualenv
VENV_WRAPPER := /usr/share/virtualenvwrapper/virtualenvwrapper.sh
LATEST_VERSION := $(shell git tag | grep -E "^v[[:digit:]]+.[[:digit:]]+.[[:digit:]]+$$" | sort -n | tail -n 1)
HEAD_VERSION_TAG := $(shell git tag --contains | head -n 1 | grep -E "^v[[:digit:]]+.[[:digit:]]+.[[:digit:]]+$$")
HEAD_TAGGED := $(if $(HEAD_VERSION_TAG),1,0)
BRANCH := $(shell git branch --show-current)

venv:	
	@. $(VENV_WRAPPER) && (workon $(PACKAGE_NAME) 2>/dev/null || mkvirtualenv -p $(PYTHONINT) $(PACKAGE_NAME))	
	@pip install --extra-index-url https://test.pypi.org/simple -t $(WORKON_HOME)/$(PACKAGE_NAME)/lib/python3.9/site-packages -r requirements.txt 

test:
	@cd tests && $(PYTHONINT) test.py
	@find tests -name "__pycache__" -type d | xargs rm -vrf

build-deps:
	@$(PYTHONINT) -m pip install --upgrade pip build twine 

version:
ifeq ($(BRANCH), main)
ifeq ($(CHANGES), 0)
ifeq ($(INVENV), 0)
ifeq ($(HEAD_TAGGED), 0)
	@echo "Versioning (DRY_RUN=$(DRY_RUN))"
ifneq ($(DRY_RUN), 1)
	sed -i \
		"s/^version = .*/version = \"$(shell standard-version --dry-run | grep "tagging release" | awk '{ print $$4 }')\"/" \
		pyproject.toml
	git diff -- pyproject.toml
	git add pyproject.toml
	standard-version -a	
else 
	@echo ""
	@echo "_---- D R Y  R U N ----_"
	@echo ""
	grep -i version pyproject.toml 
	standard-version -a	--dry-run 
endif 
else 
	@echo "No versioning today (commit already tagged $(HEAD_VERSION_TAG))"	
endif 
else 
	@echo "No versioning today (in virtual env $(VIRTUAL_ENV))"
	exit 1
endif
else
	@echo "No versioning today ($(CHANGES) changes). Stash or commit your changes."
	exit 1
endif
else 
	@echo "Will not version outside main"
	exit 1
endif 

.PHONY: build 

ifeq ($(INVENV), 0)
ifeq ($(HEAD_TAGGED), 1)
build: build-deps
	python3 -m build
else 
build:
	@echo "Will not build unversioned"
	exit 1
endif 
else 
build:
	@echo "Cannot build while in virtualenv (in virtualenv $(VIRTUAL_ENV))"
	exit 1	
endif 

publish-test: build 
ifneq ($(DRY_RUN), 1)
	python3 -m twine upload --repository testpypi dist/*
else 
	python3 -m twine check --repository testpypi dist/*
endif 

publish: build 
ifneq ($(DRY_RUN), 1)
	python3 -m twine upload dist/*
else 
	python3 -m twine check dist/*
endif 

install-test:
	pip install -i https://test.pypi.org/simple/ $(PACKAGE_NAME)

install:
ifeq ($(HEAD_TAGGED), 1)
	pip install .
else 
	@echo "Will not install unversioned"
	exit 1
endif 

uninstall:
	pip uninstall $(PACKAGE_NAME)

clean:
	rm -rf build 
	rm -rf dist 
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ | xargs rm -rvf 
	find . -type f -name *.pyc | xargs rm -vf 
