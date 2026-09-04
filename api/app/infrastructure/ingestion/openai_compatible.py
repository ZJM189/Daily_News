import hashlib
import json
import time
from typing import Any
from uuid import UUID

import httpx

from app.application.ingestion.dtos import (
    ItemForSummarizationDTO,
    ItemForTopicAggregationDTO,
    ItemSummaryDTO,
    LLMRuntimeProviderDTO,
    TopicAggregationGroupDTO,
)
from app.application.ingestion.summarization import SummarySchemaError, validate_item_summary


class OpenAICompatibleSummarizationClient:
    def summarize_item(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        item: ItemForSummarizationDTO,
    ) -> ItemSummaryDTO:
        started_at = time.perf_counter()
        payload = _build_chat_completion_payload(provider=provider, item=item)
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        with httpx.Client(timeout=provider.timeout_seconds) as client:
            response = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()

        content = _extract_message_content(response_payload)
        summary_payload = _parse_summary_json(content)
        summary = validate_item_summary(summary_payload)
        usage = response_payload.get("usage")
        input_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
        output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
        return ItemSummaryDTO(
            summary_zh=summary.summary_zh,
            importance_zh=summary.importance_zh,
            category=summary.category,
            tags=summary.tags,
            confidence=summary.confidence,
            input_tokens=input_tokens if isinstance(input_tokens, int) else None,
            output_tokens=output_tokens if isinstance(output_tokens, int) else None,
            latency_ms=round((time.perf_counter() - started_at) * 1000),
        )


class OpenAICompatibleTopicAggregationClient:
    def aggregate_topics(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        items: list[ItemForTopicAggregationDTO],
    ) -> list[TopicAggregationGroupDTO]:
        if not items:
            return []

        payload = _build_topic_aggregation_payload(provider=provider, items=items)
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        with httpx.Client(timeout=provider.timeout_seconds) as client:
            response = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()

        content = _extract_message_content(response_payload)
        aggregation_payload = _parse_summary_json(content)
        return parse_topic_aggregation_payload(aggregation_payload, items=items)

    def consolidate_topic_groups(
        self,
        *,
        provider: LLMRuntimeProviderDTO,
        groups: list[TopicAggregationGroupDTO],
    ) -> list[TopicAggregationGroupDTO]:
        if not groups:
            return []

        payload = _build_topic_consolidation_payload(provider=provider, groups=groups)
        headers = {"Content-Type": "application/json"}
        if provider.api_key:
            headers["Authorization"] = f"Bearer {provider.api_key}"

        with httpx.Client(timeout=provider.timeout_seconds) as client:
            response = client.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            response_payload = response.json()

        content = _extract_message_content(response_payload)
        consolidation_payload = _parse_summary_json(content)
        return parse_topic_consolidation_payload(consolidation_payload, groups=groups)


def _build_chat_completion_payload(
    *,
    provider: LLMRuntimeProviderDTO,
    item: ItemForSummarizationDTO,
) -> dict[str, Any]:
    source_text = "\n".join(
        part
        for part in [
            f"标题：{item.title}",
            f"链接：{item.url}",
            f"原文摘要：{item.summary_original or ''}",
            f"内容片段：{item.content_snippet or ''}",
        ]
        if part.strip()
    )
    return {
        "model": provider.model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 AI 热点信息分析助手。请用简体中文输出严格 JSON，"
                    "字段为 summary_zh、importance_zh、tags、confidence。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于以下信息生成中文摘要。tags 最多 12 个。\n\n"
                    f"{source_text}"
                ),
            },
        ],
    }


