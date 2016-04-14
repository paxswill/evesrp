SHELL := /bin/sh
include variables.mk

.PHONY: all clean deep-clean doc-clean build-deps test test-python \
	test-javascript docs travis-setup travis travis-success sdist upload

all:: docs

distclean:: clean doc-clean
	rm -rf node_modules

doc-clean:
	$(MAKE) -C doc clean

build-deps: node_modules
	pip install -r requirements.txt
	npm install
	./scripts/mariadb.sh
ifneq (,$(findstring psycopg2,$(DB)))
	pip install psycopg2
else ifneq (,$(findstring pg8000,$(DB)))
	pip install pg8000
else ifneq (,$(findstring pymysql,$(DB)))
	pip install pymysql
else ifneq (,$(findstring cymysql,$(DB)))
	pip install cython cymysql
else ifneq (,$(findstring mysqldb,$(DB)))
	pip install mysql-python
endif

sdist: all setup.py
	python setup.py sdist

upload: all setup.py
	python setup.py sdist upload

test:: test-python test-javascript

test-python:
	coverage erase
	tox
	coverage combine
	coverage html -d coverage-report

clean::
	rm -f test-report*.html .coverage.*
	rm -rf coverage-report tests_python/coverage-report

docs:
	$(MAKE) -C doc html

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
	pip install tox
travis:
	tox -e $(SRP_PYTHON)-$(SRP_DB)
travis-success:
	coveralls
endif

$(NODE_MODULES): package.json
	npm install

$(NODE_MODULES)/%:
	npm install

include translations.mk
include misc.mk
include javascript.mk
