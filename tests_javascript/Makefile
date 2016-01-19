STATIC_JS := ../evesrp/static/js
TESTS_COFFEE := $(notdir $(wildcard ./test_*.coffee))
TESTS_JS := $(TESTS_COFFEE:.coffee=.js)

BROWSERIFY_OPTS := -t coffeeify -t hbsfy \
                   --extension=".coffee" \
                   --extension=".hbs"
BROWSERIFY_COVER_OPTS := $(BROWSERIFY_OPTS) \
                         -t [ browserify-istanbul --ignore **/*.hbs ]

.PHONY: $(STATIC_JS)/evesrp.js all

PYTHON_VERSION := $(shell python -c \
	"from __future__ import print_function; \
	import sys; \
	print(sys.version_info.major)")

KILL_STATIC_SERVER := kill \
	`ps -o pid -o args | \
	 egrep -e '[0-9]+ python -m (Simple)?[hH][tT][tT][pP]\.?[sS]erver 5000' | \
	 egrep -oe '^ *[0-9]+'`

all: tests.html
	# kill any lingering static servers
	-$(KILL_STATIC_SERVER)
ifeq "$(PYTHON_VERSION)" "2"
	cd ../evesrp && python -m SimpleHTTPServer 5000 > /dev/null &
else
	cd ../evesrp && python -m http.server 5000 > /dev/null &
endif
	$(NODE_BIN)/mocha-phantomjs \
		-s webSecurityEnabled=false \
		--no-color \
		--hooks hooks.js \
		tests.html
	$(KILL_STATIC_SERVER)
	$(NODE_BIN)/istanbul report --root coverage lcovonly

clean:
	rm -f tests_*.js tests.html
	rm -rf coverage

browserify.mk: Makefile $(TESTS_COFFEE)
	@echo "Creating browserify.mk"
	@echo "evesrp.js: $(shell $(NODE_BIN)/browserify $(addprefix -r ./,$(TESTS_COFFEE)) $(BROWSERIFY_OPTS) --list)" > $@

$(NODE_MODULES)/%:
	node install

-include browserify.mk

%.js: %.coffee browserify.mk
	$(NODE_BIN)/browserify $(BROWSERIFY_COVER_OPTS) "$<" -o "$@"

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
    <script>$$SCRIPT_ROOT = \"http://localhost:5000\";</script>
    <script src="../node_modules/mocha/mocha.js"></script>
    <script src="$(STATIC_JS)/evesrp.js"></script>
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

tests.html: $(TESTS_JS) Makefile
	printf '$(subst $(newline),\n,${TEST_HTML_START})' > $@
	printf "$(foreach test_js,$(TESTS_JS),\
		<script src="$(test_js)"></script>)\n" >> $@
	printf '$(subst $(newline),\n,${TEST_HTML_END})' >> $@
