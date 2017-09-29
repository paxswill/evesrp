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
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls
else ifneq (,$(findstring docs,$(TEST_SUITE)))
travis-setup:
travis: docs
travis-success:
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
