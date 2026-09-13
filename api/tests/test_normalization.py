from app.application.ingestion.service import (
    extract_standard_fields,
    extract_text_field,
    hash_title,
    normalize_title,
)
from app.infrastructure.ingestion.repositories import _category_for_source
from app.infrastructure.models import CategoryCode, Source, SourceStatus, SourceType


def test_normalize_title_compacts_whitespace_and_lowercases() -> None:
    assert normalize_title("  OpenAI   Releases GPT  ") == "openai releases gpt"


def test_hash_title_is_stable_sha256() -> None:
    assert (
        hash_title("openai releases gpt")
        == "f90168d8d11e9b77a434aa629295ad3efb5b30f0176f58f54fe107e308ebd88e"
    )


def test_extract_text_field_reads_first_available_child_text() -> None:
    payload = {
        "children": {
            "description": {"text": "  A   useful update.  "},
            "summary": {"text": "Fallback"},
        }
    }

    assert extract_text_field(payload, "description", "summary") == "A useful update."


def test_extract_text_field_reads_top_level_text() -> None:
    payload = {"description": "  AI   coding agent.  "}

    assert extract_text_field(payload, "description", "summary") == "AI coding agent."


def test_extract_standard_fields_maps_github_payload() -> None:
    fields = extract_standard_fields(
        {
            "description": "AI coding agent",
            "metrics": {"stars": 1000, "forks": 40, "open_issues": 5},
            "source_payload": {"ignored": "large upstream payload"},
        }
    )

    assert fields.summary_original == "AI coding agent"
    assert fields.content_snippet == "AI coding agent"
    assert fields.tags == []
    assert fields.metrics == {"stars": 1000, "forks": 40, "open_issues": 5}


def test_extract_standard_fields_maps_product_hunt_topics_to_tags() -> None:
    fields = extract_standard_fields(
        {
            "description": "Summarize daily AI news",
            "topics": ["Artificial Intelligence", "AI", "AI"],
            "metrics": {"votes": 10, "comments": 2},
        }
    )

    assert fields.summary_original == "Summarize daily AI news"
    assert fields.tags == ["Artificial Intelligence", "AI"]
    assert fields.metrics == {"votes": 10, "comments": 2}


def test_extract_standard_fields_maps_hugging_face_tags_and_metrics() -> None:
    fields = extract_standard_fields(
        {
            "description": "text-generation / transformers, llm",
            "tags": ["transformers", "llm"],
            "metrics": {"likes": 500, "downloads": 12000, "ignored": None},
        }
    )

    assert fields.summary_original == "text-generation / transformers, llm"
    assert fields.tags == ["transformers", "llm"]
    assert fields.metrics == {"likes": 500, "downloads": 12000}


def test_extract_standard_fields_maps_rss_children_category_to_tags() -> None:
    fields = extract_standard_fields(
        {
            "children": {
                "description": {"text": "RAG research summary"},
                "category": {"text": "cs.AI"},
            }
        }
    )

    assert fields.summary_original == "RAG research summary"
    assert fields.content_snippet == "RAG research summary"
    assert fields.tags == ["cs.AI"]
    assert fields.metrics == {}


def test_category_for_source_uses_source_rules() -> None:
    assert _category_for_source(
        Source(name="arXiv Computer Science", type=SourceType.RSS, status=SourceStatus.ENABLED)
    ) == CategoryCode.RESEARCH_PAPER
    assert _category_for_source(
        Source(name="OpenAI News", type=SourceType.RSS, status=SourceStatus.ENABLED)
    ) == CategoryCode.MODEL_COMPANY
    assert _category_for_source(
        Source(name="GitHub AI Trending", type=SourceType.GITHUB, status=SourceStatus.ENABLED)
    ) == CategoryCode.OPEN_SOURCE
