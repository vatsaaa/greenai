from fastapi import FastAPI
import logging


def setup_logging() -> None:
    # Minimal structured logging setup for staging/dev.
    logging.basicConfig(level=logging.INFO)


def metrics_app() -> FastAPI:
    # Minimal metrics app placeholder. In production replace with Prometheus app.
    app = FastAPI()

    @app.get("/")
    async def root():
        return {"metrics": "placeholder"}

    return app
