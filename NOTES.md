# Learning Notes

## Virtual environments

- A virtual environment (`.venv/`) is a private copy of Python for this project. Packages installed into it don't affect other projects.
- Activate it: `source .venv/bin/activate` (fish: `source .venv/bin/activate.fish`). Your prompt usually shows `(.venv)`.
- `.venv/` is never committed to Git. It's large and can be rebuilt from `requirements.txt`.

## Dependencies

- A dependency is a package your code needs (FastAPI, pytest, ...).
- `pip install <package>` installs it into the active venv.
- `pip freeze > requirements.txt` records exact versions. `pip install -r requirements.txt` reinstalls them on any machine.
- `httpx2` is the HTTP client that FastAPI's `TestClient` uses to send fake requests in tests.

## FastAPI routes

```python
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
```

- `app` is the application. Uvicorn runs it: `uvicorn app.main:app --reload` means "in the file `app/main.py`, run the object named `app`". `--reload` restarts the server when you save a file.
- `@app.get("/health")` is a **route**: when a GET request arrives for `/health`, call this function.
- The function returns a dict, and FastAPI turns it into JSON: `{"status": "ok"}`.
- HTTP methods: GET = read, POST = create, PUT/PATCH = update, DELETE = remove.
- http://127.0.0.1:8000/docs shows every route and lets you try them.

## HTTP status codes

Every response includes a number that says how the request went:

| Code | Meaning | Example |
|---|---|---|
| 200 | OK | `/health` worked |
| 201 | Created | a new tournament was made |
| 400 / 422 | Bad request / invalid data | the body is missing a field (FastAPI sends 422 automatically) |
| 401 / 403 | Not logged in / not allowed | a player tries an organizer action |
| 404 | Not found | the URL or ID doesn't exist |
| 500 | Server error | a bug in our code |

## pytest

- pytest finds files named `test_*.py` and runs the functions named `test_*` inside them.
- A test is "arrange, act, assert": set things up, do the action, check the result with `assert`.
- `TestClient(app)` sends requests to the app **without** starting a server, which makes it fast and reliable.

```python
client = TestClient(app)

def test_health_returns_ok():
    response = client.get("/health")             # act
    assert response.status_code == 200           # assert
    assert response.json() == {"status": "ok"}
```

- Run all tests: `pytest`. Run one: `pytest tests/test_health.py::test_health_returns_ok`. Add `-v` to see each test's name.
- `pyproject.toml` sets `pythonpath = ["."]` so tests can `import app`.

## Project files

| Path | Purpose |
|---|---|
| `app/main.py` | Creates the FastAPI app; the program starts here |
| `app/models/` | Pydantic models: the shapes of User, Tournament, Game |
| `app/repositories/` | Save and load models (JSON files in `data/`) |
| `app/services/` | Business rules (registration, pairing, ...) |
| `app/routes/` | HTTP endpoints, which call services |
| `app/config.py` | Settings (e.g. file paths, secret key) |
| `tests/` | pytest tests; `conftest.py` holds shared fixtures |
| `data/` | JSON files used as the database |
| `requirements.txt` | Pinned dependencies |
| `pyproject.toml` | Tool settings (pytest) |
| `.gitignore` | Files Git should not track (`.venv/`, caches, `.env`) |
