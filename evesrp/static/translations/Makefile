LOCALES := $(filter-out %Makefile,$(wildcard $(PROJECT_ROOT)evesrp/translations/*))
LOCALES := $(notdir $(LOCALES))
LOCALES := $(subst _,-,$(LOCALES))
PO2JSON_FLAGS := --fuzzy --format jed1.x --domain messages
ifdef DEBUG
PO2JSON_FLAGS += --pretty
endif

all: $(notdir $(foreach lang,$(LOCALES),$(lang).json))
ifndef DEBUG
	rm -fv en-CA.json
endif

clean:
	rm -fv ./*.json

.PHONY: all clean

# Give the locale with "_" as the tag separator. Creates a rule that'll output
# a JSON file using "-" as the tag separator.
define JSON_template
$(1).json: $$(PROJECT_ROOT)evesrp/translations/$(subst -,_,$(1))/LC_MESSAGES/messages.po
	$$(NODE_BIN)/po2json "$$<" "$$@" $$(PO2JSON_FLAGS)
endef

$(foreach locale,$(LOCALES),$(eval $(call JSON_template,$(locale))))
