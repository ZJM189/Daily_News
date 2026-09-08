from dataclasses import dataclass
from typing import Any, Protocol

from app.application.content_library.dtos import LibraryChatMessageDTO, LibraryLLMProviderDTO

LIBRARY_CHAT_REJECTION_MESSAGE = (
    "我只能查询已入库的 AI 信息、论文、开源项目和产业动态。"
    "你可以试试：“最近 7 天 RAG 论文”或“GitHub 上高分 Agent 项目”。"
)

ALLOWED_INTENTS = {
    "library_search",
    "library_filter",
    "library_summarize_results",
    "library_followup",
}

BLOCKED_INTENTS = {
    "general_chat",
    "coding",
    "finance",
    "weather",
    "medical",
    "legal",
    "external_web_search",
    "prompt_injection",
    "content_generation",
    "unknown",
}

AI_LIBRARY_KEYWORDS = {
    "ai",
    "agent",
    "agents",
    "anthropic",
    "arxiv",
    "chatgpt",
    "claude",
    "deepseek",
    "diffusion",
    "github",
    "gpt",
    "hugging face",
    "llm",
    "model",
    "openai",
    "paper",
    "rag",
    "transformer",
    "产品发布",
    "产业动态",
    "人工智能",
    "信息库",
    "入库",
    "大模型",
    "开源",
    "模型",
    "论文",
}

LIBRARY_ACTION_KEYWORDS = {
    "找",
    "查",
    "查询",
    "检索",
    "筛选",
    "搜索",
    "总结",
    "高分",
    "最近",
    "来源",
    "摘要",
    "分数",
}

CODE_KEYWORDS = {
    "api",
    "bug",
    "code",
    "javascript",
    "python",
    "react",
    "typescript",
    "代码",
    "接口",
    "脚本",
    "爬虫",
    "程序",
}

CODE_ACTION_KEYWORDS = {
    "debug",
    "报错",
    "调试",
    "函数",
    "后端",
    "前端",
    "实现",
    "怎么写",
    "组件",
    "运行",
}

BLOCKED_PHRASES = {
    "写代码": "coding",
    "帮我写": "content_generation",
    "生成文章": "content_generation",
    "生成论文": "content_generation",
    "讲个笑话": "general_chat",
    "天气": "weather",
    "股票": "finance",
    "基金": "finance",
    "法律": "legal",
    "医疗": "medical",
    "联网查": "external_web_search",
    "实时搜索": "external_web_search",
    "实时搜": "external_web_search",
    "外部搜索": "external_web_search",
    "忽略前面": "prompt_injection",
    "忽略以上": "prompt_injection",
    "系统提示词": "prompt_injection",
    "system prompt": "prompt_injection",
}


@dataclass(frozen=True, slots=True)
class LibraryChatIntentDTO:
    allowed: bool
    intent: str
    confidence: float
    reason: str
    normalized_query: str | None = None


class LibraryChatIntentClassifier(Protocol):
    def classify(
        self,
        *,
        provider: LibraryLLMProviderDTO | None,
        query: str,
        previous_messages: list[LibraryChatMessageDTO],
    ) -> LibraryChatIntentDTO:
        raise NotImplementedError


def classify_library_chat_intent_by_rules(
    query: str,
    *,
    previous_messages: list[LibraryChatMessageDTO] | None = None,
) -> LibraryChatIntentDTO | None:
    normalized_query = _clean_text(query)
    if normalized_query is None:
        return LibraryChatIntentDTO(
            allowed=False,
            intent="unknown",
            confidence=1.0,
            reason="empty query",
            normalized_query=None,
        )

    text = normalized_query.casefold()
    has_code_keyword = _has_any(text, CODE_KEYWORDS)
    has_library_keyword = _has_any(text, AI_LIBRARY_KEYWORDS)
    if has_code_keyword and (not has_library_keyword or _has_any(text, CODE_ACTION_KEYWORDS)):
        return LibraryChatIntentDTO(
            allowed=False,
            intent="coding",
            confidence=0.9,
            reason="coding request is outside library-search scope",
            normalized_query=normalized_query,
        )

    for phrase, intent in BLOCKED_PHRASES.items():
        if phrase.casefold() in text:
            return LibraryChatIntentDTO(
                allowed=False,
                intent=intent,
                confidence=0.92,
                reason="query is outside library-search scope",
                normalized_query=normalized_query,
            )

    if has_library_keyword and _has_any(text, LIBRARY_ACTION_KEYWORDS):
        return LibraryChatIntentDTO(
            allowed=True,
            intent="library_search",
            confidence=0.82,
            reason="query matches AI library search terms",
            normalized_query=normalized_query,
        )

    if has_library_keyword:
        return LibraryChatIntentDTO(
            allowed=True,
            intent="library_search",
            confidence=0.74,
            reason="query references AI library content",
            normalized_query=normalized_query,
        )

    if _looks_like_followup(text) and _has_recent_library_answer(previous_messages or []):
        return LibraryChatIntentDTO(
            allowed=True,
            intent="library_followup",
            confidence=0.7,
            reason="query follows a prior library result",
            normalized_query=normalized_query,
        )

    return None


def sanitize_library_chat_intent(
    payload: dict[str, Any],
    *,
    original_query: str,
) -> LibraryChatIntentDTO:
    intent = _clean_text(payload.get("intent"), max_length=80) or "unknown"
    confidence = _bounded_confidence(payload.get("confidence"))
    allowed = bool(payload.get("allowed")) and intent in ALLOWED_INTENTS and confidence >= 0.55
    if intent in BLOCKED_INTENTS:
        allowed = False
    normalized_query = _clean_text(payload.get("normalized_query")) or _clean_text(original_query)
    return LibraryChatIntentDTO(
        allowed=allowed,
        intent=intent if intent in ALLOWED_INTENTS | BLOCKED_INTENTS else "unknown",
        confidence=confidence,
        reason=_clean_text(payload.get("reason"), max_length=200) or "intent classified",
        normalized_query=normalized_query,
    )


def _has_any(text: str, terms: set[str]) -> bool:
    return any(term.casefold() in text for term in terms)


def _looks_like_followup(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "再",
            "这些",
            "结果",
            "只看",
            "换成",
            "筛选",
            "高分",
            "展开",
            "总结",
        )
    )


def _has_recent_library_answer(messages: list[LibraryChatMessageDTO]) -> bool:
    for message in reversed(messages[-6:]):
        if message.role != "assistant":
            continue
        mode = message.metadata.get("mode")
        if mode in {"llm", "fallback"}:
            return True
    return False


def _clean_text(value: object, *, max_length: int = 200) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text[:max_length] if text else None


def _bounded_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)
