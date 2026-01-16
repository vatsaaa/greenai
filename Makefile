.PHONY: setup install-dev pre-commit-install lint format precommit-run

setup: install-dev pre-commit-install

install-dev:
	python -m pip install -r requirements-dev.txt

pre-commit-install:
	pre-commit install

lint:
	ruff check .

format:
	black .
	ruff format .

precommit-run:
	pre-commit run --all-files

check-lockfile:
	./scripts/check_lockfile.sh

staging-run:
	# Run the reproducible staging harness (Docker required)
	bash ./scripts/run_staging_load.sh
