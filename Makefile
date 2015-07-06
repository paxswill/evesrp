# Work around a bug in Apple's version of Make where setting PATH doesn't stick
# unless SHELL is set first.
SHELL := /bin/sh
export PATH := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))node_modules/.bin:$(PATH)
SUBDIRS := evesrp/static
NODE_UTILS := \
	bower \
	coffee-script \
	less \
	uglify-js

.PHONY: all clean distclean build-deps test docs $(SUBDIRS)

all: $(SUBDIRS) docs messages.pot node-pkgs bower_components

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C "$$DIR" clean; \
	done

distclean:
	rm -f messages.pot
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

test:
	nosetests --with-html --html-file=test-report.html -w tests/

docs:
	$(MAKE) -C doc html

messages.pot: babel.cfg evesrp/*.py evesrp/*/*.py evesrp/templates/*.html
	echo $?
	pybabel extract \
		-F babel.cfg \
		-o messages.pot \
		-c "TRANS:" \
		--project=EVE-SRP \
		--version=0.10.6-dev \
		-k lazy_gettext \
		-s \
		--msgid-bugs-address=paxswill@paxswill.com \
		--copyright-holder="Will Ross" \
		.

node-pkgs: $(foreach pkg,$(NODE_UTILS),node_modules/$(pkg))

node_modules/%:
	npm install $*

node_modules/handlebars:
	npm install handlebars@3
