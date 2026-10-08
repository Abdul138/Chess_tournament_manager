# Chess Tournament Manager

A backend API for running chess tournaments (round-robin and Swiss), built with FastAPI, Pydantic and pytest using the Repository Pattern. Data is stored in JSON files in `data/`.

This is a learning project and is still in progress.

## Setup

Requires Python 3.14.

```sh
python -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
```

## Run the application

```sh
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/health, or http://127.0.0.1:8000/docs for the interactive API docs.

## Run the tests

```sh
pytest                                              # all tests
pytest tests/test_health.py                         # one file
pytest tests/test_health.py::test_health_returns_ok # one test
```
