LESSC ?= lessc
BOOTSTRAP ?= $(THIRDPARTY)/bootstrap/less
FONTAWESOME ?= $(THIRDPARTY)/fontawesome/less
LESSC_OPTS ?= --source-map \
			  --source-map-less-inline

all: bootstrap.css bootstrap.min.css bootstrap-theme.css \
	bootstrap-theme.min.css font-awesome.css font-awesome.min.css

clean:
	rm -f bootstrap*.css font-awesome*.css *.map

$(BOOTSTRAP) $(FONTAWESOME):
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
