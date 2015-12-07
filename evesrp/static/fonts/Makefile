FONTAWESOME := $(NODE_MODULES)/font-awesome/fonts
BOOTSTRAP := $(NODE_MODULES)/bootstrap/fonts
SUFFIXES := eot ttf svg woff woff2
FONT_FILES := \
	FontAwesome.otf \
	$(addprefix fontawesome-webfont.,$(SUFFIXES)) \
	$(addprefix glyphicons-halflings-regular.,$(SUFFIXES)) \


.PHONY: all clean

all: $(FONT_FILES)

clean:
	rm -f $(addprefix ./*,$(SUFFIXES)) ./*.woff2 ./*.otf

fontawesome-webfont.%: $(FONTAWESOME)/fontawesome-webfont.%
	cp "$^" "$@"

FontAwesome.otf: $(FONTAWESOME)/FontAwesome.otf
	cp "$^" "$@"

glyphicons-halflings-regular.%: $(BOOTSTRAP)/glyphicons-halflings-regular.%
	cp "$^" "$@"
