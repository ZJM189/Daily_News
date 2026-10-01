from uuid import uuid4

import httpx
import pytest

from app.application.analytics.dtos import VisitStatsDTO
from app.interfaces.http.dependencies import get_visit_analytics_service
from app.main import create_app


class FakeVisitAnalyticsService:
    def __init__(self) -> None:
        self.recorded: list[dict[str, str | None]] = []

    def record_visit(
        self,
        *,
        visitor_id: str,
        path: str,
        referrer: str | None,
        user_agent: str | None,
    ) -> VisitStatsDTO:
        self.recorded.append(
            {
                "visitor_id": visitor_id,
                "path": path,
                "referrer": referrer,
                "user_agent": user_agent,
            }
        )
        return VisitStatsDTO(
            total_visits=8,
            today_visits=3,
            unique_visitors=5,
            today_unique_visitors=2,
        )

    def get_visit_stats(self) -> VisitStatsDTO:
        return VisitStatsDTO(
            total_visits=7,
            today_visits=2,
            unique_visitors=5,
            today_unique_visitors=2,
        )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_record_visit_returns_stats_without_authentication() -> None:
    app = create_app()
    service = FakeVisitAnalyticsService()

    async def get_service() -> FakeVisitAnalyticsService:
        return service

    app.dependency_overrides[get_visit_analytics_service] = get_service
    visitor_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/analytics/visits",
            json={"visitor_id": str(visitor_id), "path": "/today"},
            headers={
                "referer": "https://example.test/",
                "user-agent": "test-agent",
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["today_visits"] == 3
    assert service.recorded == [
        {
            "visitor_id": str(visitor_id),
            "path": "/today",
            "referrer": "https://example.test/",
            "user_agent": "test-agent",
        }
    ]


@pytest.mark.anyio
async def test_visit_stats_can_be_read_without_authentication() -> None:
    app = create_app()
    service = FakeVisitAnalyticsService()

    async def get_service() -> FakeVisitAnalyticsService:
        return service

    app.dependency_overrides[get_visit_analytics_service] = get_service

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/analytics/visits")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "total_visits": 7,
        "today_visits": 2,
        "unique_visitors": 5,
        "today_unique_visitors": 2,
    }
