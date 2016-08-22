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
	# This target downloads a PhantomJS binary and installs it in the home
	# directory. Used in testing javascript and browser-based tests.
	wget https://s3.amazonaws.com/travis-phantomjs/phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	tar -xjf phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	mv phantomjs $(HOME)/phantomjs

# Depending on the value of TEST_SUITE, the travis-setup, travis and
# travis-success targets are defined differently.

# Travis Javascript testing:
ifneq (,$(findstring javascript,$(TEST_SUITE)))
travis-setup: $(HOME)/phantomjs
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls

# Travis documentation build testing:
else ifneq (,$(findstring docs,$(TEST_SUITE)))
travis-setup:
travis: docs
travis-success:

# Travis browser-based testing:
else ifneq (,$(findstring browser,$(TEST_SUITE)))
travis-setup: $(HOME)/phantomjs
	pip install coveralls
# Define TOXENV and SELENIUM_DRIVER for the test-python target
test-python: TOXENV := $(SRP_PYTHON)-sqlite-browser
# TODO: Add a better way of specifying the capabilities to test.
test-python: SELENIUM_DRIVER := "PhantomJS,Chrome,Firefox"
travis: test-python
travis-success:
	coveralls
	# TODO: Collect and bundle up Javascript coverage results

# Travis Python testing:
else
travis-setup:
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
