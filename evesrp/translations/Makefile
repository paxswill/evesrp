LANGUAGES := $(filter-out %Makefile,$(wildcard ./*))
ifdef DEBUG
LANGUAGES := $(LANGUAGES) en_CA
endif

all: $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.mo)
ifndef DEBUG
	rm -rfv ./en_CA/
endif

clean:
	rm -fv ./*/LC_MESSAGES/messages.mo
	rm -fv ./en/LC_MESSAGES/messages.po

.PHONY: all clean en_CA/LC_MESSAGES/messages.po

%/LC_MESSAGES/messages.mo: %/LC_MESSAGES/messages.po
	pybabel compile \
		--use-fuzzy \
		-i "$<" \
		-o "$@"

%/LC_MESSAGES/messages.po: $(PROJECT_ROOT)messages.pot
	pybabel update \
		-l $(subst ./,,$*) \
		-i "$<" \
		-o "$@"

en_CA/LC_MESSAGES/messages.po: $(PROJECT_ROOT)messages.pot
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
