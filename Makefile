# Work around a bug in Apple's version of Make where setting PATH doesn't stick
# unless SHELL is set first.
SHELL := /bin/sh
export PROJECT_ROOT := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
export NODE_MODULES := $(PROJECT_ROOT)node_modules
export PATH := $(NODE_MODULES)/.bin:$(PATH)
SUBDIRS := evesrp/translations evesrp/static
NODE_UTILS := \
	bootstrap \
	bower \
	browserify \
	cldr-core \
	cldr-dates-full \
	cldr-numbers-full \
	coffee-script \
	coffeeify \
	globalize \
	handlebars \
	hbsfy \
	jed \
	jquery \
	less \
	mocha \
	po2json \
	selectize \
	uglify-js \
	underscore \
	underscore.string \
	zeroclipboard

.PHONY: all clean distclean build-deps test test-python test-javascript docs \
	node-pkgs $(SUBDIRS)

all: docs messages.pot node-pkgs bower_components $(SUBDIRS)

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C "$$DIR" clean; \
	done
	rm -f generated_messages.pot messages.pot

doc-clean:
	$(MAKE) -C doc clean

$(SUBDIRS):
	$(MAKE) -C "$@"

bower_components: bower.json node_modules/bower
	node_modules/.bin/bower install

build-deps: node-pkgs bower_components
	pip install -r requirements.txt
	tests/mariadb.sh
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

test: test-python test-javascript

test-python:
	nosetests \
		--with-html \
		--html-file=test-report.html \
		-w tests_python

test-javascript: 
	mocha \
		--compilers coffee:coffee-script/register \
		--reporter dot \
		--ui tdd \
		tests_javascript/*.coffee

docs:
	$(MAKE) -C doc html

generated_messages.pot: babel.cfg evesrp/*.py evesrp/*/*.py evesrp/templates/*.html
	echo $?
	pybabel extract \
		-F babel.cfg \
		-o generated_messages.pot \
		-c "TRANS:" \
		--project=EVE-SRP \
		--version=0.10.6-dev \
		-k lazy_gettext \
		-s \
		--msgid-bugs-address=paxswill@paxswill.com \
		--copyright-holder="Will Ross" \
		.

messages.pot: generated_messages.pot manual_messages.pot
	cat $^ > $@

node-pkgs: $(foreach pkg,$(NODE_UTILS),node_modules/$(pkg))

node_modules/%:
	npm install $*

node_modules/handlebars:
	npm install handlebars@3

node_modules/bootstrap:
	npm install bootstrap@3
