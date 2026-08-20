.PHONY: init check openlore/analyze openlore/export openlore/import openlore/preflight openlore/refresh

# Node 22.13+ is required (openlore uses node:sqlite).
OPENLORE := npx --yes openlore@2.1.8
BASE_REF ?= origin/main

init:
	pre-commit install
	$(OPENLORE) install --preset full

check:
	pre-commit run --all-files

openlore/analyze:
	$(OPENLORE) analyze --no-embed --config .openlore/config.json

openlore/export:
	$(OPENLORE) export bundle

openlore/import:
	$(OPENLORE) import .openlore/index-bundle.olbundle

openlore/preflight:
	$(OPENLORE) preflight --since $(BASE_REF)

openlore/refresh: openlore/analyze openlore/export
	@echo "Stage .openlore/index-bundle.olbundle (and config if changed)."
