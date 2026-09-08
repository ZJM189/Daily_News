from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.application.content_library.chat import ContentLibraryChatService
from app.application.identity.dtos import UserDTO
from app.interfaces.http.dependencies import get_content_library_chat_service, get_current_user
from app.interfaces.http.schemas import (
    CreateLibraryChatThreadRequest,
    LibraryChatMessageRequest,
    LibraryChatMessageResponse,
    LibraryChatThreadResponse,
)

router = APIRouter(prefix="/library/chat", tags=["library-chat"])


@router.get("/threads")
async def list_library_chat_threads(
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryChatService, Depends(get_content_library_chat_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    threads = service.list_threads(actor=actor, limit=limit)
    return {"data": [LibraryChatThreadResponse.model_validate(thread) for thread in threads]}


@router.post("/threads")
async def create_library_chat_thread(
    request: CreateLibraryChatThreadRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryChatService, Depends(get_content_library_chat_service)],
) -> dict[str, object]:
    thread = service.create_thread(actor=actor, title=request.title)
    return {"data": LibraryChatThreadResponse.model_validate(thread)}


@router.get("/threads/{thread_id}/messages")
async def list_library_chat_messages(
    thread_id: UUID,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryChatService, Depends(get_content_library_chat_service)],
) -> dict[str, object]:
    try:
        messages = service.list_messages(actor=actor, thread_id=thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {"data": [LibraryChatMessageResponse.model_validate(message) for message in messages]}


@router.post("/threads/{thread_id}/messages/stream")
async def stream_library_chat_message(
    thread_id: UUID,
    request: LibraryChatMessageRequest,
    actor: Annotated[UserDTO, Depends(get_current_user)],
    service: Annotated[ContentLibraryChatService, Depends(get_content_library_chat_service)],
) -> StreamingResponse:
    if service.get_thread(actor=actor, thread_id=thread_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="chat thread not found")

    return StreamingResponse(
        service.stream_message(actor=actor, thread_id=thread_id, content=request.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )
