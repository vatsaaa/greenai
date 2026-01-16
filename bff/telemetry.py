from typing import Any
from fastapi import FastAPI


def init_telemetry(app: FastAPI) -> Any:
    # No-op telemetry initializer for staging when telemetry libs are absent.
    return None
