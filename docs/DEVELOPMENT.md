# Development Guide

## Project Layout

- backend/ FastAPI application and database modules
- frontend/ Static UI for query and admin
- docs/ Documentation
- tests/ Pytest suite

## Local Setup

```
python3 -m pip install -r requirements.txt
python3 -m uvicorn backend.main:app --reload
```

## Tests

```
python3 -m pytest
```

## Environment Variables

See `.env.example` for supported configuration.
