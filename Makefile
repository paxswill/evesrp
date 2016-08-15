SHELL := /bin/sh
include variables.mk

.PHONY: all clean deep-clean doc-clean build-deps test test-python \
	test-javascript docs travis-setup travis travis-success sdist upload \
	javascript translations static

all:: docs javascript translations static

distclean:: clean doc-clean
	rm -rf node_modules

build-deps: node_modules
	pip install tox babel coverage jinja2
	npm install

sdist: javascript translations static setup.py
	python setup.py sdist

upload: javascript translations static setup.py
	python setup.py sdist upload

# test-javascript gets added to the test target in javascript.mk
test:: test-python

test-python: translations javascript static
# TODO: Split browser based testing into a different target
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

# Travis targets
$(HOME)/phantomjs:
	wget https://s3.amazonaws.com/travis-phantomjs/phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	tar -xjf phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	mv phantomjs $(HOME)/phantomjs

# Depending on the value of TEST_SUITE, the travis-setup, travis and
# travis-success targets are defined differently.
ifneq (,$(findstring javascript,$(TEST_SUITE)))
travis-setup: $(HOME)/phantomjs
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls
else ifneq (,$(findstring docs,$(TEST_SUITE)))
travis-setup:
travis: docs
travis-success:
else
# if SELENIUM_DRIVER is defined, download the phantomjs binary for browser
# testing.
ifeq (,$(SELENIUM_DRIVER))
travis-setup: $(HOME)/phantomjs
else
travis-setup:
endif
	pip install coveralls
travis: test-python
travis-success:
	coveralls
endif

# Node packages
$(NODE_MODULES): package.json
	npm install

$(NODE_MODULES)/%:
	npm install

include translations.mk
include misc.mk
include javascript.mk