def _build_topic_aggregation_payload(
    *,
    provider: LLMRuntimeProviderDTO,
    items: list[ItemForTopicAggregationDTO],
) -> dict[str, Any]:
    item_payload = [
        {
            "id": str(item.id),
            "title": item.title[:180],
            "url": item.url[:300],
            "score": float(item.score),
            "tags": item.tags[:8],
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "summary_zh": _clip(item.summary_zh, 240),
            "importance_zh": _clip(item.importance_zh, 220),
            "summary_original": _clip(item.summary_original, 180),
            "content_snippet": _clip(item.content_snippet, 220),
        }
        for item in items
    ]
    return {
        "model": provider.model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 AI 信息聚合编辑。请把输入条目按“同一事件、同一项目、"
                    "同一模型发布、同一论文主题或同一行业事件”合并为专题。"
                    "不要因为都属于 AI 或同一公司就合并。输出严格 JSON。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于 items 生成专题聚合结果。只能使用输入中的 item id，不能编造 id。"
                    "返回 JSON 格式："
                    "{\"topics\":[{\"title_zh\":\"专题标题\","
                    "\"summary_zh\":\"专题中文摘要\","
                    "\"importance_zh\":\"重要性说明\","
                    "\"tags\":[\"标签\"],\"confidence\":0.0,"
                    "\"item_ids\":[\"item id\"]}]}"
                    "。不能合并的条目也要作为单条专题返回。\n\n"
                    f"items={json.dumps(item_payload, ensure_ascii=False)}"
                ),
            },
        ],
    }


def _build_topic_consolidation_payload(
    *,
    provider: LLMRuntimeProviderDTO,
    groups: list[TopicAggregationGroupDTO],
) -> dict[str, Any]:
    group_payload = [
        {
            "group_id": f"g{index}",
            "title": group.title[:180],
            "score": float(group.score),
            "source_count": group.source_count,
            "item_count": len(group.item_ids),
            "item_ids": [str(item_id) for item_id in group.item_ids[:20]],
            "tags": group.tags[:8],
            "summary_zh": _clip(group.summary_zh, 240),
            "importance_zh": _clip(group.importance_zh, 220),
        }
        for index, group in enumerate(groups, start=1)
    ]
    return {
        "model": provider.model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 AI 信息聚合编辑。请合并输入中跨批次重复的专题。"
                    "只有明确属于同一事件、同一项目、同一模型发布、同一论文主题"
                    "或同一行业事件时才合并。输出严格 JSON。"
                ),
            },
            {
                "role": "user",
                "content": (
                    "请基于 groups 生成最终专题。只能使用输入中的 group_id，不能编造。"
                    "返回 JSON 格式："
                    "{\"topics\":[{\"title_zh\":\"专题标题\","
                    "\"summary_zh\":\"专题中文摘要\","
                    "\"importance_zh\":\"重要性说明\","
                    "\"tags\":[\"标签\"],\"confidence\":0.0,"
                    "\"group_ids\":[\"g1\"]}]}"
                    "。不能合并的 group 也要作为单独专题返回。\n\n"
                    f"groups={json.dumps(group_payload, ensure_ascii=False)}"
                ),
            },
        ],
    }


def parse_topic_aggregation_payload(
    payload: dict[str, object],
    *,
    items: list[ItemForTopicAggregationDTO],
) -> list[TopicAggregationGroupDTO]:
    item_by_id = {str(item.id): item for item in items}
    used_ids: set[str] = set()
    groups: list[TopicAggregationGroupDTO] = []
    raw_topics = payload.get("topics")
    if not isinstance(raw_topics, list):
        raise SummarySchemaError("llm topic aggregation response missing topics")

    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            continue
        item_ids = _valid_item_ids(raw_topic.get("item_ids"), item_by_id, used_ids)
        if not item_ids:
            continue
        topic_items = [item_by_id[item_id] for item_id in item_ids]
        groups.append(
            _build_llm_topic_group(
                items=topic_items,
                title=_optional_string(raw_topic.get("title_zh")),
                summary_zh=_optional_string(raw_topic.get("summary_zh")),
                importance_zh=_optional_string(raw_topic.get("importance_zh")),
                tags=_string_list(raw_topic.get("tags"), maximum=12),
                confidence=_confidence(raw_topic.get("confidence")),
            )
        )
        used_ids.update(item_ids)

    for item_id, item in item_by_id.items():
        if item_id in used_ids:
            continue
        groups.append(
            _build_llm_topic_group(
                items=[item],
                title=item.title,
                summary_zh=item.summary_zh,
                importance_zh=item.importance_zh,
                tags=item.tags,
                confidence=None,
            )
        )

    return groups


