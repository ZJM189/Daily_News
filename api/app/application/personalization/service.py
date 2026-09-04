from typing import Any
from uuid import UUID

from app.application.identity.dtos import UserDTO
from app.application.personalization.dtos import FollowingItemDTO, SavedSearchDTO, UserPreferenceDTO
from app.application.personalization.repositories import PersonalizationRepository

DEFAULT_WEIGHTS = {
    "keyword": 18.0,
    "category": 8.0,
    "source_type": 6.0,
}
ALLOWED_CATEGORIES = {
    "model_company",
    "open_source",
    "research_paper",
    "product_launch",
    "community",
    "industry_funding",
    "other",
}
ALLOWED_SOURCE_TYPES = {"rss", "hacker_news", "github", "arxiv", "product_hunt", "hugging_face"}
ALLOWED_FEEDBACK_ACTIONS = {"more_like", "less_like", "block_source"}


class PersonalizationService:
    def __init__(self, repository: PersonalizationRepository) -> None:
        self._repository = repository

    def get_preference(self, *, actor: UserDTO) -> UserPreferenceDTO:
        return self._repository.get_preference(actor.id) or UserPreferenceDTO(weights=DEFAULT_WEIGHTS)

    def save_preference(self, *, actor: UserDTO, preference: UserPreferenceDTO) -> UserPreferenceDTO:
        cleaned = UserPreferenceDTO(
            follow_keywords=_clean_text_list(preference.follow_keywords),
            exclude_keywords=_clean_text_list(preference.exclude_keywords),
            follow_categories=_clean_text_list(preference.follow_categories),
            follow_source_types=_clean_text_list(preference.follow_source_types),
            disabled_source_types=_clean_text_list(preference.disabled_source_types),
            blocked_source_ids=_clean_text_list(preference.blocked_source_ids),
            blocked_domains=_clean_text_list(preference.blocked_domains),
            weights={**DEFAULT_WEIGHTS, **preference.weights},
        )
        return self._repository.save_preference(user_id=actor.id, preference=cleaned)

    def list_saved_searches(self, *, actor: UserDTO) -> list[SavedSearchDTO]:
        return self._repository.list_saved_searches(user_id=actor.id)

    def create_saved_search(
        self,
        *,
        actor: UserDTO,
        name: str,
        query: dict[str, Any],
        apply_as_filter: bool,
        apply_as_boost: bool,
    ) -> SavedSearchDTO:
        cleaned_query = _clean_query(query)
        saved_search = self._repository.create_saved_search(
            user_id=actor.id,
            name=name.strip() or _default_search_name(cleaned_query),
            query=cleaned_query,
            apply_as_filter=apply_as_filter,
            apply_as_boost=apply_as_boost,
        )
        if apply_as_boost:
            self._merge_search_into_preference(actor=actor, query=cleaned_query)
        return saved_search

    def record_feedback(
        self,
        *,
        actor: UserDTO,
        action: str,
        item_id: UUID | None,
        source_id: UUID | None,
    ) -> None:
        if action not in ALLOWED_FEEDBACK_ACTIONS:
            raise ValueError("unsupported feedback action")
        if action in {"more_like", "less_like"} and item_id is None:
            raise ValueError("item_id is required for item feedback")
        if action == "block_source" and source_id is None:
            raise ValueError("source_id is required for source feedback")

        self._repository.create_feedback(
            user_id=actor.id,
            action=action,
            item_id=item_id,
            source_id=source_id,
        )
        if action == "block_source" and source_id is not None:
            preference = self.get_preference(actor=actor)
            self.save_preference(
                actor=actor,
                preference=UserPreferenceDTO(
                    follow_keywords=preference.follow_keywords,
                    exclude_keywords=preference.exclude_keywords,
                    follow_categories=preference.follow_categories,
                    follow_source_types=preference.follow_source_types,
                    disabled_source_types=preference.disabled_source_types,
                    blocked_source_ids=_merge_values(preference.blocked_source_ids, [str(source_id)]),
                    blocked_domains=preference.blocked_domains,
                    weights=preference.weights,
                ),
            )

    def list_following_items(
        self,
        *,
        actor: UserDTO,
        page: int,
        page_size: int,
    ) -> tuple[list[FollowingItemDTO], int]:
        preference = self.get_preference(actor=actor)
        if not _has_active_rules(preference):
            return [], 0

        candidates = self._repository.list_feed_candidates(
            preference=preference,
            limit=max(page * page_size * 5, 200),
        )
        ranked = sorted(
            (_score_item(item, preference) for item in candidates),
            key=lambda item: (item.personalized_score, item.item.published_at or item.item.collected_at),
            reverse=True,
        )
        offset = (page - 1) * page_size
        return ranked[offset : offset + page_size], len(ranked)

    def _merge_search_into_preference(self, *, actor: UserDTO, query: dict[str, Any]) -> None:
        preference = self.get_preference(actor=actor)
        next_preference = UserPreferenceDTO(
            follow_keywords=_merge_values(preference.follow_keywords, [_string_value(query.get("keyword"))]),
            exclude_keywords=preference.exclude_keywords,
            follow_categories=_merge_values(
                preference.follow_categories,
                [_string_value(query.get("category"))],
            ),
            follow_source_types=_merge_values(
                preference.follow_source_types,
                [_string_value(query.get("source_type"))],
            ),
            disabled_source_types=preference.disabled_source_types,
            blocked_source_ids=preference.blocked_source_ids,
            blocked_domains=preference.blocked_domains,
            weights=preference.weights,
        )
        self.save_preference(actor=actor, preference=next_preference)


