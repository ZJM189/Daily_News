"""Run against a migrated, isolated database via FAVORITES_TEST_DATABASE_URL."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import Header
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.identity.dtos import UserDTO
from app.infrastructure.models import Favorite, FavoriteFolder, Item, Source, User
from app.interfaces.http.dependencies import get_current_user, get_db_session
from app.main import create_app

pytestmark = pytest.mark.skipif(
    not os.getenv("FAVORITES_TEST_DATABASE_URL"), reason="isolated PostgreSQL URL required"
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def database():
    engine = create_engine(os.environ["FAVORITES_TEST_DATABASE_URL"])
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(connection)
    readers = [
        User(id=uuid4(), username=f"test-{uuid4()}", password_hash="unused", role=role)
        for role in ["user", "admin"]
    ]
    source = Source(id=uuid4(), type="rss", name="Favorites test source")
    session.add_all([*readers, source])
    session.flush()
    items = [
        Item(
            id=uuid4(),
            source_id=source.id,
            title=f"Article {i} 100%",
            normalized_title=f"article {i}",
            title_hash=str(uuid4()),
            url=f"https://example.com/{i}",
            summary_zh=f"Summary {i}",
            score=i,
            published_at=datetime.now(UTC) - timedelta(days=i),
        )
        for i in range(12)
    ]
    session.add_all(items)
    session.flush()
    app = create_app()

    async def current_user(x_test_user: str = Header(default="0")):
        user = readers[int(x_test_user)]
        return UserDTO(
            user.id,
            user.username,
            None,
            None,
            user.role,
            "active",
            user.created_at,
            user.updated_at,
            None,
        )

    async def db_session():
        with session.begin_nested():
            yield session

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_db_session] = db_session
    yield app, session, readers, items
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
async def client(database):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=database[0]), base_url="http://test/api/v1/favorites/"
    ) as client:
        yield client


@pytest.mark.anyio
async def test_root_save_idempotence_and_removal_preserve_content(client, database):
    item = database[3][0]
    first = (await client.put(f"items/{item.id}", json={})).json()["data"]
    second = (await client.put(f"items/{item.id}", json={})).json()["data"]
    assert first == second and first["folder_id"] is None
    overview = (await client.get("folders")).json()["data"]
    assert overview["total"] == overview["root_count"] == 1
    assert (await client.get("items", params={"scope": "root"})).json()["meta"]["total"] == 1
    assert (await client.delete(f"items/{item.id}")).status_code == 200
    assert (await client.delete(f"items/{item.id}")).status_code == 200
    assert database[1].get(Item, item.id) is not None
    assert (await client.get("items")).json()["meta"]["total"] == 0


@pytest.mark.anyio
async def test_folder_crud_move_and_delete_preserve_favorites(client, database):
    item = database[3][0]
    folder = (await client.post("folders", json={"name": " Papers "})).json()["data"]
    assert folder["name"] == "Papers"
    assert (await client.post("folders", json={"name": "Papers"})).status_code == 409
    saved = (await client.put(f"items/{item.id}", json={"folder_id": folder["id"]})).json()["data"]
    renamed = await client.patch(f"folders/{folder['id']}", json={"name": "Research"})
    assert renamed.json()["data"]["count"] == 1
    assert (
        await client.get("items", params={"scope": "folder", "folder_id": folder["id"]})
    ).json()["meta"]["total"] == 1
    assert (await client.put(f"items/{item.id}", json={})).json()["data"]["created_at"] == saved[
        "created_at"
    ]
    await client.put(f"items/{item.id}", json={"folder_id": folder["id"]})
    assert (await client.delete(f"folders/{folder['id']}")).status_code == 200
    overview = (await client.get("folders")).json()["data"]
    assert overview["folders"] == [] and overview["root_count"] == 1
    assert (await client.get("status", params={"item_ids": str(item.id)})).json()["data"][0][
        "folder_id"
    ] is None


@pytest.mark.anyio
async def test_admin_cannot_access_another_users_favorites_or_folders(client, database):
    item = database[3][0]
    folder = (await client.post("folders", json={"name": "Private"})).json()["data"]
    await client.put(f"items/{item.id}", json={"folder_id": folder["id"]})
    client.headers["x-test-user"] = "1"
    assert (await client.get("folders")).json()["data"]["total"] == 0
    assert (await client.get("items")).json()["data"] == []
    assert (await client.get("status", params={"item_ids": str(item.id)})).json()["data"] == []
    assert (
        await client.put(f"items/{item.id}", json={"folder_id": folder["id"]})
    ).status_code == 404
    assert (
        await client.patch(f"folders/{folder['id']}", json={"name": "Stolen"})
    ).status_code == 404
    assert (await client.delete(f"folders/{folder['id']}")).status_code == 404
    assert (
        await client.get("items", params={"scope": "folder", "folder_id": folder["id"]})
    ).status_code == 404
    await client.delete(f"items/{item.id}")
    assert (await client.post("folders", json={"name": "Private"})).status_code == 201
    client.headers["x-test-user"] = "0"
    assert (await client.get("folders")).json()["data"]["total"] == 1


@pytest.mark.anyio
async def test_search_sort_pagination_and_batch_status(client, database):
    for item in database[3]:
        assert (await client.put(f"items/{item.id}", json={})).status_code == 200
    result = (
        await client.get("items", params={"page": 2, "page_size": 10, "sort": "score"})
    ).json()
    assert result["meta"]["total"] == 12 and len(result["data"]) == 2
    assert result["data"][0]["item"]["score"] == 1
    result = (await client.get("items", params={"sort": "published", "keyword": "100%"})).json()
    assert result["data"][0]["item"]["id"] == str(database[3][0].id)
    assert (await client.get("items", params={"keyword": "_"})).json()["meta"]["total"] == 0
    assert (await client.get("items", params={"category": "research_paper"})).json()["meta"][
        "total"
    ] == 0
    assert (await client.get("items", params={"source_type": "github"})).json()["meta"][
        "total"
    ] == 0
    result = await client.get("status", params=[("item_ids", str(item.id)) for item in database[3]])
    assert len(result.json()["data"]) == 12


@pytest.mark.anyio
async def test_request_validation_and_missing_targets(client):
    assert (await client.post("folders", json={"name": " "})).status_code == 422
    assert (await client.post("folders", json={"name": "根目录"})).status_code == 422
    assert (
        await client.post("folders", json={"name": "Test", "user_id": str(uuid4())})
    ).status_code == 422
    assert (await client.get("items", params={"scope": "folder"})).status_code == 422
    assert (await client.get("items", params={"category": "invalid"})).status_code == 422
    assert (await client.get("items", params={"page_size": 101})).status_code == 422
    assert (
        await client.get("status", params=[("item_ids", str(uuid4())) for _ in range(101)])
    ).status_code == 422
    assert (await client.put(f"items/{uuid4()}", json={})).status_code == 404
    assert (await client.delete(f"folders/{uuid4()}")).status_code == 404


def test_database_enforces_unique_favorites_and_owned_folders(database):
    _, session, users, items = database
    folder = FavoriteFolder(user_id=users[0].id, name="Private")
    session.add(folder)
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Favorite(user_id=users[1].id, item_id=items[0].id, folder_id=folder.id))
        session.flush()
    session.add(Favorite(user_id=users[0].id, item_id=items[0].id, folder_id=folder.id))
    session.flush()
    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(Favorite(user_id=users[0].id, item_id=items[0].id))
        session.flush()
    assert (
        session.scalar(select(Favorite.item_id).where(Favorite.user_id == users[0].id))
        == items[0].id
    )
    session.execute(text("DELETE FROM users WHERE id = :id"), {"id": users[0].id})
    assert session.scalar(select(Favorite.id).where(Favorite.user_id == users[0].id)) is None
