# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early-stage FastAPI backend for running chess tournaments. Only `app/main.py` (a `/health` endpoint) and the Pydantic models in `app/models/` are implemented. The routes, services, repositories, `app/config.py`, `tests/conftest.py` and most test files are empty placeholders that show where the code is meant to go.

## Commands

Uses Python 3.14 with a local `.venv` (dependencies are pinned in `requirements.txt`). No linter or formatter is configured.

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload            # run dev server
.venv/bin/python -m pytest                         # run all tests
.venv/bin/python -m pytest tests/test_health.py::test_health_returns_ok   # single test
```

Run pytest as `python -m pytest` from the repo root. Plain `pytest` fails with `ModuleNotFoundError: No module named 'app'` because there is no `pyproject.toml`/`pytest.ini` setting `pythonpath`, and `app/` has no top-level `__init__.py`.

## Architecture

The layers are routes → services → repositories → models:

- `app/routes/`: FastAPI routers (`auth`, `tournaments`, `games`). These must be included in `app/main.py`.
- `app/services/`: business logic. `auth_service` (password hashing and JWT; the JWT secret is meant to come from `.env`, which is gitignored), `tournament_service` (lifecycle and registration), and `pairing` (round-robin and Swiss pairing).
- `app/repositories/`: persistence over flat JSON files in `data/` (`users.json`, `tournaments.json`, `games.json`), with shared logic in `base.py`. There is no database.
- `app/models/`: Pydantic v2 models, re-exported from `app/models/__init__.py`.

Domain rules encoded in the models:
- `User.role` is one of `player`, `organizer` or `admin`. The default rating is 1200.
- `Tournament.format` is `round_robin` or `swiss`. `TournamentStatus` moves through `draft → registration_open → in_progress → finished`, and it can also be `cancelled`. Players who withdraw are tracked in `withdrawn_ids`, separately from `player_ids`.
- In `Game`, `black_id is None` means a bye (`result="bye"`). Ratings are copied into `white_rating_at_start`/`black_rating_at_start` when the game is created, so later rating changes don't alter past games.
