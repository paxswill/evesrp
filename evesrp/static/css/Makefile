LESSC ?= lessc
BOOTSTRAP ?= $(THIRDPARTY)/bootstrap/less
FONTAWESOME ?= $(THIRDPARTY)/fontawesome/less
TOKENFIELD ?= $(THIRDPARTY)/bootstrap-tokenfield/less
LESSC_OPTS ?= --source-map \
			  --source-map-less-inline

all: bootstrap.css bootstrap.min.css bootstrap-theme.css \
	bootstrap-theme.min.css font-awesome.css font-awesome.min.css \
	bootstrap-tokenfield.css bootstrap-tokenfield.min.css \
	tokenfield-typeahead.css tokenfield-typeahead.min.css

clean:
	rm -f bootstrap*.css font-awesome*.css *.map tokenfield*.css

$(BOOTSTRAP) $(FONTAWESOME) $(TOKENFIELD):
	git submodule -u -i "$@"

bootstrap.css: $(BOOTSTRAP)
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		"$(BOOTSTRAP)/bootstrap.less" \
		$@

bootstrap.min.css: $(BOOTSTRAP)
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		-x \
		"$(BOOTSTRAP)/bootstrap.less" \
		$@

bootstrap-theme.css: $(BOOTSTRAP)
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		"$(BOOTSTRAP)/theme.less" \
		$@

bootstrap-theme.min.css: $(BOOTSTRAP)
	$(LESSC) \
		--include-path="$(BOOTSTRAP)" \
		$(LESSC_OPTS) \
		-x \
		"$(BOOTSTRAP)/theme.less" \
		$@

font-awesome.css: $(FONTAWESOME)
	$(LESSC) \
		--include-path="$(FONTAWESOME)" \
		$(LESSC_OPTS) \
		"$(FONTAWESOME)/font-awesome.less" \
		$@

font-awesome.min.css: $(FONTAWESOME)
	$(LESSC) \
		--include-path="$(FONTAWESOME)" \
		$(LESSC_OPTS) \
		-x \
		"$(FONTAWESOME)/font-awesome.less" \
		$@

bootstrap-tokenfield.css tokenfield-typeahead.css: $(TOKENFIELD)
	# It tries to depend on bower including bootstrap. How cute.
	sed -e s,'\.\./bower_components/','',g "$^/$(@:css=less)" | \
	$(LESSC) \
		--include-path="$^:$(THIRDPARTY)" \
		$(LESSC_OPTS) \
		- \
		$@

bootstrap-tokenfield.min.css tokenfield-typeahead.min.css: $(TOKENFIELD)
	# It tries to depend on bower including bootstrap. How cute.
	sed -e s,'\.\./bower_components/','',g "$^/$(@:min.css=less)" | \
	$(LESSC) \
		--include-path="$^:$(THIRDPARTY)" \
		$(LESSC_OPTS) \
		-x \
		- \
		$@
