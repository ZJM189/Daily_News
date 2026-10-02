from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class StructuredAnswerDTO:
    question_type: str
    value: Any
    confidence: float
    probability: float | None = None


@dataclass(frozen=True, slots=True)
class StructuredDecisionDTO:
    model: str
    answers: dict[str, StructuredAnswerDTO]
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ItemDecisionDTO:
    is_ai_related: float
    prompt_injection: float
    importance_score: float
    quality_score: float
    category: str
    confidence: float
    model: str
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class ItemDecisionEvaluationDTO:
    decision: ItemDecisionDTO | None
    status: str
    error_message: str | None = None
