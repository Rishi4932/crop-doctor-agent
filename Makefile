# Makefile for crop-doctor-agent

.PHONY: install playground run test lint

install:
	uv sync

playground:
	uv run adk web app --host 127.0.0.1 --port 18081 --reload_agents

run:
	uv run python -m app.web_server

test:
	uv run pytest

lint:
	uv run ruff check app
