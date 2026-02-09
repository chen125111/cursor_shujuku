# Gas Hydrate Phase Equilibrium Query System

This project provides a FastAPI backend and a static frontend for managing
gas mixture data and performing hydrate phase equilibrium queries.

## Features

- Public query APIs for hydrate and component-based lookups
- Query history and favorites for authenticated users
- Batch query and pressure comparison summaries
- CSV/Excel import and export, plus PDF export
- Data review, backup, and audit logging
- JWT auth, sessions, rate limiting, and caching

## Quick Start

1) Install dependencies

```
python3 -m pip install -r requirements.txt
```

2) Start the API server

```
python3 -m uvicorn backend.main:app --reload
```

3) Open the UI

- Query UI: http://127.0.0.1:8000
- Admin UI: http://127.0.0.1:8000/admin
- API docs: http://127.0.0.1:8000/docs

## Configuration

Copy `.env.example` and update values as needed:

```
cp .env.example .env
```

Environment variables are described in `.env.example`.

## Documentation

- docs/API.md
- docs/USER_GUIDE.md
- docs/DEVELOPMENT.md
- docs/CONTRIBUTING.md

## Testing

```
python3 -m pytest
```
