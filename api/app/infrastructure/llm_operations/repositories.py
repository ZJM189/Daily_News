from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.llm_operations.dtos import LLMProviderDTO
from app.application.llm_operations.repositories import LLMProviderRepository
from app.infrastructure.models import LLMProvider, LLMProviderType


class SqlAlchemyLLMProviderRepository(LLMProviderRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_providers(
        self,
        *,
        enabled: bool | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[LLMProviderDTO], int]:
        conditions = []
        if enabled is not None:
            conditions.append(LLMProvider.enabled == enabled)
        if keyword:
            conditions.append(LLMProvider.name.ilike(f"%{keyword}%"))

        total_statement = select(func.count()).select_from(LLMProvider)
        list_statement = select(LLMProvider).order_by(
            LLMProvider.is_default.desc(), LLMProvider.created_at.desc()
        )
        if conditions:
            total_statement = total_statement.where(*conditions)
            list_statement = list_statement.where(*conditions)

        total = self._session.scalar(total_statement) or 0
        providers = self._session.scalars(
            list_statement.offset((page - 1) * page_size).limit(page_size)
        ).all()
        return [self._to_dto(provider) for provider in providers], total

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
        if is_default:
            self._clear_default()
        provider = LLMProvider(
            name=name,
            type=LLMProviderType(provider_type),
            base_url=base_url,
            model=model,
            encrypted_api_key=encrypted_api_key,
            api_key_masked=api_key_masked,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            enabled=enabled,
            is_default=is_default,
        )
        self._session.add(provider)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError("llm provider already exists") from exc
        return self._to_dto(provider)

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
        values: dict[str, object] = {"updated_at": func.now()}
        if name is not None:
            values["name"] = name
        if base_url is not None:
            values["base_url"] = base_url
        if model is not None:
            values["model"] = model
        if api_key_provided:
            values["encrypted_api_key"] = encrypted_api_key
            values["api_key_masked"] = api_key_masked
        if timeout_seconds is not None:
            values["timeout_seconds"] = timeout_seconds
        if retry_count is not None:
            values["retry_count"] = retry_count
        if enabled is not None:
            values["enabled"] = enabled
        if is_default is not None:
            values["is_default"] = is_default
            if is_default:
                self._clear_default(except_provider_id=provider_id)

        try:
            result = self._session.execute(
                update(LLMProvider).where(LLMProvider.id == provider_id).values(**values)
            )
            if result.rowcount == 0:
                return None
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise ValueError("llm provider already exists") from exc
        return self._get(provider_id)

    def set_default_provider(self, provider_id: UUID) -> LLMProviderDTO | None:
        if self._get(provider_id) is None:
            return None
        self._clear_default(except_provider_id=provider_id)
        self._session.execute(
            update(LLMProvider)
            .where(LLMProvider.id == provider_id)
            .values(is_default=True, updated_at=func.now())
        )
        self._session.flush()
        return self._get(provider_id)

    def _clear_default(self, except_provider_id: UUID | None = None) -> None:
        statement = update(LLMProvider).where(LLMProvider.is_default.is_(True))
        if except_provider_id is not None:
            statement = statement.where(LLMProvider.id != except_provider_id)
        self._session.execute(statement.values(is_default=False, updated_at=func.now()))

    def _get(self, provider_id: UUID) -> LLMProviderDTO | None:
        provider = self._session.get(LLMProvider, provider_id)
        return self._to_dto(provider) if provider is not None else None

    def _to_dto(self, provider: LLMProvider) -> LLMProviderDTO:
        return LLMProviderDTO(
            id=provider.id,
            name=provider.name,
            type=str(provider.type.value if hasattr(provider.type, "value") else provider.type),
            base_url=provider.base_url,
            model=provider.model,
            api_key_masked=provider.api_key_masked,
            timeout_seconds=provider.timeout_seconds,
            retry_count=provider.retry_count,
            enabled=provider.enabled,
            is_default=provider.is_default,
            last_test_at=provider.last_test_at,
            last_test_status=provider.last_test_status,
            last_test_error=provider.last_test_error,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )
