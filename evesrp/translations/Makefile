LANGUAGES := $(filter-out %Makefile,$(wildcard ./*))

all: $(foreach lang,$(LANGUAGES),$(lang)/LC_MESSAGES/messages.mo)

clean:
	rm -fv ./*/LC_MESSAGES/messages.mo

.PHONY: all clean

%/LC_MESSAGES/messages.mo: %/LC_MESSAGES/messages.po
	pybabel compile \
		-i "$<" \
		-o "$@"


%/LC_MESSAGES/messages.po: $(PROJECT_ROOT)messages.pot
	pybabel update \
		-l $(subst ./,,$*) \
		-i "$<" \
		-o "$@"
