from typing import Protocol
from uuid import UUID

from app.application.llm_operations.dtos import LLMProviderDTO


class LLMProviderRepository(Protocol):
    def list_providers(
        self,
        *,
        enabled: bool | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[LLMProviderDTO], int]:
        raise NotImplementedError

    def create_provider(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        model: str,
        encrypted_api_key: str | None,
        api_key_masked: str | None,
        timeout_seconds: int,
        retry_count: int,
        enabled: bool,
        is_default: bool,
    ) -> LLMProviderDTO:
        raise NotImplementedError

    def update_provider(
        self,
        *,
        provider_id: UUID,
        name: str | None,
        base_url: str | None,
        model: str | None,
        encrypted_api_key: str | None,
        api_key_masked: str | None,
        api_key_provided: bool,
        timeout_seconds: int | None,
        retry_count: int | None,
        enabled: bool | None,
        is_default: bool | None,
    ) -> LLMProviderDTO | None:
        raise NotImplementedError

    def set_default_provider(self, provider_id: UUID) -> LLMProviderDTO | None:
        raise NotImplementedError
