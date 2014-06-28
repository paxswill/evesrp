UGLIFY ?= uglifyjs
ifndef DEBUG
UGLIFY_OPTS ?= -m -c
endif
UGLIFY_OPTS += --source-map-include-sources
BOOTSTRAP = $(THIRDPARTY)/bootstrap/js

SOURCE_NAMES := \
	$(BOOTSTRAP)/dropdown \
	$(BOOTSTRAP)/tab \
	$(BOOTSTRAP)/transition \
	$(BOOTSTRAP)/collapse \
	$(BOOTSTRAP)/tooltip \
	$(BOOTSTRAP)/alert \
	$(BOOTSTRAP)/modal \
	$(THIRDPARTY)/handlebars/handlebars.runtime \
	custom-handlebars \
	custom-requests \
	$(THIRDPARTY)/underscore/underscore \
	$(THIRDPARTY)/pourover/pourover \
	$(THIRDPARTY)/history.js/scripts/bundled/html4+html5/jquery.history \
	$(THIRDPARTY)/bootstrap-tokenfield/js/bootstrap-tokenfield \
	$(THIRDPARTY)/zeroclipboard/ZeroClipboard \
	custom-pourover \
	$(THIRDPARTY)/typeahead.js/dist/typeahead.bundle \
	custom-typeahead \
	custom-divisions \
	handlebars-templates
JS_SOURCE = $(patsubst %,%.js,$(SOURCE_NAMES))

all: evesrp.min.js

handlebars-templates.js: $(wildcard templates/*.hbs)
	handlebars -e hbs templates -f $@ -k each -k if -k csrf

evesrp.min.js: $(JS_SOURCE)
	$(UGLIFY) $^ \
		$(UGLIFY_OPTS) \
		--output $@ \
		--source-map evesrp.min.js.map

clean:
	rm -f evesrp.min.js evesrp.min.js.map handlebars-templates.js
