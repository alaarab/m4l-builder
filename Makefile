# m4l-builder — local dev gate. `make check` mirrors CI exactly (ruff + mypy +
# pytest), so a green `make check` means a green GitHub Actions run. Run it
# before every push; it is also wired as a pre-push hook (see .githooks/).
.PHONY: check lint typecheck test fix hooks help

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}'

check: lint typecheck test  ## Full CI-parity gate — run before pushing

lint:            ## Ruff (identical to CI's lint step)
	uv run ruff check src tests examples

typecheck:       ## Mypy (identical to CI's type-check step)
	uv run mypy

test:            ## Pytest
	uv run pytest -q

fix:             ## Auto-fix what ruff can (imports, simple lint)
	uv run ruff check --fix src tests examples

hooks:           ## Enable the repo's pre-push hook in this clone
	git config core.hooksPath .githooks
	@echo "pre-push hook enabled (runs 'make check')."
