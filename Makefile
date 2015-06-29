SUBDIRS := evesrp/static

.PHONY: all clean distclean build-deps test docs $(SUBDIRS)

all: $(SUBDIRS) docs messages.pot

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C "$$DIR" clean; \
	done

distclean:
	rm -f messages.pot
	$(MAKE) -C doc clean

$(SUBDIRS):
	$(MAKE) -C "$@"

build-deps:
	pip install -r requirements.txt
	npm install -g less uglify-js bower handlebars@2.0.0-alpha.4
	bower install
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

messages.pot: $(vpath %.py evesrp) babel.cfg
	pybabel extract \
		-F babel.cfg \
		-o messages.pot \
		-c "TRANS:" \
		--project=EVE-SRP \
		--version=0.10.6-dev \
		-k lazy_gettext \
		-s \
		--msgid-bugs-address=paxswill@gmail.com \
		--copyright-holder="Will Ross" \
		.
