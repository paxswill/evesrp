SUBDIRS := js css
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

ZeroClipboard.swf: $(THIRDPARTY)/zeroclipboard/ZeroClipboard.swf
	cp "$^" "$@"

$(THIRDPARTY)/zeroclipboard/ZeroClipboard.swf:
	git submodule update -i "$@"
