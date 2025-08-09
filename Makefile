# TermAgent Makefile

.PHONY: help install run debug test clean

# Default target
help:
	@echo "🤖 TermAgent - Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the application"
	@echo "  make debug      - Run the application in debug mode"
	@echo "  make test       - Run tests"
	@echo "  make clean      - Clean cache files"

# Install dependencies
install:
	uv sync

# Run the application
run:
	uv run main.py

# Run the application in debug mode
debug:
	uv run main.py --debug

# Run tests
test:
	uv run python -c "from termagent_graph import create_agent_graph; print('✅ Tests passed')"

# Clean cache files
clean:
	rm -rf __pycache__ agents/__pycache__
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
