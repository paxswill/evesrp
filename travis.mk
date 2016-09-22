# Travis targets
$(HOME)/phantomjs:
	# This target downloads a PhantomJS binary and installs it in the home
	# directory. Used in testing javascript and browser-based tests.
	wget https://s3.amazonaws.com/travis-phantomjs/phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	tar -xjf phantomjs-2.0.0-ubuntu-12.04.tar.bz2
	mv phantomjs $(HOME)/phantomjs

install-coveralls:
	pip install -U coveralls

# Targets used for uploading test reports

deploy_key: deploy_key.enc
	openssl \
		aes-256-cbc \
		-K $(encrypted_20e576b606a4_key) \
		-iv $(encrypted_20e576b606a4_iv) \
		-in deploy_key.enc \
		-out deploy_key \
		-d
# SSH refuses to load a key readable by someone other than the owner
	chmod 0400 deploy_key
	ssh-add deploy_key

gh-pages: deploy_key
	git clone \
		--quiet \
		--branch=gh-pages \
		"git@github.com:paxswill/evesrp.git" \
		gh-pages

BUILD_REPORT_DIR := gh-pages/test_reports/$(TRAVIS_BUILD_NUMBER)
$(BUILD_REPORT_DIR): gh-pages
	mkdir -p "$@"

# Copy over the styles for Pytest reports
$(BUILD_REPORT_DIR)/assets: $(BUILD_REPORT_DIR)
	mkdir -p "$@"

$(BUILD_REPORT_DIR)/assets/style.css: $(BUILD_REPORT_DIR)/assets
	cp -f test-reports/assets/style.css "$@"

TEST_REPORTS := $(notdir $(wildcard test-reports/*.html))
BUILD_REPORTS := $(addprefix $(BUILD_REPORT_DIR)/, $(TEST_REPORTS))
$(BUILD_REPORTS): $(BUILD_REPORT_DIR)
$(BUILD_REPORTS): $(BUILD_REPORT_DIR)/%.html: test-reports/%.html
	cp -f "$<" "$@"

.PHONY: upload-reports
upload-reports: $(BUILD_REPORTS) $(BUILD_REPORT_DIR)/assets/style.css
	scripts/upload_reports.sh

clean::
	rm -rf gh-pages


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
travis-setup: $(HOME)/phantomjs install-coveralls
	pip install -U sauceclient
# Define TOXENV and SELENIUM_DRIVER for the test-python target
test-python: export TOXENV := $(SRP_PYTHON)-sqlite-browser
# TODO: Add a better way of specifying the capabilities to test.
test-python: export BROWSERS := PhantomJS;
test-python: export BROWSERS += Chrome,platform=Win10;
test-python: export BROWSERS += Chrome,platform=Win8.1;
test-python: export BROWSERS += Edge,platform=Win10;
test-python: export BROWSERS += InternetExplorer,platform=Win10;
test-python: export BROWSERS += InternetExplorer,platform=Win8.1;
test-python: export BROWSERS += Firefox;
travis: test-python
travis-success:
	coveralls
	# TODO: Collect and bundle up Javascript coverage results

# Travis Python testing:
else
travis-setup: install-coveralls
travis: test-python
travis-success:
	coveralls
endif
