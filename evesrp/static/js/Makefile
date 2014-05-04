UGLIFY ?= uglifyjs
UGLIFY_OPTS ?= -m -c

SOURCE_NAMES := bootstrap custom-requests underscore pourover jquery.history \
	custom-pourover typeahead.bundle custom-typeahead
JS_SOURCE = $(patsubst %,%.js,$(SOURCE_NAMES))

all: evesrp.min.js

evesrp.min.js: $(JS_SOURCE)
	$(UGLIFY) $^ \
		$(UGLIFY_OPTS) \
		--output $@ \
		--source-map evesrp.min.js.map \

clean:
	rm -f evesrp.min.js evesrp.min.js.map
