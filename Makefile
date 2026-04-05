PYTHON ?= python

.PHONY: dev test lint seed perf-smoke migrate

dev:
	$(PYTHON) -m uvicorn app.main:app --reload

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check .

seed:
	$(PYTHON) scripts/seed.py

perf-smoke:
	$(PYTHON) scripts/perf_smoke.py --rows 100000 --target-ms 150

migrate:
	$(PYTHON) -m alembic upgrade head
