# Python interpreter. Default: '$(PYTHON)'
PYTHON ?= python
PIP ?= pip

# BEGIN-EVAL makefile-parser --make-help Makefile

help:
	@echo ""
	@echo "  Targets"
	@echo ""
	@echo "    install   Install this package"
	@echo "    deps      Install dependencies only"
	@echo "    deps-test Install dependencies for testing only"
	@echo "    test      Run all unit tests"
	@echo "    coverage  Run coverage tests"
	@echo ""
	@echo "  Variables"
	@echo ""
	@echo "    PYTHON  Python interpreter. Default: '$(PYTHON)'"
	@echo "    PIP     Python packager. Default: '$(PIP)'"

# END-EVAL

#
# Tests
#

.PHONY: install check test coverage deps deps-test

install:
	$(PIP) install .

deps:
	$(PIP) install -r requirements.txt

deps-test:
	$(PIP) install -r requirements-test.txt

check:
	ruff check

# Run all unit tests
test: check
	$(PYTHON) -m pytest --cov=mets_mods2tei --cov-branch --cov-report=xml:coverage.xml

# Run coverage tests
coverage:
	make test
	$(PYTHON) -m coverage report -m
	$(PYTHON) -m coverage html
