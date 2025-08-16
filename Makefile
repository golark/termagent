# TermAgent Makefile

.PHONY: help install run debug test clean oneshot voice-setup voice-demo

# Default target
help:
	@echo "🤖 TermAgent - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run the application"
	@echo "  make debug        - Run the application in debug mode"
	@echo "  make oneshot      - Run a single command and exit (usage: make oneshot CMD='git status')"
	@echo "  make test         - Run tests"
	@echo "  make clean        - Clean cache files"
	@echo "  make voice-setup  - Set up voice input (download Vosk model)"
	@echo "  make voice-demo   - Run voice input demo"
	@echo "  make voice-test   - Test voice input functionality"

# Install dependencies
install:
	uv sync

# Run the application
run:
	uv run python -m termagent.main

# Run the application in debug mode
debug:
	uv run python -m termagent.main --debug 

# Run a single command and exit
oneshot:
	@if [ -z "$(CMD)" ]; then \
		echo "❌ Error: Please specify a command with CMD='your command'"; \
		echo "Example: make oneshot CMD='git status'"; \
		exit 1; \
	fi
	uv run python -m termagent.main --oneshot "$(CMD)"

# Run tests
test:
	uv run python -c "from termagent.termagent_graph import create_agent_graph; print('✅ Tests passed')"

# Clean cache files
clean:
	rm -rf __pycache__ agents/__pycache__
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Set up voice input
voice-setup:
	@echo "🎤 Setting up voice input..."
	python scripts/setup_voice.py

# Run voice input demo
voice-demo:
	@echo "🎤 Running voice input demo..."
	python scripts/voice_demo.py

# Test voice input
voice-test:
	@echo "🎤 Testing voice input..."
	python scripts/test_voice.py
