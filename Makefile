SUBDIRS := evesrp/static

.PHONY: all clean build-deps $(SUBDIRS)

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

sdist: $(SUBDIRS) setup.py
	python setup.py sdist

upload: $(SUBDIRS) setup.py
	python setup.py sdist upload
