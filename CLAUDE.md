# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Early-stage FastAPI backend for running chess tournaments. Only `app/main.py` (a `/health` endpoint) and the Pydantic models in `app/models/` are implemented. The routes, services, repositories, `app/config.py`, `tests/conftest.py` and most test files are empty placeholders that show where the code is meant to go.

## Commands

Uses Python 3.14 with a local `.venv` (dependencies are pinned in `requirements.txt`). No linter or formatter is configured.

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload            # run dev server
.venv/bin/pytest                                   # run all tests
.venv/bin/pytest tests/test_health.py::test_health_returns_ok   # single test
```

`pyproject.toml` sets `pythonpath = ["."]` so tests can `import app`. `app/` has no top-level `__init__.py`.

The test client dependency is `httpx2` (not `httpx`) on purpose: Starlette 1.7's `TestClient` imports `httpx2` first.

The user is learning backend development: explain changes in beginner-friendly terms, work in small steps, and don't invent requirements. Ask if a design detail is missing.

## Architecture

The layers are routes → services → repositories → models:

- `app/routes/`: FastAPI routers (`auth`, `tournaments`, `games`). These must be included in `app/main.py`.
- `app/services/`: business logic. `auth_service` (password hashing and JWT; the JWT secret is meant to come from `.env`, which is gitignored), `tournament_service` (lifecycle and registration), and `pairing` (round-robin and Swiss pairing).
- `app/repositories/`: persistence over flat JSON files in `data/` (`users.json`, `tournaments.json`, `games.json`), with shared logic in `base.py`. There is no database.
- `app/models/`: Pydantic v2 models, re-exported from `app/models/__init__.py`.

Domain rules encoded in the models:
- `User.role` is `player` or `organizer` (no admin). `rating` defaults to 1000 and must be ≥ 0. Rating groups (e.g. 500–800) are planned for later.
- `Tournament.format` is `round_robin` or `swiss`. `TournamentStatus` moves through `draft → registration_open → in_progress → finished`, and it can also be `cancelled`. Players who withdraw are tracked in `withdrawn_ids`, separately from `player_ids`.
- In `Game`, a bye has `black_id=None` and `result="bye"`. A validator enforces that the two always go together, and that `white_id != black_id`. `result=None` means the game hasn't been played yet. Rating snapshot fields will be added once rating calculation exists.
- `Tournament.max_players` ≥ 2. `num_rounds` is required for Swiss and rejected for round robin. Use the `total_rounds` property for the round count: round robin derives it from the player count (n−1 if even, n if odd because of byes, 0 if fewer than 2 players). `Game.round` ≥ 1.
