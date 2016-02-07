include variables.mk


TRANSLATIONS_DIR := evesrp/translations
UNDER_LOCALES := $(notdir $(wildcard $(TRANSLATIONS_DIR)/*))
ifdef DEBUG
# We use Canadian English for pseudolocalization testing. Sorry Canada.
UNDER_LOCALES += en_CA
endif


##### Base translations files #####
.PRECIOUS: $(TRANSLATIONS_DIR)/*/LC_MESSAGES/*.po
MO_FILES := $(foreach \
	lang,$(UNDER_LOCALES),$(TRANSLATIONS_DIR)/$(lang)/LC_MESSAGES/messages.mo)

all:: $(MO_FILES)
ifndef DEBUG
	rm -rfv $(TRANSLATIONS_DIR)/en_CA/
endif

clean::
	rm -fv $(TRANSLATIONS_DIR)/*/LC_MESSAGES/messages.mo
	rm -fv $(TRANSLATIONS_DIR)/en_CA/LC_MESSAGES/messages.po
	rm -fv messages.pot generated_messages.pot

$(MO_FILES): %.mo: %.po
	pybabel compile \
		--use-fuzzy \
		-i "$<" \
		-o "$@"

$(MO_FILES:.mo=.po): %.po: messages.pot
	pybabel update \
		-l $(*:$(TRANSLATIONS_DIR)/%/LC_MESSAGES/messages=%) \
		-i "$<" \
		-o "$@"

$(TRANSLATIONS_DIR)/en_CA/LC_MESSAGES/messages.po: messages.pot
ifeq ($(findstring unicode,$(DEBUG)),unicode)
	mkdir -p $(dir $@)
	podebug \
		--progress=none \
		--rewrite=unicode \
		--input="$<" \
		--output="$@"
else ifeq ($(findstring flipped,$(DEBUG)),flipped)
	mkdir -p $(dir $@)
	podebug \
		--progress=none \
		--rewrite=flipped \
		--input="$<" \
		--output="$@"
else ifeq ($(findstring xxx,$(DEBUG)),xxx)
	mkdir -p $(dir $@)
	podebug \
		--progress=none \
		--rewrite=xxx \
		--input="$<" \
		--output="$@"
else
	mkdir -p $(dir $@)
	podebug \
		--progress=none \
		--rewrite=en \
		--input="$<" \
		--output="$@"
endif

messages.pot: generated_messages.pot manual_messages.pot
	cat $^ > $@

# Figure out how to bump the version automatically
generated_messages.pot: babel.cfg evesrp/*.py evesrp/*/*.py evesrp/templates/*.html
	pybabel extract \
		-F babel.cfg \
		-o $@ \
		-c "TRANS:" \
		--project=EVE-SRP \
		--version=0.10.6-dev \
		-k lazy_gettext \
		-s \
		--msgid-bugs-address=paxswill@paxswill.com \
		--copyright-holder="Will Ross" \
		.


##### JSON translations #####
# STATIC_DIR is defined in the parent Makefile
JSON_TRANSLATIONS_DIR := $(STATIC_DIR)/translations
DASH_LOCALES := $(subst _,-,$(UNDER_LOCALES))
JSON_LOCALES := $(foreach \
	lang,$(DASH_LOCALES),$(JSON_TRANSLATIONS_DIR)/$(lang).json)
PO2JSON_FLAGS := --fuzzy --format jed1.x --domain messages
ifdef DEBUG
PO2JSON_FLAGS += --pretty
endif

all:: $(JSON_LOCALES)
ifndef DEBUG
	rm -fv $(JSON_TRANSLATIONS_DIR)/en-CA.json
endif

clean::
	rm -fv $(JSON_TRANSLATIONS_DIR)/*.json

# Give the locale with "_" as the tag separator. Creates a rule that'll output
# a JSON file using "-" as the tag separator.
# NODE_BIN is defined in the parent Makefile
define JSON_template
$(JSON_TRANSLATIONS_DIR)/$(subst _,-,$(1)).json: $(TRANSLATIONS_DIR)/$(1)/LC_MESSAGES/messages.po
	$$(NODE_BIN)/po2json "$$<" "$$@" $$(PO2JSON_FLAGS)
endef
$(foreach locale,$(UNDER_LOCALES),$(eval $(call JSON_template,$(locale))))
