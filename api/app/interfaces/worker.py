import logging
import time

from app.infrastructure.config import get_settings
from app.infrastructure.digest_publishing.factory import create_generate_digest_job_executor
from app.infrastructure.ingestion.factory import (
    create_collect_job_executor,
    create_normalize_job_executor,
    create_rank_job_executor,
    create_summarize_job_executor,
    create_topic_aggregation_job_executor,
)
from app.infrastructure.persistence import get_session_factory


logger = logging.getLogger("daily_news.worker")


def run_once() -> bool:
    session = get_session_factory()()
    try:
        result = create_collect_job_executor(session).run_next_collect_job()
        if result is not None:
            logger.info("completed collect job: %s", result)
        if result is None:
            result = create_normalize_job_executor(session).run_next_normalize_job()
            if result is not None:
                logger.info("completed normalize job: %s", result)
        if result is None:
            result = create_rank_job_executor(session).run_next_rank_job()
            if result is not None:
                logger.info("completed rank job: %s", result)
        if result is None:
            result = create_topic_aggregation_job_executor(
                session
            ).run_next_topic_aggregation_job()
            if result is not None:
                logger.info("completed dedupe job: %s", result)
        if result is None:
            result = create_summarize_job_executor(session).run_next_summarize_job()
            if result is not None:
                logger.info("completed summarize job: %s", result)
        if result is None:
            result = create_generate_digest_job_executor(session).run_next_generate_digest_job()
            if result is not None:
                logger.info("completed generate_digest job: %s", result)
        session.commit()
        return result is not None
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("worker poll failed; retrying")
        time.sleep(max(settings.worker_poll_interval_seconds, 1))


if __name__ == "__main__":
    main()
