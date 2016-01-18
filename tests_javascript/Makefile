STATIC_JS := ../evesrp/static/js
TESTS_COFFEE := $(notdir $(wildcard ./test_*.coffee))
TESTS_JS := $(TESTS_COFFEE:.coffee=.js)

BROWSERIFY_OPTS := -t coffeeify -t hbsfy \
                   --extension=".coffee" \
                   --extension=".hbs"

.PHONY: $(STATIC_JS)/evesrp.js all

PYTHON_VERSION := $(shell python -c "from __future__ import print_function; import sys; print(sys.version_info.major)")

all: tests.html
	# kill any lingering static servers
	-kill `ps -A -o pid -o args| egrep -e '[0-9]+ python -m (Simple)?[hH][tT][tT][pP]\.?[sS]erver 5000' | egrep -oe '^ *[0-9]+'`
ifeq "$(PYTHON_VERSION)" "2"
	cd ../evesrp && python -m SimpleHTTPServer 5000 > /dev/null &
else
	cd ../evesrp && python -m http.server 5000 > /dev/null &
endif
	mocha-phantomjs \
		-s webSecurityEnabled=false \
		--no-color \
		tests.html
	kill `ps -A -o pid -o args| egrep -e '[0-9]+ python -m (Simple)?[hH][tT][tT][pP]\.?[sS]erver 5000' | egrep -oe '^ *[0-9]+'`

clean:
	rm -f tests_*.js tests.html

$(STATIC_JS)/evesrp.js:
	$(MAKE) -C $(STATIC_JS) evesrp.js

%.js: %.coffee
	browserify $(BROWSERIFY_OPTS) "$^" -o "$@"

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

tests.html: $(TESTS_JS) $(STATIC_JS)/evesrp.js Makefile
	printf '$(subst $(newline),\n,${TEST_HTML_START})' > $@
	printf "$(foreach test_js,$(TESTS_JS),\
		<script src="$(test_js)"></script>)\n" >> $@
	printf '$(subst $(newline),\n,${TEST_HTML_END})' >> $@
