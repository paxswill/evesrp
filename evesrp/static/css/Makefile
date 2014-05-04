LESSC ?= lessc
BOOTSTRAP ?= ../bootstrap/less
FONTAWESOME ?= ../fontawesome/less
LESSC_OPTS ?= --source-map \
			 --source-map-url=$@.map \
			 --source-map-rootpath=$(BOOTSTRAP)

all: bootstrap.css bootstrap.min.css bootstrap-theme.css \
	bootstrap-theme.min.css font-awesome.css font-awesome.min.css

clean:
	rm -f bootstrap*.css font-awesome*.css *.map

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
