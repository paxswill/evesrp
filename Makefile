SUBDIRS := evesrp/static

.PHONY: all clean build-deps test $(SUBDIRS)

all: $(SUBDIRS)

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C "$$DIR" clean; \
	done

$(SUBDIRS):
	$(MAKE) -C "$@"

build-deps:
	pip install -r requirements.txt
	npm install -g less uglify-js
ifneq (,$(findstring psycopg2,$(DB)))
	pip install psycopg2
else ifneq (,$(findstring pymysql,$(DB)))
	pip install pymysql
else ifneq (,$(findstring cymysql,$(DB)))
	pip install cython cymysql
endif

sdist: $(SUBDIRS) setup.py
	python setup.py sdist

upload: $(SUBDIRS) setup.py
	python setup.py sdist upload

test:
	python -m unittest discover
