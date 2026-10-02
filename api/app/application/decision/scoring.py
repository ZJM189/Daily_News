from app.application.decision.dtos import ItemDecisionEvaluationDTO


def compose_item_score(
    *,
    rule_score: float,
    rule_breakdown: dict[str, object],
    evaluation: ItemDecisionEvaluationDTO,
    jev_weight: float,
) -> tuple[float, dict[str, object]]:
    """Combine deterministic ranking with optional semantic decisions."""
    bounded_weight = min(max(jev_weight, 0.0), 1.0)
    decision = evaluation.decision
    if decision is None:
        breakdown = dict(rule_breakdown)
        breakdown["jev"] = {
            "status": evaluation.status,
            "error": evaluation.error_message,
        }
        breakdown["final"] = round(rule_score, 2)
        return round(rule_score, 2), breakdown

    jev_score = round(
        decision.is_ai_related * 40
        + decision.importance_score * 0.35
        + decision.quality_score * 0.25,
        2,
    )
    blocked = decision.prompt_injection >= 0.5
    final_score = round(
        0.0
        if blocked
        else min(100.0, rule_score * (1 - bounded_weight) + jev_score * bounded_weight),
        2,
    )
    breakdown = dict(rule_breakdown)
    breakdown["jev"] = {
        "status": evaluation.status,
        "blocked": blocked,
        "is_ai_related": decision.is_ai_related,
        "prompt_injection": decision.prompt_injection,
        "importance": decision.importance_score,
        "quality": decision.quality_score,
        "category": decision.category,
        "confidence": decision.confidence,
        "model": decision.model,
        "latency_ms": decision.latency_ms,
        "score": jev_score,
    }
    breakdown["final"] = final_score
    return final_score, breakdown
