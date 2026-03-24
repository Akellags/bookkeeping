# Help U - Bookkeeper Project Guide

## Build & Setup
- Initialize virtual environment: `python -m venv venv`
- Activate virtual environment: `venv\Scripts\activate`
- Install dependencies: `pip install -r requirements.txt`
- Start Backend Server: `python -m uvicorn src.main:app --reload` (Run from project root)

## Test
- Run tests: `pytest`

## Lint & Typecheck
- Lint: `pylint src`
- Typecheck: `mypy src`
