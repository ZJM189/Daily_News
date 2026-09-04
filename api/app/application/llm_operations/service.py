from uuid import UUID

from app.application.identity.dtos import UserDTO
from app.application.llm_operations.dtos import LLMProviderDTO
from app.application.llm_operations.repositories import LLMProviderRepository
from app.domain.identity.exceptions import PermissionDenied
from app.domain.llm_operations.exceptions import LLMProviderAlreadyExists, LLMProviderNotFound
from app.infrastructure.secrets import SecretCipher, mask_secret


class LLMProviderService:
    def __init__(self, repository: LLMProviderRepository, secret_cipher: SecretCipher) -> None:
        self._repository = repository
        self._secret_cipher = secret_cipher

    def list_providers(
        self,
        *,
        actor: UserDTO,
        enabled: bool | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[LLMProviderDTO], int]:
        self._require_admin(actor)
        return self._repository.list_providers(
            enabled=enabled,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def create_provider(
        self,
        *,
        actor: UserDTO,
        name: str,
        base_url: str,
        model: str,
        api_key: str | None,
        timeout_seconds: int,
        retry_count: int,
        enabled: bool,
        is_default: bool,
    ) -> LLMProviderDTO:
        self._require_admin(actor)
        try:
            return self._repository.create_provider(
                name=name.strip(),
                provider_type="openai_compatible",
                base_url=base_url.strip(),
                model=model.strip(),
                encrypted_api_key=self._secret_cipher.encrypt(api_key) if api_key else None,
                api_key_masked=mask_secret(api_key) if api_key else None,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                enabled=enabled,
                is_default=is_default,
            )
        except ValueError as exc:
            raise LLMProviderAlreadyExists("llm provider name already exists") from exc

    def update_provider(
        self,
        *,
        actor: UserDTO,
        provider_id: UUID,
        name: str | None,
        base_url: str | None,
        model: str | None,
        api_key: str | None,
        api_key_provided: bool,
        timeout_seconds: int | None,
        retry_count: int | None,
        enabled: bool | None,
        is_default: bool | None,
    ) -> LLMProviderDTO:
        self._require_admin(actor)
        try:
            provider = self._repository.update_provider(
                provider_id=provider_id,
                name=name.strip() if name is not None else None,
                base_url=base_url.strip() if base_url is not None else None,
                model=model.strip() if model is not None else None,
                encrypted_api_key=self._secret_cipher.encrypt(api_key)
                if api_key_provided and api_key
                else None,
                api_key_masked=mask_secret(api_key) if api_key_provided and api_key else None,
                api_key_provided=api_key_provided,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                enabled=enabled,
                is_default=is_default,
            )
        except ValueError as exc:
            raise LLMProviderAlreadyExists("llm provider name already exists") from exc
        if provider is None:
            raise LLMProviderNotFound("llm provider not found")
        return provider

    def set_default_provider(self, *, actor: UserDTO, provider_id: UUID) -> LLMProviderDTO:
        self._require_admin(actor)
        provider = self._repository.set_default_provider(provider_id)
        if provider is None:
            raise LLMProviderNotFound("llm provider not found")
        return provider

    def _require_admin(self, actor: UserDTO) -> None:
        if actor.role != "admin":
            raise PermissionDenied("admin role required")
