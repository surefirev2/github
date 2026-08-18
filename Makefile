.PHONY: init check

# Node 22.13+ is required (openlore uses node:sqlite).
OPENLORE := npx --yes openlore@2.1.8

init:
	pre-commit install
	$(OPENLORE) install --preset full

check:
	pre-commit run --all-files
