from fastapi import FastAPI

app = FastAPI(
    title="Screening Frontend API",
    description="Backend API placeholder for the equity screening application.",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
