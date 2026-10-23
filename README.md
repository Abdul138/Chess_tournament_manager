# Chess Tournament Manager

A backend API for running chess tournaments (round-robin and Swiss), built with FastAPI, Pydantic and pytest using the Repository Pattern. Data is stored in JSON files in `data/`.

This is a learning project and is still in progress.

## Clone

```sh
git clone https://github.com/Abdul138/Chess_tournament_manager.git
cd Chess_tournament_manager
```

## Setup

Requires Python 3.14.

Linux / macOS:

```sh
python -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell says running scripts is disabled, allow it for your user once with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again.

Once the virtual environment is active, the commands below are the same on every system.

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
