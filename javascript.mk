include variables.mk


##### Client File Pipeline #####
JS_DIR := $(STATIC_DIR)/js
REAL_JS_DIR := $(realpath ./$(JS_DIR))
ifndef DEBUG
UGLIFY_OPTS ?= -m -c
endif
UGLIFY_OPTS += --source-map-include-sources
BROWSERIFY_OPTS := -t coffeeify -t hbsfy \
                   --extension=".coffee" \
                   --extension=".hbs"
BROWSERIFY ?= $(NODE_BIN)/browserify
COFFEE_FILES := $(wildcard $(JS_DIR)/*.coffee)

all:: $(JS_DIR)/evesrp.min.js

clean::
	rm -f $(addprefix $(JS_DIR)/,evesrp.min.js evesrp.min.js.map evesrp.js)

include browserify.mk

BROWSERIFY_MAKEFILE_CMD = $(NODE_BIN)/browserify $(JS_DIR)/main.coffee $(BROWSERIFY_OPTS) \
	--list | \
	sed s,$(PROJECT_ROOT)/,, | \
	tr '\n' ' '

browserify.mk: $(BROWSERIFY)
	@printf "Creating browserify.mk..."
	@printf "$(JS_DIR)/evesrp.js tests_javascript/evesrp.test.js: $(shell $(BROWSERIFY_MAKEFILE_CMD))" > $@
	@printf "done\n"

# The dependencies for evesrp.js are included from browserify.mk
$(JS_DIR)/evesrp.js: $(NODE_MODULES)/evesrp
	$(BROWSERIFY) -e $(JS_DIR)/main.coffee $(BROWSERIFY_OPTS) -o $@


$(NODE_MODULES)/evesrp:
	ln -s $(REAL_JS_DIR) $@

$(JS_DIR)/evesrp.min.js: $(JS_DIR)/evesrp.js
	$(NODE_BIN)/uglifyjs $(JS_DIR)/evesrp.js \
		$(UGLIFY_OPTS) \
		--output $@ \
		--prefix relative \
		--input-source-map \
		--source-map $(JS_DIR)/evesrp.min.js.map


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

PYTHON_VERSION := $(shell python -c \
	"from __future__ import print_function; \
	import sys; \
	print(sys.version_info.major)")

KILL_STATIC_SERVER := kill \
	`ps -o pid -o args | \
	 egrep -e '[0-9]+ python -m (Simple)?[hH][tT][tT][pP]\.?[sS]erver 5000' | \
	 egrep -oe '^ *[0-9]+'`

test:: test-javascript

test-javascript: tests_javascript/tests.html
	# kill any lingering static servers
	-$(KILL_STATIC_SERVER)
ifeq "$(PYTHON_VERSION)" "2"
	cd ./evesrp && python -m SimpleHTTPServer 5000 > /dev/null &
else
	cd ./evesrp && python -m http.server 5000 > /dev/null &
endif
	$(NODE_BIN)/mocha-phantomjs \
		-s webSecurityEnabled=false \
		--no-color \
		--hooks tests_javascript/hooks.js \
		--path $(PHANTOMJS) \
		$<
	$(KILL_STATIC_SERVER)
	$(NODE_BIN)/istanbul report \
		--root tests_javascript/coverage \
		--dir tests_javascript/coverage \
		lcovonly

clean::
	rm -f \
		tests_javascript/tests_*.js \
		evesrp.test.js \
		tests_javascript/tests.html
	rm -rf tests_javascript/coverage

# Instrument evesrp.test.js for code coverage
tests_javascript/evesrp.test.js: BROWSERIFY_OPTS += \
	-t [ browserify-istanbul --ignore **/*.hbs ] \
	$(foreach mod,$(COFFEE_FILES), \
		-r ./$(mod):evesrp/$(basename $(notdir $(mod))))

tests_javascript/evesrp.test.js: $(NODE_MODULES)/evesrp
	$(BROWSERIFY) -e $(JS_DIR)/main.coffee $(BROWSERIFY_OPTS) -o $@

# This excludes the evesrp.js files from the test bundles
$(TESTS_JS): BROWSERIFY_OPTS += $(foreach \
	mod,$(basename $(notdir $(COFFEE_FILES))),-x evesrp/$(mod))

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
    <div id="mocha"></div>
    <script type="text/javascript">scriptRoot = "http://localhost:5000";</script>
    <script src="../node_modules/mocha/mocha.js"></script>
    <script src="./evesrp.test.js"></script>
    <script>mocha.setup("tdd")</script>

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

tests_javascript/tests.html: $(TESTS_JS) Makefile tests_javascript/evesrp.test.js
	printf '$(subst $(newline),\n,${TEST_HTML_START})' > $@
	printf "$(foreach test_js,$(TESTS_JS),\
		<script src="$(subst tests_javascript/,,$(test_js))"></script>)\n" >> $@
	printf '$(subst $(newline),\n,${TEST_HTML_END})' >> $@
