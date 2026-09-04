from datetime import UTC, datetime

import typer

from app.application.identity.passwords import PasswordService
from app.application.identity.service import IdentityService
from app.application.job_operations.service import JobOperationsService
from app.domain.identity.exceptions import (
    AdminAlreadyInitialized,
    InvalidPassword,
    UserAlreadyExists,
)
from app.infrastructure.config import get_settings
from app.infrastructure.digest_publishing.factory import create_generate_digest_job_executor
from app.infrastructure.identity.repositories import SqlAlchemyIdentityRepository
from app.infrastructure.ingestion.factory import (
    create_collect_job_executor,
    create_normalize_job_executor,
    create_rank_job_executor,
    create_summarize_job_executor,
    create_topic_aggregation_job_executor,
)
from app.infrastructure.job_operations.repositories import SqlAlchemyJobOperationsRepository
from app.infrastructure.models import Source, SourceStatus, SourceType
from app.infrastructure.persistence import get_session_factory

app = typer.Typer(help="Daily News backend management commands.")


@app.callback()
def main() -> None:
    """Daily News backend management commands."""


@app.command("create-admin")
def create_admin(
    username: str = typer.Option(..., prompt=True),
    email: str | None = typer.Option(None),
    display_name: str | None = typer.Option(None),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Create the first administrator account."""
    session = get_session_factory()()
    try:
        service = IdentityService(
            SqlAlchemyIdentityRepository(session),
            PasswordService(),
            session_ttl_hours=get_settings().session_ttl_hours,
        )
        user = service.create_first_admin(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
        )
        session.commit()
    except AdminAlreadyInitialized:
        session.rollback()
        raise typer.BadParameter("admin already initialized") from None
    except UserAlreadyExists:
        session.rollback()
        raise typer.BadParameter("username or email already exists") from None
    except InvalidPassword as exc:
        session.rollback()
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()

    typer.echo(f"admin user created: {user.username}")


@app.command("reset-password")
def reset_password(
    login: str = typer.Argument(..., help="Username or email of the user to reset."),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Reset a user password from the server CLI."""
    session = get_session_factory()()
    try:
        repository = SqlAlchemyIdentityRepository(session)
        user = repository.get_user_by_login(login)
        if user is None:
            raise typer.BadParameter("user not found")

        password_hash = PasswordService().hash_password(password)
        repository.update_password(user_id=user.id, password_hash=password_hash)
        repository.revoke_user_sessions(user.id, datetime.now(UTC))
        session.commit()
    except InvalidPassword as exc:
        session.rollback()
        raise typer.BadParameter(str(exc)) from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    typer.echo(f"password reset: {user.username}")


@app.command("init-scheduler-configs")
def init_scheduler_configs() -> None:
    """Ensure default scheduler configs exist."""
    session = get_session_factory()()
    try:
        service = JobOperationsService(SqlAlchemyJobOperationsRepository(session))
        configs = service.ensure_default_scheduler_configs()
        session.commit()
    finally:
        session.close()

    typer.echo(f"scheduler configs ready: {len(configs)}")


@app.command("seed-default-sources")
def seed_default_sources() -> None:
    """Ensure default RSS sources exist."""
    default_sources = [
        {
            "name": "OpenAI News",
            "url": "https://openai.com/news/rss.xml",
            "weight": 95,
        },
        {
            "name": "Google DeepMind Blog",
            "url": "https://deepmind.google/blog/feed/basic/",
            "weight": 90,
        },
        {
            "name": "arXiv Computer Science",
            "url": "https://rss.arxiv.org/rss/cs",
            "weight": 88,
        },
        {
            "name": "量子位",
            "url": "https://www.qbitai.com/feed",
            "weight": 84,
            "language": "zh",
        },
        {
            "name": "InfoQ 中文",
            "url": "https://www.infoq.cn/feed",
            "weight": 82,
            "language": "zh",
        },
        {
            "name": "Hugging Face Blog",
            "url": "https://huggingface.co/blog/feed.xml",
            "weight": 85,
        },
    ]

    session = get_session_factory()()
    created_count = 0
    try:
        for item in default_sources:
            existing = (
                session.query(Source)
                .filter(Source.type == SourceType.RSS, Source.url == item["url"])
                .first()
            )
            if existing is not None:
                continue
            session.add(
                Source(
                    name=item["name"],
                    type=SourceType.RSS,
                    status=SourceStatus.ENABLED,
                    url=item["url"],
                    query_config={},
                    weight=item["weight"],
                    language=item.get("language", "en"),
                )
            )
            created_count += 1
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    typer.echo(f"default sources ready, created: {created_count}")


@app.command("worker-once")
def worker_once() -> None:
    """Run one pending collect or normalize job if available."""
    session = get_session_factory()()
    try:
        result = create_collect_job_executor(session).run_next_collect_job()
        job_label = "collect"
        if result is None:
            result = create_normalize_job_executor(session).run_next_normalize_job()
            job_label = "normalize"
        if result is None:
            result = create_rank_job_executor(session).run_next_rank_job()
            job_label = "rank"
        if result is None:
            result = create_topic_aggregation_job_executor(
                session
            ).run_next_topic_aggregation_job()
            job_label = "dedupe"
        if result is None:
            result = create_summarize_job_executor(session).run_next_summarize_job()
            job_label = "summarize"
        if result is None:
            result = create_generate_digest_job_executor(session).run_next_generate_digest_job()
            job_label = "generate_digest"
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    if result is None:
        typer.echo("no pending collect, normalize, rank, dedupe, summarize, or generate_digest job")
        return
    typer.echo(
        f"{job_label} job finished: "
        f"{result.job_run_id} total={result.total_count} "
        f"success={result.success_count} failed={result.failure_count}"
    )


if __name__ == "__main__":
    app()
