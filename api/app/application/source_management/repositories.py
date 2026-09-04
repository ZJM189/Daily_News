from typing import Any, Protocol
from uuid import UUID

from app.application.source_management.dtos import SourceCredentialDTO, SourceDTO


class SourceManagementRepository(Protocol):
    def list_credentials(
        self,
        *,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceCredentialDTO], int]:
        raise NotImplementedError

    def get_credential(self, credential_id: UUID) -> SourceCredentialDTO | None:
        raise NotImplementedError

    def create_credential(
        self,
        *,
        name: str,
        source_type: str,
        encrypted_secret: str,
        secret_masked: str,
        status: str,
        actor_id: UUID,
    ) -> SourceCredentialDTO:
        raise NotImplementedError

    def update_credential(
        self,
        *,
        credential_id: UUID,
        name: str | None,
        encrypted_secret: str | None,
        secret_masked: str | None,
        status: str | None,
        actor_id: UUID,
    ) -> SourceCredentialDTO | None:
        raise NotImplementedError

    def list_sources(
        self,
        *,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceDTO], int]:
        raise NotImplementedError

    def get_source(self, source_id: UUID) -> SourceDTO | None:
        raise NotImplementedError

    def create_source(
        self,
        *,
        name: str,
        source_type: str,
        status: str,
        url: str | None,
        query_config: dict[str, Any],
        credential_id: UUID | None,
        credential_env_key: str | None,
        weight: int,
        language: str | None,
    ) -> SourceDTO:
        raise NotImplementedError

    def update_source(
        self,
        *,
        source_id: UUID,
        name: str | None,
        status: str | None,
        url: str | None,
        url_provided: bool,
        query_config: dict[str, Any] | None,
        credential_id: UUID | None,
        credential_id_provided: bool,
        credential_env_key: str | None,
        credential_env_key_provided: bool,
        weight: int | None,
        language: str | None,
        language_provided: bool,
    ) -> SourceDTO | None:
        raise NotImplementedError
