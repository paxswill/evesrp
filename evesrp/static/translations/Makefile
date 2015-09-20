LANGUAGES := $(wildcard $(PROJECT_ROOT)evesrp/translations/*)
PO2JSON_FLAGS := --fuzzy --format jed1.x --domain messages
ifdef DEBUG
PO2JSON_FLAGS += --pretty
endif

all: $(notdir $(foreach lang,$(LANGUAGES),$(lang).json))

%.json: $(PROJECT_ROOT)evesrp/translations/%/LC_MESSAGES/messages.po
	po2json "$<" "$@" $(PO2JSON_FLAGS)
