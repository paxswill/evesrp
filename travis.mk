# Travis targets
$(HOME)/phantomjs:
	# This target downloads a PhantomJS binary and installs it in the home
	# directory. Used in testing javascript and browser-based tests.
	wget https://s3.amazonaws.com/travis-phantomjs/phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	tar -xjf phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	mv phantomjs $(HOME)/phantomjs


# Depending on the value of TEST_SUITE, the travis-setup, travis and
# travis-success targets are defined differently.

# Travis Javascript testing:
ifneq (,$(findstring javascript,$(TEST_SUITE)))
travis-setup: $(HOME)/phantomjs
travis: test-javascript
travis-success:
	cat tests_javascript/coverage/lcov.info | $(NODE_BIN)/coveralls

# Travis documentation build testing:
else ifneq (,$(findstring docs,$(TEST_SUITE)))
travis-setup:
travis: docs
travis-success:

# Travis browser-based testing:
else ifneq (,$(findstring browser,$(TEST_SUITE)))
travis-setup: $(HOME)/phantomjs
	pip install coveralls
	./scripts/sauce_connect.sh start
# Define TOXENV and SELENIUM_DRIVER for the test-python target
test-python: TOXENV := $(SRP_PYTHON)-sqlite-browser
# TODO: Add a better way of specifying the capabilities to test.
test-python: SELENIUM_DRIVER := "PhantomJS,Chrome,Firefox"
travis: test-python
travis-success:
	coveralls
	# TODO: Collect and bundle up Javascript coverage results

# Travis Python testing:
else
travis-setup:
	pip install coveralls
travis: test-python
travis-success:
	coveralls
endif
