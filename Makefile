run:
	uv run python src/main.py

debug:
	TERMAGENT_DEBUG=1 uv run python src/main.py

test:
	uv run pytest

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

build: clean
	uv run python -m build
	uv run twine check dist/*

upload: check
	uv run twine upload dist/*

.PHONY: run debug test clean build check upload-test upload
