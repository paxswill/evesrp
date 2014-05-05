UGLIFY ?= uglifyjs
UGLIFY_OPTS ?= -m \
			   -c \
			   --source-map-include-sources
BOOTSTRAP = $(THIRDPARTY)/bootstrap/js

SOURCE_NAMES := \
	$(BOOTSTRAP)/dropdown \
	$(BOOTSTRAP)/tab \
	$(BOOTSTRAP)/transition \
	$(BOOTSTRAP)/collapse \
	$(BOOTSTRAP)/tooltip \
	$(BOOTSTRAP)/popover \
	custom-requests \
	$(THIRDPARTY)/underscore/underscore \
	$(THIRDPARTY)/pourover/pourover \
	$(THIRDPARTY)/history_js/scripts/bundled/html4+html5/jquery.history \
	custom-pourover \
	$(THIRDPARTY)/typeahead_js/dist/typeahead.bundle \
	custom-typeahead
JS_SOURCE = $(patsubst %,%.js,$(SOURCE_NAMES))

all: evesrp.min.js

evesrp.min.js: $(JS_SOURCE)
	$(UGLIFY) $^ \
		$(UGLIFY_OPTS) \
		--output $@ \
		--source-map evesrp.min.js.map

clean:
	rm -f evesrp.min.js evesrp.min.js.map