def _clean_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        text = value.strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def _merge_values(existing: list[str], incoming: list[str | None]) -> list[str]:
    return _clean_text_list([*existing, *(value for value in incoming if value)])


def _string_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_query(query: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "keyword",
        "category",
        "source_type",
        "source_id",
        "status",
        "min_score",
        "has_summary",
        "sort",
    }
    cleaned: dict[str, Any] = {}
    for key, value in query.items():
        if key not in allowed_keys or value is None or value == "":
            continue
        if key == "category" and str(value) not in ALLOWED_CATEGORIES:
            continue
        if key == "source_type" and str(value) not in ALLOWED_SOURCE_TYPES:
            continue
        cleaned[key] = str(value).strip() if isinstance(value, str) else value
    return cleaned


def _default_search_name(query: dict[str, Any]) -> str:
    keyword = _string_value(query.get("keyword"))
    if keyword:
        return f"{keyword} 相关内容"
    category = _string_value(query.get("category"))
    if category:
        return f"{category} 分类关注"
    return "保存的搜索"


def _has_active_rules(preference: UserPreferenceDTO) -> bool:
    return bool(
        preference.follow_keywords
        or preference.follow_categories
        or preference.follow_source_types
        or preference.exclude_keywords
        or preference.disabled_source_types
        or preference.blocked_source_ids
        or preference.blocked_domains
    )


def _score_item(item, preference: UserPreferenceDTO) -> FollowingItemDTO:
    score = float(item.score)
    reasons: list[str] = []
    searchable_text = " ".join(
        [
            item.title,
            item.summary_zh or "",
            item.summary_original or "",
            item.content_snippet or "",
            " ".join(item.tags),
        ]
    ).lower()

    matched_keywords = [
        keyword for keyword in preference.follow_keywords if keyword.lower() in searchable_text
    ]
    if matched_keywords:
        score += min(len(matched_keywords), 2) * preference.weights.get("keyword", 18.0)
        reasons.append(f"匹配关注关键词：{'、'.join(matched_keywords[:3])}")

    if item.category in preference.follow_categories:
        score += preference.weights.get("category", 8.0)
        reasons.append("匹配关注分类")

    if item.source.type in preference.follow_source_types:
        score += preference.weights.get("source_type", 6.0)
        reasons.append(f"来自关注来源类型：{item.source.type}")

    if not reasons:
        reasons.append("符合当前硬过滤规则")

    return FollowingItemDTO(item=item, personalized_score=round(score, 2), match_reasons=reasons)
