LESSC ?= $(NODE_BIN)/lessc
LESSC_OPTS ?= --source-map \
			  --source-map-less-inline \
			  --source-map-basepath="$(PROJECT_ROOT)"

all: evesrp.css

clean:
	rm -f custom.css custom.css.map

less.mk: Makefile custom.less
	$(LESSC) \
		--include-path="$(NODE_MODULES)" \
		--depends \
		custom.less \
		custom.css > less.mk

-include less.mk

evesrp.css: custom.less
	$(LESSC) \
		--include-path="$(NODE_MODULES)" \
		$(LESSC_OPTS) \
		$^ \
		$@
