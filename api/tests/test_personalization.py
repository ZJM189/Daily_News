from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.identity.dtos import UserDTO
from app.application.personalization.dtos import SavedSearchDTO, UserPreferenceDTO
from app.application.personalization.service import PersonalizationService


def test_saved_search_merges_supported_filters_into_preferences() -> None:
    repository = FakePersonalizationRepository()
    service = PersonalizationService(repository)
    actor = _user()

    service.create_saved_search(
        actor=actor,
        name="Agent 搜索",
        query={"keyword": "Agent", "category": "open_source", "source_type": "github"},
        apply_as_filter=True,
        apply_as_boost=True,
    )

    preference = repository.preference
    assert preference.follow_keywords == ["Agent"]
    assert preference.follow_categories == ["open_source"]
    assert preference.follow_source_types == ["github"]


def test_saved_search_ignores_invalid_category_when_merging() -> None:
    repository = FakePersonalizationRepository()
    service = PersonalizationService(repository)
    actor = _user()

    service.create_saved_search(
        actor=actor,
        name="bad",
        query={"keyword": "OpenAI", "category": "bad_category"},
        apply_as_filter=True,
        apply_as_boost=True,
    )

    assert repository.preference.follow_keywords == ["OpenAI"]
    assert repository.preference.follow_categories == []


def test_block_source_feedback_requires_source_id() -> None:
    service = PersonalizationService(FakePersonalizationRepository())

    with pytest.raises(ValueError, match="source_id is required"):
        service.record_feedback(
            actor=_user(),
            action="block_source",
            item_id=None,
            source_id=None,
        )


class FakePersonalizationRepository:
    def __init__(self) -> None:
        self.preference = UserPreferenceDTO(weights={})

    def get_preference(self, user_id: UUID) -> UserPreferenceDTO | None:
        return self.preference

    def save_preference(self, *, user_id: UUID, preference: UserPreferenceDTO) -> UserPreferenceDTO:
        self.preference = preference
        return preference

    def list_saved_searches(self, *, user_id: UUID) -> list[SavedSearchDTO]:
        return []

    def create_saved_search(
        self,
        *,
        user_id: UUID,
        name: str,
        query: dict[str, object],
        apply_as_filter: bool,
        apply_as_boost: bool,
    ) -> SavedSearchDTO:
        now = datetime.now(UTC)
        return SavedSearchDTO(
            id=uuid4(),
            name=name,
            query=query,
            enabled=True,
            apply_as_filter=apply_as_filter,
            apply_as_boost=apply_as_boost,
            created_at=now,
            updated_at=now,
        )

    def create_feedback(
        self,
        *,
        user_id: UUID,
        action: str,
        item_id: UUID | None,
        source_id: UUID | None,
    ) -> None:
        return None

    def list_feed_candidates(self, *, preference: UserPreferenceDTO, limit: int) -> list[object]:
        return []


def _user() -> UserDTO:
    now = datetime.now(UTC)
    return UserDTO(
        id=uuid4(),
        username="demo",
        email=None,
        display_name=None,
        role="user",
        status="active",
        created_at=now,
        updated_at=now,
        last_login_at=None,
    )
