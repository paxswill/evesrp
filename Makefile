SHELL := /bin/sh
include variables.mk

.PHONY: all clean deep-clean doc-clean build-deps test test-python \
	test-javascript docs travis travis-success sdist upload

all:: docs

deep-clean: doc-clean clean
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

sdist: $(SUBDIRS) setup.py
	python setup.py sdist

upload: $(SUBDIRS) setup.py
	python setup.py sdist upload

test:: test-python test-javascript

test-python:
	nosetests \
		--with-html \
		--html-file=test-report.html \
		--with-coverage \
		--cover-erase \
		--cover-branch \
		--cover-package=evesrp \
		-w tests_python
	coverage html -d coverage-report

docs:
	$(MAKE) -C doc html

ifneq (,$(findstring javascript,$(TEST_SUITE)))
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls
else
travis: test-python
travis-success:
	coveralls
endif

node_modules node_modules/% $(NODE_BIN)/% (NODE_MODULES)/%: package.json
	npm install

include translations.mk
include misc.mk
include javascript.mk
