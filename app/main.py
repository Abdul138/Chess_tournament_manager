from fastapi import FastAPI

app = FastAPI(title="Chess Tournament Manager")


@app.get("/health")
def health() -> dict[str, str]:
    """Simple check that the server is running."""
    return {"status": "ok"}

