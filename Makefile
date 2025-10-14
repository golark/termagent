run:
	uv run python src/main.py

debug:
	TERMAGENT_DEBUG=1 uv run python src/main.py

test:
	uv run pytest
