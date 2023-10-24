.PHONY: lint test

lint:
	@echo "Run Lint..."
	@flake8 app/

test:
	@echo "Run Test..."
	@python -m pytest -p no:warnings -rEfp tests/

all: lint test
