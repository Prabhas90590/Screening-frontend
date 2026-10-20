# Screening Backend

This folder contains the FastAPI backend for the equity screening application.

## Setup

From the `backend` folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

- Health check: `GET /health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
