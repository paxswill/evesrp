LESSC ?= lessc
BOOTSTRAP ?= $(THIRDPARTY)/bootstrap/less
FONTAWESOME ?= $(THIRDPARTY)/font-awesome/less
TOKENFIELD ?= $(THIRDPARTY)/bootstrap-tokenfield/less
LESSC_OPTS ?= --source-map \
			  --source-map-less-inline

all: bootstrap.css bootstrap.min.css bootstrap-theme.css \
	bootstrap-theme.min.css font-awesome.css font-awesome.min.css \
	bootstrap-tokenfield.css bootstrap-tokenfield.min.css \
	tokenfield-typeahead.css tokenfield-typeahead.min.css

clean:
	rm -f bootstrap*.css font-awesome*.css *.map tokenfield*.css

bootstrap.css:
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		"$(BOOTSTRAP)/bootstrap.less" \
		$@

bootstrap.min.css:
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		-x \
		"$(BOOTSTRAP)/bootstrap.less" \
		$@

bootstrap-theme.css:
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		"$(BOOTSTRAP)/theme.less" \
		$@

bootstrap-theme.min.css:
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		-x \
		"$(BOOTSTRAP)/theme.less" \
		$@

font-awesome.css:
	$(LESSC) \
		--include-path="$(FONTAWESOME)" \
		$(LESSC_OPTS) \
		"$(FONTAWESOME)/font-awesome.less" \
		$@

font-awesome.min.css:
	$(LESSC) \
		--include-path="$(FONTAWESOME)" \
		$(LESSC_OPTS) \
		-x \
		"$(FONTAWESOME)/font-awesome.less" \
		$@

bootstrap-tokenfield.css tokenfield-typeahead.css:
	$(LESSC) \
		--include-path="$(THIRDPARTY)" \
		$(LESSC_OPTS) \
		"$(TOKENFIELD)/$(@:css=less)" \
		$@

bootstrap-tokenfield.min.css tokenfield-typeahead.min.css:
	$(LESSC) \
		--include-path="$(THIRDPARTY)" \
		$(LESSC_OPTS) \
		-x \
		"$(TOKENFIELD)/$(@:min.css=less)" \
		$@
