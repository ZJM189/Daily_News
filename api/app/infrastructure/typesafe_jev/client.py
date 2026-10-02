from __future__ import annotations

import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.application.decision.dtos import StructuredAnswerDTO, StructuredDecisionDTO

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504, 529}
MAX_RETRY_DELAY_SECONDS = 30.0


class JevClientError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JevClientConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 30
    retry_count: int = 3


class TypeSafeJevClient:
    """Adapter for the TypeSafe System One endpoint."""

    def __init__(
        self,
        config: JevClientConfig,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport

    def evaluate(
        self,
        *,
        state: dict[str, Any],
        questions: dict[str, dict[str, Any]],
    ) -> StructuredDecisionDTO:
        if not self._config.api_key:
            raise JevClientError("TypeSafe API key is not configured")

        started_at = time.perf_counter()
        payload = {
            "model": self._config.model,
            "state": state,
            "questions": questions,
        }
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }
        response_payload = self._post(payload=payload, headers=headers)
        answers = _extract_answers(response_payload, questions=questions)
        usage = response_payload.get("usage")
        input_tokens = _int_or_none(usage.get("input_tokens")) if isinstance(usage, dict) else None
        output_tokens = (
            _int_or_none(usage.get("output_tokens")) if isinstance(usage, dict) else None
        )
        return StructuredDecisionDTO(
            model=str(response_payload.get("model") or self._config.model),
            answers=answers,
            latency_ms=round((time.perf_counter() - started_at) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _post(self, *, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        attempts = max(self._config.retry_count, 0) + 1
        last_error: Exception | None = None
        endpoint = _endpoint(self._config.base_url)
        with httpx.Client(
            timeout=self._config.timeout_seconds,
            transport=self._transport,
        ) as client:
            for attempt in range(attempts):
                try:
                    response = client.post(endpoint, headers=headers, json=payload)
                    if response.status_code not in RETRYABLE_STATUS_CODES:
                        response.raise_for_status()
                        body = response.json()
                        if not isinstance(body, dict):
                            raise JevClientError("TypeSafe returned a non-object response")
                        return body
                    last_error = httpx.HTTPStatusError(
                        f"TypeSafe retryable status code: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                    if attempt >= attempts - 1:
                        response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if not _retryable_http_error(exc) or attempt >= attempts - 1:
                        raise JevClientError(_http_error_message(exc)) from exc
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= attempts - 1:
                        raise JevClientError(f"TypeSafe request failed: {exc}") from exc

                _sleep_before_retry(attempt=attempt, error=last_error)

        raise JevClientError("TypeSafe request failed without a response")


def _endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/v1/systemone"):
        return normalized
    return f"{normalized}/v1/systemone"


def _extract_answers(
    payload: dict[str, Any],
    *,
    questions: dict[str, dict[str, Any]],
) -> dict[str, StructuredAnswerDTO]:
    answers_payload: object = payload.get("answers")
    if not isinstance(answers_payload, dict):
        data = payload.get("data")
        answers_payload = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(answers_payload, dict):
        raise JevClientError("TypeSafe response does not contain answers")

    answers: dict[str, StructuredAnswerDTO] = {}
    for name, question in questions.items():
        raw_answer = answers_payload.get(name)
        answers[name] = _parse_answer(raw_answer, question_type=str(question.get("type", "")))
    return answers


def _parse_answer(raw_answer: object, *, question_type: str) -> StructuredAnswerDTO:
    if isinstance(raw_answer, dict):
        value: object
        if question_type == "choice":
            value = raw_answer.get("choice", raw_answer.get("value"))
        elif question_type == "score":
            value = raw_answer.get("score", raw_answer.get("value"))
        else:
            value = raw_answer.get(
                "noul",
                raw_answer.get("probability", raw_answer.get("value")),
            )
        probability = raw_answer.get("probability", raw_answer.get("noul"))
        confidence = raw_answer.get("confidence", raw_answer.get("certainty", 0.0))
        return StructuredAnswerDTO(
            question_type=str(raw_answer.get("type") or question_type),
            value=value,
            confidence=_bounded_confidence(confidence),
            probability=_probability_or_none(probability),
        )
    return StructuredAnswerDTO(
        question_type=question_type,
        value=raw_answer,
        confidence=0.0,
        probability=_probability_or_none(raw_answer) if question_type == "noul" else None,
    )


def _retryable_http_error(error: httpx.HTTPStatusError) -> bool:
    return error.response.status_code in RETRYABLE_STATUS_CODES


def _http_error_message(error: httpx.HTTPStatusError) -> str:
    status = error.response.status_code
    try:
        body = error.response.json()
    except ValueError:
        body = error.response.text[:500]
    return f"TypeSafe request failed with HTTP {status}: {body}"


def _sleep_before_retry(*, attempt: int, error: Exception | None) -> None:
    response = error.response if isinstance(error, httpx.HTTPStatusError) else None
    delay = _retry_after_delay(response)
    if delay is None:
        delay = min((2**attempt) + random.uniform(0, 1), MAX_RETRY_DELAY_SECONDS)
    time.sleep(delay)


def _retry_after_delay(response: httpx.Response | None) -> float | None:
    if response is None:
        return None
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        return min(max(float(retry_after), 0.0), MAX_RETRY_DELAY_SECONDS)
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(retry_after)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        return None
    return min(max(retry_at.timestamp() - time.time(), 0.0), MAX_RETRY_DELAY_SECONDS)


def _bounded_confidence(value: object) -> float:
    try:
        return min(max(float(value), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.0


def _probability_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return min(max(float(value), 0.0), 1.0)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
