BUILD_DIR:=build
VENV:=$(BUILD_DIR)/virtualenv

DJANGO_SETTINGS_MODULE?=test_sqlite

test: $(VENV)/bin/django-admin
	cd tests \
	&& PYTHONPATH=..:$$PYTHONPATH \
		$(abspath $(VENV))/bin/python ./runtests.py \
			--settings=$(DJANGO_SETTINGS_MODULE)

$(VENV)/bin/django-admin: $(VENV)/bin/python
	$(VENV)/bin/pip install -e .

$(VENV)/bin/python: $(VENV)

$(VENV):
	virtualenv $@

clean:
	$(RM) -r $(BUILD_DIR)

.PHONY: clean test
