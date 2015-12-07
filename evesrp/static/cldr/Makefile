LOCALES := $(notdir $(filter-out %Makefile,$(wildcard $(PROJECT_ROOT)evesrp/translations/*)))
LOCALES := $(LOCALES) en
CLDR_CORE := $(NODE_MODULES)/cldr-core
CLDR_DATES := $(NODE_MODULES)/cldr-dates-full
CLDR_NUMBERS := $(NODE_MODULES)/cldr-numbers-full

SHARED_FILES := \
	supplemental/likelySubtags.json \
	supplemental/numberingSystems.json \
	supplemental/timeData.json \
	supplemental/weekData.json

LOCALE_FILES = \
	main/$(locale)/numbers.json \
	main/$(locale)/ca-gregorian.json \
	main/$(locale)/timeZoneNames.json

ALL_LOCALES := \
	$(foreach locale,$(LOCALES),$(LOCALE_FILES))

.PHONY: all clean

all: $(SHARED_FILES) $(ALL_LOCALES)

clean:
	rm -rf main supplemental

supplemental/%: $(CLDR_CORE)/supplemental/%
	mkdir -p "$(dir $@)"
	cp "$^" "$@"

main/%/numbers.json: $(CLDR_NUMBERS)/main/%/numbers.json
	mkdir -p "$(dir $@)"
	cp "$^" "$@"

main/%/ca-gregorian.json: $(CLDR_DATES)/main/%/ca-gregorian.json
	mkdir -p "$(dir $@)"
	cp "$^" "$@"

main/%/timeZoneNames.json: $(CLDR_DATES)/main/%/timeZoneNames.json
	mkdir -p "$(dir $@)"
	cp "$^" "$@"
