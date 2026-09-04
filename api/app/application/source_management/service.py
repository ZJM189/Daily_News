from typing import Any
from uuid import UUID

from app.application.identity.dtos import UserDTO
from app.application.source_management.dtos import SourceCredentialDTO, SourceDTO
from app.application.source_management.repositories import SourceManagementRepository
from app.domain.identity.exceptions import PermissionDenied
from app.domain.source_management.exceptions import CredentialNotFound, SourceNotFound
from app.infrastructure.secrets import SecretCipher, mask_secret


class SourceManagementService:
    def __init__(self, repository: SourceManagementRepository, secret_cipher: SecretCipher) -> None:
        self._repository = repository
        self._secret_cipher = secret_cipher

    def list_credentials(
        self,
        *,
        actor: UserDTO,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceCredentialDTO], int]:
        self._require_admin(actor)
        return self._repository.list_credentials(
            source_type=source_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def create_credential(
        self,
        *,
        actor: UserDTO,
        name: str,
        source_type: str,
        secret: str,
        status: str,
    ) -> SourceCredentialDTO:
        self._require_admin(actor)
        return self._repository.create_credential(
            name=name.strip(),
            source_type=source_type,
            encrypted_secret=self._secret_cipher.encrypt(secret),
            secret_masked=mask_secret(secret),
            status=status,
            actor_id=actor.id,
        )

    def update_credential(
        self,
        *,
        actor: UserDTO,
        credential_id: UUID,
        name: str | None,
        secret: str | None,
        secret_provided: bool,
        status: str | None,
    ) -> SourceCredentialDTO:
        self._require_admin(actor)
        encrypted_secret = self._secret_cipher.encrypt(secret) if secret_provided and secret else None
        secret_masked = mask_secret(secret) if secret_provided and secret else None
        credential = self._repository.update_credential(
            credential_id=credential_id,
            name=name.strip() if name is not None else None,
            encrypted_secret=encrypted_secret,
            secret_masked=secret_masked,
            status=status,
            actor_id=actor.id,
        )
        if credential is None:
            raise CredentialNotFound("source credential not found")
        return credential

    def list_sources(
        self,
        *,
        actor: UserDTO,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceDTO], int]:
        self._require_admin(actor)
        return self._repository.list_sources(
            source_type=source_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )

    def create_source(
        self,
        *,
        actor: UserDTO,
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
        self._require_admin(actor)
        self._ensure_credential_exists(credential_id)
        return self._repository.create_source(
            name=name.strip(),
            source_type=source_type,
            status=status,
            url=url.strip() if url else None,
            query_config=query_config,
            credential_id=credential_id,
            credential_env_key=credential_env_key.strip() if credential_env_key else None,
            weight=weight,
            language=language.strip() if language else None,
        )

    def update_source(
        self,
        *,
        actor: UserDTO,
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
    ) -> SourceDTO:
        self._require_admin(actor)
        if credential_id_provided:
            self._ensure_credential_exists(credential_id)
        source = self._repository.update_source(
            source_id=source_id,
            name=name.strip() if name is not None else None,
            status=status,
            url=url.strip() if url else None,
            url_provided=url_provided,
            query_config=query_config,
            credential_id=credential_id,
            credential_id_provided=credential_id_provided,
            credential_env_key=credential_env_key.strip() if credential_env_key else None,
            credential_env_key_provided=credential_env_key_provided,
            weight=weight,
            language=language.strip() if language else None,
            language_provided=language_provided,
        )
        if source is None:
            raise SourceNotFound("source not found")
        return source

    def _ensure_credential_exists(self, credential_id: UUID | None) -> None:
        if credential_id is not None and self._repository.get_credential(credential_id) is None:
            raise CredentialNotFound("source credential not found")

    def _require_admin(self, actor: UserDTO) -> None:
        if actor.role != "admin":
            raise PermissionDenied("admin role required")
