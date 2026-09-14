from datetime import date

import httpx
import pytest

from app.interfaces.http.dependencies import get_digest_query_service
from app.main import create_app


class EmptyDigestQueryService:
    def get_published_digest(self, *, digest_date: date, version: int | None):
        return None


async def empty_digest_query_service() -> EmptyDigestQueryService:
    return EmptyDigestQueryService()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_today_digest_is_public_when_no_digest_exists() -> None:
    app = create_app()
    app.dependency_overrides[get_digest_query_service] = empty_digest_query_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/digests/today")

    assert response.status_code == 200
    assert response.json() == {"data": None}


@pytest.mark.anyio
async def test_digest_by_date_still_requires_authentication() -> None:
    app = create_app()
    app.dependency_overrides[get_digest_query_service] = empty_digest_query_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/digests/2026-09-09")

    assert response.status_code == 401


@pytest.mark.anyio
async def test_public_digest_by_date_is_available_without_authentication() -> None:
    app = create_app()
    app.dependency_overrides[get_digest_query_service] = empty_digest_query_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/digests/public/2026-09-09")

    assert response.status_code == 200
    assert response.json() == {"data": None}
