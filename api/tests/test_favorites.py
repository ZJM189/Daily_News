from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest

from app.application.favorites.service import FavoritesService
from app.application.identity.dtos import UserDTO
from app.main import create_app


def actor():
    return UserDTO(
        uuid4(), "reader", None, None, "user", "active", datetime.now(UTC), datetime.now(UTC), None
    )


@pytest.mark.parametrize("name", ["", "  ", "a" * 81, "根目录", "全部收藏"])
def test_invalid_folder_names_never_reach_repository(name):
    repository = Mock()
    with pytest.raises(ValueError):
        FavoritesService(repository).save_folder(actor(), name)
    repository.save_folder.assert_not_called()


def test_folder_names_are_trimmed_and_user_scope_comes_from_actor():
    repository = Mock()
    reader = actor()
    FavoritesService(repository).save_folder(reader, "  Research  ")
    repository.save_folder.assert_called_once_with(reader.id, "Research", None)


@pytest.mark.anyio
async def test_favorites_require_authentication():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        for method, path in [
            ("GET", "/folders"),
            ("GET", "/items"),
            ("PUT", f"/items/{uuid4()}"),
            ("DELETE", f"/folders/{uuid4()}"),
        ]:
            result = await client.request(method, f"/api/v1/favorites{path}")
            assert result.status_code == 401


@pytest.fixture
def anyio_backend():
    return "asyncio"
