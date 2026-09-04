from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.application.source_management.dtos import SourceCredentialDTO, SourceDTO
from app.application.source_management.repositories import SourceManagementRepository
from app.infrastructure.models import (
    CredentialStatus,
    Source,
    SourceCredential,
    SourceStatus,
    SourceType,
)


class SqlAlchemySourceManagementRepository(SourceManagementRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_credentials(
        self,
        *,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceCredentialDTO], int]:
        conditions = []
        if source_type is not None:
            conditions.append(SourceCredential.source_type == SourceType(source_type))
        if status is not None:
            conditions.append(SourceCredential.status == CredentialStatus(status))
        if keyword:
            conditions.append(SourceCredential.name.ilike(f"%{keyword}%"))

        total_statement = select(func.count()).select_from(SourceCredential)
        list_statement = select(SourceCredential).order_by(SourceCredential.created_at.desc())
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        credentials = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._credential_to_dto(credential) for credential in credentials], total

    def get_credential(self, credential_id: UUID) -> SourceCredentialDTO | None:
        credential = self._session.get(SourceCredential, credential_id)
        return self._credential_to_dto(credential) if credential is not None else None

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
        credential = SourceCredential(
            name=name,
            source_type=SourceType(source_type),
            encrypted_secret=encrypted_secret,
            secret_masked=secret_masked,
            status=CredentialStatus(status),
            created_by=actor_id,
            updated_by=actor_id,
        )
        self._session.add(credential)
        self._session.flush()
        return self._credential_to_dto(credential)

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
        values: dict[str, object] = {"updated_by": actor_id, "updated_at": func.now()}
        if name is not None:
            values["name"] = name
        if encrypted_secret is not None and secret_masked is not None:
            values["encrypted_secret"] = encrypted_secret
            values["secret_masked"] = secret_masked
        if status is not None:
            values["status"] = CredentialStatus(status)

        result = self._session.execute(
            update(SourceCredential).where(SourceCredential.id == credential_id).values(**values)
        )
        if result.rowcount == 0:
            return None
        self._session.flush()
        return self.get_credential(credential_id)

    def list_sources(
        self,
        *,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[SourceDTO], int]:
        conditions = []
        if source_type is not None:
            conditions.append(Source.type == SourceType(source_type))
        if status is not None:
            conditions.append(Source.status == SourceStatus(status))
        if keyword:
            like_keyword = f"%{keyword}%"
            conditions.append(or_(Source.name.ilike(like_keyword), Source.url.ilike(like_keyword)))

        total_statement = select(func.count()).select_from(Source)
        list_statement = select(Source).order_by(Source.created_at.desc())
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        sources = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._source_to_dto(source) for source in sources], total

    def get_source(self, source_id: UUID) -> SourceDTO | None:
        source = self._session.get(Source, source_id)
        return self._source_to_dto(source) if source is not None else None

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
        source = Source(
            name=name,
            type=SourceType(source_type),
            status=SourceStatus(status),
            url=url,
            query_config=query_config,
            credential_id=credential_id,
            credential_env_key=credential_env_key,
            weight=weight,
            language=language,
        )
        self._session.add(source)
        self._session.flush()
        return self._source_to_dto(source)

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
        values: dict[str, object] = {"updated_at": func.now()}
        if name is not None:
            values["name"] = name
        if status is not None:
            values["status"] = SourceStatus(status)
        if url_provided:
            values["url"] = url
        if query_config is not None:
            values["query_config"] = query_config
        if credential_id_provided:
            values["credential_id"] = credential_id
        if credential_env_key_provided:
            values["credential_env_key"] = credential_env_key
        if weight is not None:
            values["weight"] = weight
        if language_provided:
            values["language"] = language

        result = self._session.execute(update(Source).where(Source.id == source_id).values(**values))
        if result.rowcount == 0:
            return None
        self._session.flush()
        return self.get_source(source_id)

    def _credential_to_dto(self, credential: SourceCredential) -> SourceCredentialDTO:
        return SourceCredentialDTO(
            id=credential.id,
            name=credential.name,
            source_type=str(
                credential.source_type.value
                if hasattr(credential.source_type, "value")
                else credential.source_type
            ),
            secret_masked=credential.secret_masked,
            status=str(
                credential.status.value if hasattr(credential.status, "value") else credential.status
            ),
            last_test_at=credential.last_test_at,
            last_test_status=credential.last_test_status,
            last_test_error=credential.last_test_error,
            created_at=credential.created_at,
            updated_at=credential.updated_at,
        )

    def _source_to_dto(self, source: Source) -> SourceDTO:
        return SourceDTO(
            id=source.id,
            name=source.name,
            type=str(source.type.value if hasattr(source.type, "value") else source.type),
            status=str(source.status.value if hasattr(source.status, "value") else source.status),
            url=source.url,
            query_config=source.query_config,
            credential_id=source.credential_id,
            credential_env_key=source.credential_env_key,
            weight=source.weight,
            language=source.language,
            last_fetched_at=source.last_fetched_at,
            last_success_at=source.last_success_at,
            last_error=source.last_error,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )
