import json
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.application.content_library.agent import (
    DatabaseSearchTool,
    LibrarySearchAgentClient,
    LibrarySearchAgentSchemaError,
    parse_agent_payload,
)
from app.application.content_library.dtos import (
    LibraryAgentParseDTO,
    LibraryLLMProviderDTO,
)


class _AgentQueryResponse(BaseModel):
    keyword: str | None = None
    search_terms: list[str] = Field(default_factory=list)
    source_id: str | None = None
    source_type: str | None = None
    category: str | None = None
    status: str | None = None
    published_from: str | None = None
    published_to: str | None = None
    min_score: float | None = None
    has_summary: bool | None = None
    sort: str = "latest"
    page_size: int = 10
    explanation: str = ""
    confidence: float = 0.5


class DeepAgentsLibrarySearchClient(LibrarySearchAgentClient):
    def interpret_query(
        self,
        *,
        provider: LibraryLLMProviderDTO,
        query: str,
        page_size: int,
        current_time: datetime,
        database_search_tool: DatabaseSearchTool,
    ) -> LibraryAgentParseDTO:
        try:
            from deepagents import (
                GeneralPurposeSubagentProfile,
                HarnessProfile,
                create_deep_agent,
                register_harness_profile,
            )
            from langchain_core.tools import tool
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("deepagents runtime dependencies are not installed") from exc

        started_at = time.perf_counter()
        model = ChatOpenAI(
            model=provider.model,
            api_key=provider.api_key,
            base_url=provider.base_url,
            timeout=provider.timeout_seconds,
            max_retries=provider.retry_count,
        )
        _register_restricted_openai_profile(
            register_harness_profile=register_harness_profile,
            HarnessProfile=HarnessProfile,
            GeneralPurposeSubagentProfile=GeneralPurposeSubagentProfile,
        )
        database_tool = tool(database_search_tool)
        agent = create_deep_agent(
            model=model,
            tools=[database_tool],
            system_prompt=_SYSTEM_PROMPT,
            response_format=_AgentQueryResponse,
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _user_prompt(
                            query=query,
                            page_size=page_size,
                            current_time=current_time,
                        ),
                    }
                ]
            },
            config={"recursion_limit": 8},
        )
        payload = _extract_structured_response(result)
        payload.setdefault("input_tokens", None)
        payload.setdefault("output_tokens", None)
        payload["latency_ms"] = round((time.perf_counter() - started_at) * 1000)
        return parse_agent_payload(payload, fallback_query=query, page_size=page_size)


def _register_restricted_openai_profile(
    *,
    register_harness_profile: Any,
    HarnessProfile: Any,
    GeneralPurposeSubagentProfile: Any,
) -> None:
    register_harness_profile(
        "openai",
        HarnessProfile(
            excluded_tools=frozenset(
                {
                    "ls",
                    "read_file",
                    "write_file",
                    "edit_file",
                    "glob",
                    "grep",
                    "execute",
                    "task",
                }
            ),
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )


def _extract_structured_response(result: object) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise LibrarySearchAgentSchemaError("deepagents returned an invalid state")
    structured = result.get("structured_response")
    if isinstance(structured, BaseModel):
        return structured.model_dump()
    if isinstance(structured, dict):
        return dict(structured)

    messages = result.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            content = getattr(message, "content", None)
            if isinstance(content, str):
                parsed = _parse_json_content(content)
                if parsed is not None:
                    return parsed
    raise LibrarySearchAgentSchemaError("deepagents returned no structured response")


def _parse_json_content(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _user_prompt(*, query: str, page_size: int, current_time: datetime) -> str:
    return (
        "用户自然语言查询如下：\n"
        f"{query}\n\n"
        f"当前时间：{current_time.isoformat()}\n"
        f"预览条数上限：{page_size}\n\n"
        "请先理解查询意图，然后必须调用 search_library_database 一次查询数据库。"
        "只能使用工具返回的已入库结果。最后按 response_format 返回结构化查询条件、"
        "简短中文 explanation 和 0 到 1 的 confidence。"
    )


_SYSTEM_PROMPT = """
你是 Daily News 的站内信息库查询 Agent。

严格规则：
1. 你只能查询系统已入库的内容，不能联网、不能抓取、不能新增来源。
2. 你必须使用 search_library_database 工具执行查询，不能凭记忆回答。
3. 只能传递工具 schema 中允许的筛选字段，不能生成 SQL。
4. source_type、category、status、sort 必须使用系统允许的值。
5. “最近 N 天”等时间表达必须根据当前时间转换成 ISO 8601 时间。
6. search_terms 可以包含用户关键词的英文或中文同义词，但最多 8 个。
7. 最终输出必须是结构化 response_format，不要输出 Markdown。
"""