def parse_topic_consolidation_payload(
    payload: dict[str, object],
    *,
    groups: list[TopicAggregationGroupDTO],
) -> list[TopicAggregationGroupDTO]:
    group_by_id = {f"g{index}": group for index, group in enumerate(groups, start=1)}
    used_ids: set[str] = set()
    consolidated_groups: list[TopicAggregationGroupDTO] = []
    raw_topics = payload.get("topics")
    if not isinstance(raw_topics, list):
        raise SummarySchemaError("llm topic consolidation response missing topics")

    for raw_topic in raw_topics:
        if not isinstance(raw_topic, dict):
            continue
        group_ids = _valid_group_ids(raw_topic.get("group_ids"), group_by_id, used_ids)
        if not group_ids:
            continue
        topic_groups = [group_by_id[group_id] for group_id in group_ids]
        consolidated_groups.append(
            _build_consolidated_topic_group(
                groups=topic_groups,
                title=_optional_string(raw_topic.get("title_zh")),
                summary_zh=_optional_string(raw_topic.get("summary_zh")),
                importance_zh=_optional_string(raw_topic.get("importance_zh")),
                tags=_string_list(raw_topic.get("tags"), maximum=12),
                confidence=_confidence(raw_topic.get("confidence")),
            )
        )
        used_ids.update(group_ids)

    for group_id, group in group_by_id.items():
        if group_id not in used_ids:
            consolidated_groups.append(group)

    return consolidated_groups


