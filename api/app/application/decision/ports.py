from typing import Any, Protocol

from app.application.decision.dtos import StructuredDecisionDTO


class StructuredDecisionClient(Protocol):
    def evaluate(
        self,
        *,
        state: dict[str, Any],
        questions: dict[str, dict[str, Any]],
    ) -> StructuredDecisionDTO:
        raise NotImplementedError
