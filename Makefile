SHELL := /bin/sh
include variables.mk

.PHONY: all clean deep-clean doc-clean build-deps test test-python \
	test-javascript docs travis-setup travis travis-success sdist upload \
	javascript translations static install-coveralls

all:: docs javascript translations static

distclean:: clean doc-clean
	rm -rf node_modules

build-deps: node_modules
	pip install -U tox babel coverage jinja2
	npm install

sdist: javascript translations static setup.py
	python setup.py sdist

upload: javascript translations static setup.py
	python setup.py sdist upload

# test-javascript gets added to the test target in javascript.mk
test:: test-python

test-python: translations javascript static
	coverage erase
	mkdir -p test-reports
	rm -rf test-reports/*
	tox
	coverage combine
	coverage html -d coverage-report

clean::
	rm -f test-report*.html .coverage.*
	rm -rf coverage-report tests_python/coverage-report

docs:
	tox -e docs


# Node packages
$(NODE_MODULES): package.json
	npm install

$(NODE_MODULES)/%:
	npm install

include translations.mk
include misc.mk
include javascript.mk
include travis.mk
