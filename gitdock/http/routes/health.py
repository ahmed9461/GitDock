"""Health/readiness HTTP routes."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gitdock.core.constants import APP_NAME, HEALTH_PATH, READINESS_PATH
from gitdock.db.session import database_ping

router = APIRouter()


@router.get(HEALTH_PATH)
async def health() -> dict[str, str]:
    return {"status": "ok", "service": APP_NAME}


@router.get(READINESS_PATH)
async def readiness(request: Request) -> JSONResponse:
    engine = request.app.state.db_engine
    db_ready = await database_ping(engine)
    payload = {
        "status": "ready" if db_ready else "not_ready",
        "checks": {"database": "ok" if db_ready else "failed"},
    }
    return JSONResponse(status_code=200 if db_ready else 503, content=payload)
