SUBDIRS := js css translations
export THIRDPARTY = $(abspath ../../bower_components)

.PHONY: all clean $(SUBDIRS)

all: $(SUBDIRS) ZeroClipboard.swf

clean:
	for DIR in $(SUBDIRS); do\
		$(MAKE) -C $$DIR clean; \
	done
	rm -f ZeroClipboard.swf

$(SUBDIRS):
	$(MAKE) -C $@

ZeroClipboard.swf: $(NODE_MODULES)/zeroclipboard/dist/ZeroClipboard.swf
	cp "$^" "$@"

$(NODE_MODULES)/zeroclipboard/dist/ZeroClipboard.swf:
	npm install zeroclipboard
