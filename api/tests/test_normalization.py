from app.application.ingestion.service import extract_text_field, hash_title, normalize_title
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
