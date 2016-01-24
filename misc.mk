include variables.mk
##### CSS #####
LESSC ?= $(NODE_BIN)/lessc
LESSC_OPTS ?= --source-map \
			  --source-map-less-inline \
			  --source-map-basepath="$(PROJECT_ROOT)"
CSS_DIR := $(STATIC_DIR)/css

all:: $(CSS_DIR)/evesrp.css

clean::
	rm -f $(CSS_DIR)/evesrp.css $(CSS_DIR)/evesrp.css.map

less.mk: $(CSS_DIR)/custom.less $(LESSC)
	$(LESSC) \
		--include-path="$(NODE_MODULES)" \
		--depends \
		$< \
		$(<:%.less=%.css) > $@

include less.mk

$(CSS_DIR)/evesrp.css: $(CSS_DIR)/custom.less
	$(LESSC) \
		--include-path="$(NODE_MODULES)" \
		$(LESSC_OPTS) \
		$^ \
		$@


##### ZeroClipboard SWF #####
$(STATIC_DIR)/ZeroClipboard.swf: $(NODE_MODULES)/zeroclipboard/dist/ZeroClipboard.swf
	cp "$^" "$@"

$(NODE_MODULES)/zeroclipboard/dist/ZeroClipboard.swf: $(NODE_MODULES)


##### Fonts #####
NODE_MODULES := $(shell npm root)
FONTAWESOME := $(NODE_MODULES)/font-awesome/fonts
BOOTSTRAP := $(NODE_MODULES)/bootstrap/fonts
SUFFIXES := eot ttf svg woff woff2
FONT_DIR := $(STATIC_DIR)/fonts
FONTS := \
	FontAwesome.otf \
	$(addprefix fontawesome-webfont.,$(SUFFIXES)) \
	$(addprefix glyphicons-halflings-regular.,$(SUFFIXES))
FONTS := $(addprefix $(FONT_DIR)/,$(FONTS))

all:: $(FONTS)

clean::
	rm -f $(addprefix $(FONT_DIR)/*.,$(SUFFIXES)) $(FONT_DIR)/*.otf

$(foreach SUFFIX,$(SUFFIXES) otf, \
	$(eval vpath %.$(SUFFIX) $(FONTAWESOME) $(BOOTSTRAP)))

$(FONTS): $(FONT_DIR)/%: %
	cp "$^" "$@"
