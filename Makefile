SHELL := /bin/sh
include variables.mk

.PHONY: all clean deep-clean doc-clean build-deps test test-python \
	test-javascript docs travis-setup travis travis-success sdist upload \
	javascript translations

all:: docs javascript translations

distclean:: clean doc-clean
	rm -rf node_modules

build-deps: node_modules
	pip install tox babel coverage
	npm install

sdist: javascript translations setup.py
	python setup.py sdist

upload: javascript translations setup.py
	python setup.py sdist upload

# test-javascript gets added to the test target in javascript.mk
test:: test-python

test-python: translations
	coverage erase
	tox
	coverage combine
	coverage html -d coverage-report

clean::
	rm -f test-report*.html .coverage.*
	rm -rf coverage-report tests_python/coverage-report

docs:
	tox -e docs

# Travis targets
ifneq (,$(findstring javascript,$(TEST_SUITE)))
travis-setup:
	wget https://s3.amazonaws.com/travis-phantomjs/phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	tar -xjf phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	mv phantomjs $(HOME)/phantomjs
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls
else
travis-setup:
	pip install coveralls
travis:
	tox -e $(SRP_PYTHON)-$(SRP_DB)
travis-success:
	coverage combine
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
