from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, object]:
    return {"data": {"status": "ok"}}


@router.get("/readyz")
async def readyz() -> dict[str, object]:
    return {"data": {"status": "ready"}}
