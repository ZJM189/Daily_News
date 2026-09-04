from sqlalchemy.orm import Session

from app.application.digest_publishing.service import (
    DigestQueryService,
    GenerateDigestJobExecutor,
)
from app.infrastructure.digest_publishing.repositories import (
    SqlAlchemyDigestPublishingRepository,
)


def create_generate_digest_job_executor(session: Session) -> GenerateDigestJobExecutor:
    return GenerateDigestJobExecutor(SqlAlchemyDigestPublishingRepository(session))


def create_digest_query_service(session: Session) -> DigestQueryService:
    return DigestQueryService(SqlAlchemyDigestPublishingRepository(session))
