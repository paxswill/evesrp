ifndef DEBUG
UGLIFY_OPTS ?= -m -c
endif
UGLIFY_OPTS += --source-map-include-sources
BROWSERIFY_OPTS := -t coffeeify -t hbsfy \
                   --extension=".coffee" \
                   --extension=".hbs"
BOOTSTRAP = $(THIRDPARTY)/bootstrap/js

all: evesrp.min.js

browserify.mk: Makefile main.coffee
	echo "evesrp.js: $(shell $(NODE_BIN)/browserify main.coffee $(BROWSERIFY_OPTS) --list)" > $@

$(NODE_MODULES)/%:
	node install

-include browserify.mk

evesrp.js: main.coffee
	$(NODE_BIN)/browserify main.coffee $(BROWSERIFY_OPTS) -o evesrp.js

evesrp.min.js: evesrp.js
	$(NODE_BIN)/uglifyjs evesrp.js \
		$(UGLIFY_OPTS) \
		--output $@ \
		--prefix relative \
		--input-source-map \
		--source-map evesrp.min.js.map

clean:
	rm -f evesrp.min.js evesrp.min.js.map evesrp.js
