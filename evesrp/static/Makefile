SUBDIRS := js

.PHONY: all clean $(SUBDIRS)

all: $(SUBDIRS)

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C $$DIR clean; \
	done

$(SUBDIRS):
	$(MAKE) -C $@
