.PHONY: help install seed train test test-backend test-frontend run dev build clean

PYTHON := backend/.venv/bin/python
ifeq ($(OS),Windows_NT)
    PYTHON := backend\.venv\Scripts\python.exe
endif

help:
	@echo "FAULTTRACE AI - Development Commands"
	@echo "------------------------------------"
	@echo "make install       Install backend and frontend dependencies"
	@echo "make seed          Initialize database and seed synthetic network"
	@echo "make train         Generate scenarios, train XGBoost, and calibrate"
	@echo "make test          Run full backend (pytest) and frontend (vitest) tests"
	@echo "make test-backend  Run backend pytest suite"
	@echo "make test-frontend Run frontend vitest suite"
	@echo "make dev           Start backend and frontend in development mode"
	@echo "make build         Build frontend production bundle"

install:
	python -m venv backend/.venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	cd frontend && npm install

seed:
	$(PYTHON) -m backend.app.database.seed

train:
	$(PYTHON) -m backend.app.ml_engine.trainer

test: test-backend test-frontend

test-backend:
	$(PYTHON) -m pytest backend/tests -v

test-frontend:
	cd frontend && npm test -- --run

build:
	cd frontend && npm run build

dev:
	@echo "Starting backend and frontend..."
	$(PYTHON) -m uvicorn backend.app.main:app --reload --port 8000
