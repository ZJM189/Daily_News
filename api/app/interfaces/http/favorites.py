from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.application.favorites.dtos import FavoriteQuery
from app.application.favorites.service import FavoritesService
from app.application.identity.dtos import UserDTO
from app.domain.favorites.exceptions import FavoriteConflict, FavoriteNotFound
from app.infrastructure.favorites.repositories import SqlAlchemyFavoritesRepository
from app.interfaces.http.dependencies import get_current_user, get_db_session
from app.interfaces.http.library import CATEGORY_PATTERN, SOURCE_TYPE_PATTERN
from app.interfaces.http.schemas import LibraryItemResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


async def get_favorites_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> Iterator[FavoritesService]:
    try:
        yield FavoritesService(SqlAlchemyFavoritesRepository(session))
    except FavoriteNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except FavoriteConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


Actor = Annotated[UserDTO, Depends(get_current_user)]
Service = Annotated[FavoritesService, Depends(get_favorites_service)]


class FolderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)


class FavoriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    folder_id: UUID | None = None


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    item: LibraryItemResponse
    folder_id: UUID | None
    created_at: datetime


@router.get("/folders")
async def overview(actor: Actor, service: Service):
    return {"data": service.overview(actor)}


@router.post("/folders", status_code=201)
async def create_folder(payload: FolderRequest, actor: Actor, service: Service):
    return {"data": service.save_folder(actor, payload.name)}


@router.patch("/folders/{folder_id}")
async def rename_folder(folder_id: UUID, payload: FolderRequest, actor: Actor, service: Service):
    return {"data": service.save_folder(actor, payload.name, folder_id)}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: UUID, actor: Actor, service: Service):
    service.delete_folder(actor, folder_id)
    return {"data": {"ok": True}}


@router.get("/status")
async def favorite_status(
    actor: Actor,
    service: Service,
    item_ids: Annotated[list[UUID], Query(max_length=100)],
):
    return {"data": service.states(actor, item_ids)}


@router.get("/items")
async def list_favorites(
    actor: Actor,
    service: Service,
    scope: Literal["all", "root", "folder"] = "all",
    folder_id: UUID | None = None,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[str | None, Query(pattern=CATEGORY_PATTERN)] = None,
    source_type: Annotated[str | None, Query(pattern=SOURCE_TYPE_PATTERN)] = None,
    sort: Literal["saved", "published", "score"] = "saved",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    items, total = service.search(
        actor,
        FavoriteQuery(
            scope=scope,
            folder_id=folder_id,
            keyword=keyword,
            category=category,
            source_type=source_type,
            sort=sort,
        ),
        page,
        page_size,
    )
    return {
        "data": [FavoriteResponse.model_validate(item) for item in items],
        "meta": {"page": page, "page_size": page_size, "total": total},
    }


@router.put("/items/{item_id}")
async def save_favorite(item_id: UUID, payload: FavoriteRequest, actor: Actor, service: Service):
    return {"data": service.save(actor, item_id, payload.folder_id)}


@router.delete("/items/{item_id}")
async def remove_favorite(item_id: UUID, actor: Actor, service: Service):
    service.remove(actor, item_id)
    return {"data": {"ok": True}}