def _extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise SummarySchemaError("llm response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise SummarySchemaError("llm response choice is invalid")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise SummarySchemaError("llm response missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise SummarySchemaError("llm response missing content")
    return content


def _parse_summary_json(content: str) -> dict[str, object]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SummarySchemaError("llm response content is not valid json") from exc
    if not isinstance(payload, dict):
        raise SummarySchemaError("llm response json is not an object")
    return payload


def _build_llm_topic_group(
    *,
    items: list[ItemForTopicAggregationDTO],
    title: str | None,
    summary_zh: str | None,
    importance_zh: str | None,
    tags: list[str],
    confidence: float | None,
) -> TopicAggregationGroupDTO:
    ordered_items = sorted(
        items,
        key=lambda item: (
            -float(item.score),
            -_timestamp(item.published_at or item.collected_at),
            str(item.id),
        ),
    )
    primary = ordered_items[0]
    timestamps = [item.published_at or item.collected_at for item in ordered_items]
    source_count = len({item.source_id for item in ordered_items})
    item_count_bonus = min((len(ordered_items) - 1) * 1.0, 10.0)
    source_count_bonus = min((source_count - 1) * 3.0, 15.0)
    confidence_bonus = round((confidence or 0) * 5, 2)
    score = round(
        min(
            100.0,
            float(primary.score) + item_count_bonus + source_count_bonus + confidence_bonus,
        ),
        2,
    )
    merged_tags = _merge_tags(tags, ordered_items)

    return TopicAggregationGroupDTO(
        normalized_key=_llm_key_from_ids([item.id for item in ordered_items]),
        title=(title or primary.title).strip()[:500],
        category=primary.category,
        tags=merged_tags,
        item_ids=[item.id for item in ordered_items],
        primary_item_id=primary.id,
        score=score,
        source_count=source_count,
        first_seen_at=min(timestamps),
        last_seen_at=max(timestamps),
        summary_zh=summary_zh or primary.summary_zh,
        importance_zh=importance_zh or primary.importance_zh,
        confidence=confidence,
    )


def _build_consolidated_topic_group(
    *,
    groups: list[TopicAggregationGroupDTO],
    title: str | None,
    summary_zh: str | None,
    importance_zh: str | None,
    tags: list[str],
    confidence: float | None,
) -> TopicAggregationGroupDTO:
    ordered_groups = sorted(
        groups,
        key=lambda group: (-float(group.score), -_timestamp(group.last_seen_at), group.normalized_key),
    )
    primary = ordered_groups[0]
    item_ids = _merge_item_ids(ordered_groups)
    merged_tags = _merge_group_tags(tags, ordered_groups)
    source_count = min(len(item_ids), sum(max(group.source_count, 1) for group in ordered_groups))
    confidence_bonus = round((confidence or 0) * 5, 2)
    cross_group_bonus = min((len(ordered_groups) - 1) * 2.0, 10.0)
    score = round(min(100.0, float(primary.score) + cross_group_bonus + confidence_bonus), 2)

    return TopicAggregationGroupDTO(
        normalized_key=_llm_key_from_ids(item_ids),
        title=(title or primary.title).strip()[:500],
        category=primary.category,
        tags=merged_tags,
        item_ids=item_ids,
        primary_item_id=primary.primary_item_id,
        score=score,
        source_count=source_count,
        first_seen_at=min(group.first_seen_at for group in ordered_groups),
        last_seen_at=max(group.last_seen_at for group in ordered_groups),
        summary_zh=summary_zh or primary.summary_zh,
        importance_zh=importance_zh or primary.importance_zh,
        confidence=confidence,
    )


def _llm_key_from_ids(item_ids: list[UUID]) -> str:
    digest = hashlib.sha256(",".join(sorted(str(item_id) for item_id in item_ids)).encode()).hexdigest()
    return f"llm:{digest[:48]}"


def _valid_item_ids(
    value: object,
    item_by_id: dict[str, ItemForTopicAggregationDTO],
    used_ids: set[str],
) -> list[str]:
    if not isinstance(value, list):
        return []
    valid_ids: list[str] = []
    for raw_id in value:
        item_id = str(raw_id)
        if item_id in item_by_id and item_id not in used_ids and item_id not in valid_ids:
            valid_ids.append(item_id)
    return valid_ids


def _valid_group_ids(
    value: object,
    group_by_id: dict[str, TopicAggregationGroupDTO],
    used_ids: set[str],
) -> list[str]:
    if not isinstance(value, list):
        return []
    valid_ids: list[str] = []
    for raw_id in value:
        group_id = str(raw_id)
        if group_id in group_by_id and group_id not in used_ids and group_id not in valid_ids:
            valid_ids.append(group_id)
    return valid_ids


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _string_list(value: object, *, maximum: int) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        tag = item.strip()[:40]
        key = tag.lower()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
        if len(tags) >= maximum:
            break
    return tags


def _merge_tags(tags: list[str], items: list[ItemForTopicAggregationDTO]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for tag in [*tags, *(tag for item in items for tag in item.tags)]:
        normalized_tag = tag.strip()[:40]
        key = normalized_tag.lower()
        if normalized_tag and key not in seen:
            seen.add(key)
            merged.append(normalized_tag)
        if len(merged) >= 30:
            break
    return merged


def _merge_group_tags(tags: list[str], groups: list[TopicAggregationGroupDTO]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for tag in [*tags, *(tag for group in groups for tag in group.tags)]:
        normalized_tag = tag.strip()[:40]
        key = normalized_tag.lower()
        if normalized_tag and key not in seen:
            seen.add(key)
            merged.append(normalized_tag)
        if len(merged) >= 30:
            break
    return merged


def _merge_item_ids(groups: list[TopicAggregationGroupDTO]) -> list[UUID]:
    item_ids: list[UUID] = []
    seen: set[str] = set()
    for group in groups:
        for item_id in group.item_ids:
            key = str(item_id)
            if key not in seen:
                seen.add(key)
                item_ids.append(item_id)
    return item_ids


def _confidence(value: object) -> float | None:
    if value is None:
        return None
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    return min(max(confidence, 0.0), 1.0)


def _timestamp(value: object) -> float:
    if not hasattr(value, "timestamp"):
        return 0
    return value.timestamp()


def _clip(value: str | None, maximum: int) -> str | None:
    if not value:
        return None
    return value.strip()[:maximum] or None
