include variables.mk
.DELETE_ON_ERROR:

JS_DIR := $(STATIC_DIR)/js


##### Compiled Globalize Files #####
GLOBALIZE_COMPILER := $(NODE_BIN)/globalize-compiler
COMPILED_GLOBALIZE_FILES := $(foreach locale,$(subst en-US,en,$(DASH_LOCALES)),\
	$(JS_DIR)/globalize-$(locale).js)

$(COMPILED_GLOBALIZE_FILES): $(JS_DIR)/globalize-%.js: $(JS_DIR)/evesrp.js
	$(GLOBALIZE_COMPILER) -l $* -o $@ $<

clean::
	rm -f $(addprefix $(JS_DIR)/,globalize-*.js)


##### Browserify #####
BROWSERIFY_OPTS := -t coffeeify -t hbsfy \
                   --extension=".coffee" \
                   --extension=".hbs" \
				   --debug
BROWSERIFY ?= $(NODE_BIN)/browserify
EXORCIST ?= $(NODE_BIN)/exorcist
COFFEE_FILES := $(wildcard $(JS_DIR)/*.coffee)

clean::
	rm -f $(addprefix $(JS_DIR)/,evesrp.js evesrp.js.map translations.js formatters.js)

distclean::
	rm -f browserify.mk

include browserify.mk

BROWSERIFY_MAKEFILE_CMD = $(NODE_BIN)/browserify $(JS_DIR)/main.coffee $(BROWSERIFY_OPTS) \
	--list | \
	sed s,$(PROJECT_ROOT)/,, | \
	tr '\n' ' '

browserify.mk: $(NODE_MODULES) $(NODE_MODULES)/evesrp
	@printf "Creating browserify.mk..."
	@printf "$(JS_DIR)/evesrp.js tests_javascript/evesrp.test.js: $(shell $(BROWSERIFY_MAKEFILE_CMD))" > $@
	@printf "done\n"

$(NODE_MODULES)/evesrp:
	ln -s $(JS_DIR) $@

# The dependencies for evesrp.js are included from browserify.mk
$(JS_DIR)/evesrp.js: $(NODE_MODULES)/evesrp
	$(BROWSERIFY) \
		$(BROWSERIFY_OPTS) \
		-r globalize/dist/globalize-runtime \
		-r globalize/dist/globalize-runtime/number \
		-r globalize/dist/globalize-runtime/date \
		-e $(JS_DIR)/main.coffee \
		-o $@

# Bundle the compiled formatters
$(JS_DIR)/formatters.js: $(COMPILED_GLOBALIZE_FILES)
	$(BROWSERIFY) \
		$(foreach mod,$^,-r $(mod):evesrp/$(basename $(notdir $(mod)))) \
		$(foreach gmod,number date,-x globalize/dist/globalize-runtime/$(gmod)) \
		-x globalize/dist/globalize-runtime \
		-o $@

# Externalize source map for evesrp.js
clean::
	rm -f $(addprefix $(JS_DIR)/,*.map *.mapless)

$(JS_DIR)/evesrp.js.map: %.map: %
	$(EXORCIST) -b $(JS_DIR) $@ < $< > $<.mapless
	mv -f $<.mapless $<


##### Minification #####
UGLIFY ?= $(NODE_BIN)/uglifyjs
ifndef DEBUG
UGLIFY_OPTS ?= -m -c
endif
UGLIFY_OPTS += --source-map-include-sources

javascript:: $(JS_DIR)/evesrp.min.js $(JS_DIR)/formatters.min.js

clean::
	rm -f $(addprefix $(JS_DIR)/,evesrp.min.js formatters.min.js)

# Include the source map for evesrp.js
$(JS_DIR)/evesrp.min.js: $(JS_DIR)/evesrp.js.map
$(JS_DIR)/evesrp.min.js: UGLIFY_OPTS += \
	--in-source-map $(JS_DIR)/evesrp.js.map
	# --prefix relative

$(JS_DIR)/%.min.js: $(JS_DIR)/%.js
	$(UGLIFY) \
		$< \
		$(UGLIFY_OPTS) \
		--prefix relative \
		--source-map $@.map \
		--source-map-url $(notdir $@.map) \
		--output $@


##### Javascript testing
TESTS_COFFEE := $(wildcard tests_javascript/test_*.coffee)
TESTS_JS := $(TESTS_COFFEE:.coffee=.js)
ifeq "$(TRAVIS)" "true"
PHANTOMJS := $(HOME)/phantomjs
else ifeq "$(patsubst 2.%,2,$(shell phantomjs --version))" "2"
PHANTOMJS := $(shell which phantomjs)
else
PHANTOMJS := $(NODE_MODULES)/phantomjs2/bin/phantomjs
endif

test:: test-javascript

test-javascript: tests_javascript/tests.html tests_javascript/evesrp.test.js
test-javascript:
	$(PHANTOMJS) \
		$(NODE_MODULES)/mocha-phantomjs-core/mocha-phantomjs-core.js \
		$< \
		spec \
		'{"hooks": "$(PROJECT_ROOT)tests_javascript/hooks"}'
	$(NODE_BIN)/istanbul report \
		--root tests_javascript/coverage \
		--dir tests_javascript/coverage

clean::
	rm -f $(addprefix tests_javascript/,test_*.js evesrp.test.js tests.html translations.js)
	rm -rf tests_javascript/coverage

# Instrument evesrp.test.js for code coverage
tests_javascript/evesrp.test.js: BROWSERIFY_OPTS := \
	--debug \
	-t hbsfy \
	--extension=".hbs" \
	--extension=".coffee" \
	-t [ browserify-coffee-coverage --instrumentor=istanbul ]\
	$(foreach mod,$(COFFEE_FILES), \
		-r $(mod):evesrp/$(basename $(notdir $(mod))))

tests_javascript/evesrp.test.js: $(NODE_MODULES)/evesrp
	$(BROWSERIFY) -e $(JS_DIR)/main.coffee $(BROWSERIFY_OPTS) -o $@

tests_javascript/translations.js: $(JSON_LOCALES) $(COMPILED_GLOBALIZE_FILES)
	$(BROWSERIFY) \
		$(foreach file,$(COMPILED_GLOBALIZE_FILES),\
		-r $(file):evesrp/$(basename $(notdir $(file)))) \
		-r $(STATIC_DIR)/translations/en-US.json:evesrp/translations/en-US.json \
		-o $@

# This excludes the evesrp.js files from the test bundles
$(TESTS_JS): BROWSERIFY_OPTS += $(foreach \
	mod,$(basename $(notdir $(COFFEE_FILES))),-x evesrp/$(mod)) \
	-x evesrp/translations/en-US.json

$(TESTS_JS): %.js: %.coffee $(COFFEE_FILES) $(NODE_MODULES)/evesrp
	$(BROWSERIFY) $(BROWSERIFY_OPTS) "$<" -o "$@"

define newline


endef

define TEST_HTML_START
<!DOCTYPE html>
<html lang="en-US">
  <head>
    <meta charset="utf-8">
    <title>Mocha Tests</title>
    <link href="../node_modules/mocha/mocha.css" rel="stylesheet" />
  </head>
  <body>
    <div id="fixtures" style="display: none"></div>
    <div id="mocha"></div>
    <script src="../node_modules/mocha/mocha.js"></script>
    <script src="./evesrp.test.js"></script>
    <script src="./translations.js"></script>
    <script>mocha.setup({
    "ui": "tdd",
    "globals": "scriptRoot",
    });</script>

endef

define TEST_HTML_END
    <script>
if (window.initMochaPhantomJS !== undefined) {
  window.initMochaPhantomJS();
}
mocha.checkLeaks();
mocha.run();
    </script>
  </body>
</html>

endef

tests_javascript/tests.html: $(TESTS_JS) tests_javascript/translations.js javascript.mk
	printf '$(subst $(newline),\n,${TEST_HTML_START})' > $@
	printf "$(foreach test_js,$(TESTS_JS),\
		<script src="$(subst tests_javascript/,,$(test_js))"></script>)\n" >> $@
	printf '$(subst $(newline),\n,${TEST_HTML_END})' >> $@
