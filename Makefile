.PHONY: build docs

BASE_DOCS_URL = deploy@tangledframework.org:~/apps/tangled.website/public/docs

all: build

build:
	@buildout

test:
	@test -f ./bin/tangled || $(MAKE) build
	@./bin/tangled test

sdist: clean build
	@./bin/python setup.py sdist

docs:
	@test -f ./bin/sphinx-build || $(MAKE) build
	@./bin/sphinx-build docs docs/_build

upload-docs: DOCS_URL = $(BASE_DOCS_URL)/$(shell basename $(shell pwd))
upload-docs:
	@test -d ./docs/_build || $(MAKE) docs
	@echo "Uploading docs to $(DOCS_URL)"
	@rsync -rlvz --delete docs/_build/ $(DOCS_URL)

clean-buildout:
	@echo "Removing Buildout directories and files..."
	@rm -vrf .installed.cfg bin develop-eggs parts

clean-dist:
	@echo "Removing dist-related directories..."
	@rm -vrf build dist *.egg-info

clean-pycache:
	@echo "Removing __pycache__ directories..."
	@find . -type d -name __pycache__ | xargs rm -rf

clean: clean-buildout clean-dist clean-pycache
