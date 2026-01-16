import os
from dotenv import load_dotenv
from fastapi import FastAPI
from typing import Optional, Callable, Any
from fastapi.middleware.cors import CORSMiddleware
from bff.routers import workflow
from bff.observability import setup_logging, metrics_app

init_telemetry: Optional[Callable[[FastAPI], Any]] = None
try:
    # Import telemetry initializer if available; keep typed as Optional[Callable]
    from bff.telemetry import init_telemetry as _init_telemetry

    init_telemetry = _init_telemetry
except Exception:
    # Leave as None when telemetry deps are not installed
    pass

# Load .env for local development (do not commit .env with secrets)
load_dotenv()

app = FastAPI(
    title="Reconciliation AI Gate",
    description="BFF for Recon Governance & Workflow",
    version="1.0.0",
)

# Setup structured JSON logging
setup_logging()

# Configure CORS origins via `ALLOWED_ORIGINS` env var (comma-separated).
# Default is localhost for local development.
allowed = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
allow_origins = [o.strip() for o in allowed.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics endpoint at /metrics
app.mount("/metrics", metrics_app())

# Initialize tracing (optional). init_telemetry is safe-noop when deps missing.
if init_telemetry is not None:
    try:
        init_telemetry(app)
    except Exception:
        pass

# Register Routers
app.include_router(workflow.router)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "Recon-BFF"}


if __name__ == "__main__":
    import uvicorn

    # Only enable reload when DEV environment variable is truthy.
    dev_mode = os.getenv("DEV", "false").lower() in ("1", "true", "yes")
    uvicorn.run("bff.main:app", host="0.0.0.0", port=8000, reload=dev_mode)
