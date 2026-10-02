from sqlalchemy.orm import Session

from app.application.decision.item import ItemDecisionService
from app.application.ingestion.collectors import CollectorRegistry
from app.application.ingestion.service import (
    CollectJobExecutor,
    NormalizeJobExecutor,
    RankJobExecutor,
)
from app.application.ingestion.summarization import SummarizeJobExecutor
from app.application.ingestion.topic_aggregation import TopicAggregationJobExecutor
from app.infrastructure.config import get_settings
from app.infrastructure.ingestion.external_collectors import (
    ArxivCollector,
    GitHubCollector,
    HackerNewsCollector,
    HuggingFaceCollector,
    ProductHuntCollector,
)
from app.infrastructure.ingestion.openai_compatible import (
    OpenAICompatibleSummarizationClient,
    OpenAICompatibleTopicAggregationClient,
)
from app.infrastructure.ingestion.repositories import SqlAlchemyIngestionRepository
from app.infrastructure.ingestion.rss import RSSCollector
from app.infrastructure.typesafe_jev.factory import create_jev_client


def create_collect_job_executor(session: Session) -> CollectJobExecutor:
    return CollectJobExecutor(
        SqlAlchemyIngestionRepository(session),
        CollectorRegistry(
            [
                RSSCollector(),
                HackerNewsCollector(),
                GitHubCollector(),
                ArxivCollector(),
                ProductHuntCollector(),
                HuggingFaceCollector(),
            ]
        ),
    )


def create_normalize_job_executor(session: Session) -> NormalizeJobExecutor:
    return NormalizeJobExecutor(SqlAlchemyIngestionRepository(session))


def create_rank_job_executor(session: Session) -> RankJobExecutor:
    settings = get_settings()
    decision_client = create_jev_client(settings) if settings.jev_item_decision_enabled else None
    return RankJobExecutor(
        SqlAlchemyIngestionRepository(session),
        decision_service=ItemDecisionService(decision_client),
        jev_score_weight=settings.jev_score_weight,
        jev_item_limit=settings.jev_item_limit,
    )


def create_topic_aggregation_job_executor(session: Session) -> TopicAggregationJobExecutor:
    return TopicAggregationJobExecutor(
        SqlAlchemyIngestionRepository(session),
        OpenAICompatibleTopicAggregationClient(),
    )


def create_summarize_job_executor(session: Session) -> SummarizeJobExecutor:
    return SummarizeJobExecutor(
        SqlAlchemyIngestionRepository(session),
        OpenAICompatibleSummarizationClient(),
    )
