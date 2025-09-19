.PHONY: env clean-env deps format lint test dist-plugin clean-dist-plugin publish-plugin-pypi publish-plugin-pypi-test check-plugin-folder

PYTHON ?= 3.12

UV = UV_CACHE_DIR=.uv-cache uv
UV_RUN = $(UV) run --no-sync

MODULES = \
	plugins/mcp/mcp-server \
	plugins/mcp/mcp-client \
	examples/plugins/example-tool

MYPY_TARGETS = \
	plugins/mcp/mcp-server:hopeit_agents.mcp_server \
	plugins/mcp/mcp-client:hopeit_agents.mcp_client \
	examples/plugins/example-tool:hopeit_agents.example_tool

env:
	$(UV) venv --seed --python $(PYTHON)
	$(UV) sync --all-packages

clean-env:
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -f uv.lock

install-dev: env
	$(UV) sync --dev --all-packages
	for module in $(MODULES); do \
		$(UV) pip install -U --no-deps -e ./$$module; \
	done

format:
	$(UV_RUN) ruff format $(MODULES:%=%/src/) $(MODULES:%=%/test/)
	$(UV_RUN) ruff check $(MODULES:%=%/src/) $(MODULES:%=%/test/) --fix

lint:
	$(UV_RUN) ruff format --check $(MODULES:%=%/src/) $(MODULES:%=%/test/)
	$(UV_RUN) ruff check $(MODULES:%=%/src/) $(MODULES:%=%/test/)
	for target in $(MYPY_TARGETS); do \
		module=$${target%%:*}; \
		package=$${target##*:}; \
		PYTHONPATH=$$module/src MYPYPATH=$$module/src $(UV_RUN) mypy --namespace-packages -p $$package; \
		PYTHONPATH=$$module/src MYPYPATH=$$module/src:$$module/test $(UV_RUN) mypy --namespace-packages $$module/test; \
	done

test:
	for module in $(MODULES); do \
		PYTHONPATH=$$module/src $(UV_RUN) pytest -v $$module/test; \
	done

ci:
	$(UV) sync --all-packages
	make lint
	make test

check-plugin-folder:
	@if [ -z "$(PLUGINFOLDER)" ]; then \
		echo "PLUGINFOLDER must be provided, e.g. 'make dist-plugin PLUGINFOLDER=plugins/mcp/mcp-server'"; \
		exit 1; \
	fi
	@if [ ! -d "$(PLUGINFOLDER)" ]; then \
		echo "Plugin folder '$(PLUGINFOLDER)' not found"; \
		exit 1; \
	fi

clean-dist-plugin: check-plugin-folder
	rm -rf $(PLUGINFOLDER)/dist

dist-plugin: check-plugin-folder clean-dist-plugin
	$(UV) --project=$(PLUGINFOLDER) build

publish-plugin-pypi: check-plugin-folder
	@if [ -z "$(PYPI_API_TOKEN)" ]; then \
		echo "PYPI_API_TOKEN must be provided via environment"; \
		exit 1; \
	fi
	$(UV) publish -u __token__ -p "$(PYPI_API_TOKEN)" $(PLUGINFOLDER)/dist/*

publish-plugin-pypi-test: check-plugin-folder
	@if [ -z "$(TEST_PYPI_API_TOKEN)" ]; then \
		echo "TEST_PYPI_API_TOKEN must be provided via environment"; \
		exit 1; \
	fi
	$(UV) publish -u __token__ -p "$(TEST_PYPI_API_TOKEN)" --publish-url=https://test.pypi.org/legacy/ $(PLUGINFOLDER)/dist/*
