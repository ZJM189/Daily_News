import json
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

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
from app.infrastructure.config import get_settings


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
                            current_time=current_time.astimezone(
                                ZoneInfo(get_settings().default_timezone)
                            ),
                        ),
                    }
                ]
            },
            config={"recursion_limit": 16},
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
        f"当前时间（Asia/Shanghai）：{current_time.isoformat()}\n"
        f"预览条数上限：{page_size}\n\n"
        "请先把查询转换成数据库筛选条件，然后必须调用 search_library_database 恰好一次。"
        "工具返回后立即停止工具调用，并按 response_format 输出结果；不要重复调用工具，"
        "不要为了扩大结果再次搜索。\n\n"
        "字段规则：\n"
        "- keyword 只能是一个短主题、项目名、公司名或缩写，例如 RAG、Agent、OpenAI；"
        "绝不能包含“最近 7 天”“相关”“论文”“项目”“产品发布”等查询修饰词，"
        "也绝不能放入整句原始问题。\n"
        "- search_terms 只能放 1 到 4 个精确可检索词。RAG 可使用 "
        "[\"RAG\", \"retrieval augmented generation\", \"retrieval-augmented generation\"]；"
        "禁止单独使用 retrieval、augmented、generation、AI、论文、项目、知识库、向量检索等宽泛词。"
        "不要把 keyword 原句重复放入 search_terms。\n"
        "- category 只能使用：model_company、open_source、research_paper、"
        "product_launch、community、industry_funding、other。\n"
        "- source_type 只能使用：rss、hacker_news、github、arxiv、product_hunt、hugging_face。"
        "当前部署的 arXiv 内容来自名为 arXiv Computer Science 的 RSS source，"
        "所以查询 arXiv 论文时使用 category=research_paper，通常不要设置 source_type=arxiv。\n"
        "- “论文”“研究论文”“学术论文”必须设置 category=research_paper；"
        "“GitHub 开源项目”设置 source_type=github 和 category=open_source；"
        "OpenAI、DeepMind、Anthropic 的产品或公司动态在当前库中通常属于 model_company，"
        "不要为了“产品发布”强行设置 product_launch。\n"
        "- 当前数据库按 coalesce(published_at, collected_at) 过滤时间。"
        "“最近 N 天”表示从当前时间往前 N×24 小时到当前时间，"
        "published_from 和 published_to 必须带 Asia/Shanghai 的时区偏移，不能扩展到当天未来时间。\n"
        "- min_score 是最低分；“80 分以上”设置 min_score=80；"
        "“高分”只设置 sort=score，不要擅自猜测最低分。\n"
        "- 没有明确条件的字段必须返回 null 或默认值，不要臆造 source_id。\n\n"
        "示例：\n"
        "1. “最近 7 天与 RAG 相关的研究论文”应调用："
        "keyword=RAG，search_terms=[RAG, retrieval augmented generation, "
        "retrieval-augmented generation]，category=research_paper，"
        "published_from=当前时间减 7 天，published_to=当前时间，sort=latest。\n"
        "2. “GitHub 上 80 分以上的 Agent 开源项目”应调用："
        "keyword=Agent，search_terms=[Agent]，source_type=github，"
        "category=open_source，min_score=80，sort=score。\n"
        "3. “OpenAI 最近的产品动态”应调用："
        "keyword=OpenAI，search_terms=[OpenAI]，category=model_company，sort=latest。\n\n"
        "只能使用工具返回的已入库结果，不能联网、不能凭记忆补充结果。"
        "最后按 response_format 返回短中文 explanation 和 0 到 1 的 confidence。"
    )


_SYSTEM_PROMPT = """
你是 Daily News 的站内信息库查询 Agent。

严格规则：
1. 你只能查询系统已入库的内容，不能联网、不能抓取、不能新增来源。
2. 你必须使用 search_library_database 工具执行查询，不能凭记忆回答。
3. 只能调用 search_library_database 一次；工具返回后立即输出结构化结果，不得重复搜索。
4. 只能传递工具 schema 中允许的筛选字段，不能生成 SQL。
5. source_type、category、status、sort 必须使用系统允许的值。
6. keyword 必须是短主题词，不能是完整自然语言句子。
7. search_terms 最多 4 个，必须是精确主题词或完整短语，不能使用宽泛单词。
8. “最近 N 天”必须转换成当前时间往前 N×24 小时的闭区间。
9. 当前 arXiv 内容通常来自 RSS source，论文查询优先使用 category=research_paper。
10. 最终输出必须是结构化 response_format，不要输出 Markdown。
"""
