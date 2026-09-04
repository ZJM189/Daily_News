from collections import defaultdict
from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, aliased

from app.application.digest_publishing.dtos import (
    DigestCandidateDTO,
    DigestDetailDTO,
    DigestDTO,
    DigestItemDTO,
)
from app.application.digest_publishing.repositories import DigestPublishingRepository
from app.infrastructure.models import (
    CategoryCode,
    Digest,
    DigestItem,
    DigestStatus,
    Item,
    JobRun,
    JobStatus,
    JobType,
    Source,
    Topic,
    TopicItem,
)


class SqlAlchemyDigestPublishingRepository(DigestPublishingRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def claim_next_generate_digest_job(self) -> UUID | None:
        return self._session.scalar(
            select(JobRun.id)
            .where(JobRun.job_type == JobType.GENERATE_DIGEST, JobRun.status == JobStatus.PENDING)
            .order_by(JobRun.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

    def mark_job_running(self, job_run_id: UUID, started_at: datetime) -> None:
        self._session.execute(
            update(JobRun)
            .where(JobRun.id == job_run_id)
            .values(status=JobStatus.RUNNING, started_at=started_at)
        )
        self._session.flush()

    def mark_job_finished(
        self,
        *,
        job_run_id: UUID,
        status: str,
        total_count: int,
        success_count: int,
        failure_count: int,
        error_message: str | None,
        ended_at: datetime,
    ) -> None:
        self._session.execute(
            update(JobRun)
            .where(JobRun.id == job_run_id)
            .values(
                status=JobStatus(status),
                total_count=total_count,
                success_count=success_count,
                failure_count=failure_count,
                error_message=error_message,
                ended_at=ended_at,
            )
        )
        self._session.flush()

    def get_job_params(self, job_run_id: UUID) -> dict[str, object]:
        params = self._session.scalar(select(JobRun.params).where(JobRun.id == job_run_id))
        return params if isinstance(params, dict) else {}

    def list_digest_topic_candidates(
        self,
        *,
        digest_date: date,
        start_at: datetime,
        end_at: datetime,
        limit: int,
        exclude_recent_digest_days: int,
    ) -> list[DigestCandidateDTO]:
        primary_item = aliased(Item)
        primary_source = aliased(Source)
        query = (
            select(
                Topic.id.label("topic_id"),
                func.max(Item.collected_at).label("last_collected_at"),
            )
            .select_from(Topic)
            .join(TopicItem, TopicItem.topic_id == Topic.id)
            .join(Item, Item.id == TopicItem.item_id)
            .where(Item.collected_at >= start_at, Item.collected_at < end_at)
            .group_by(Topic.id)
        )

        if exclude_recent_digest_days > 0:
            recent_cutoff = digest_date - timedelta(days=exclude_recent_digest_days)
            recent_topic_ids = (
                select(DigestItem.topic_id)
                .join(Digest, Digest.id == DigestItem.digest_id)
                .where(
                    Digest.digest_date >= recent_cutoff,
                    Digest.digest_date <= digest_date,
                    DigestItem.topic_id.isnot(None),
                )
                .distinct()
            )
            query = query.where(~Topic.id.in_(recent_topic_ids))

        topic_activity = query.subquery()
        rows = self._session.execute(
            select(Topic, primary_item, primary_source, primary_item.source_id)
            .add_columns(topic_activity.c.last_collected_at)
            .join(topic_activity, Topic.id == topic_activity.c.topic_id)
            .outerjoin(primary_item, primary_item.id == Topic.primary_item_id)
            .outerjoin(primary_source, primary_source.id == primary_item.source_id)
            .order_by(
                Topic.score.desc(),
                topic_activity.c.last_collected_at.desc(),
            )
        ).all()
        candidates = [
            (
                self._topic_to_candidate(topic, primary_item_row, primary_source_row),
                source_id,
                last_collected_at,
            )
            for topic, primary_item_row, primary_source_row, source_id, last_collected_at in rows
        ]
        return select_evenly_by_source(candidates, limit=limit)

    def create_published_digest(
        self,
        *,
        digest_date: date,
        title: str,
        overview_zh: str,
        stats: dict[str, object],
        job_run_id: UUID,
        candidates: list[DigestCandidateDTO],
        generated_at: datetime,
    ) -> DigestDTO:
        version = self._next_version(digest_date)
        digest = Digest(
            digest_date=digest_date,
            version=version,
            status=DigestStatus.PUBLISHED,
            title=title,
            overview_zh=overview_zh,
            stats=stats,
            job_run_id=job_run_id,
            generated_at=generated_at,
            published_at=generated_at,
        )
        self._session.add(digest)
        self._session.flush()

        for rank, candidate in enumerate(candidates, start=1):
            self._session.add(
                DigestItem(
                    digest_id=digest.id,
                    item_id=None,
                    topic_id=candidate.topic_id,
                    item_type="topic",
                    rank=rank,
                    score_snapshot=candidate.score,
                    title_snapshot=candidate.title,
                    summary_snapshot_zh=candidate.summary_zh,
                    importance_snapshot_zh=candidate.importance_zh,
                    category_snapshot=CategoryCode(candidate.category),
                    source_snapshot={
                        "source_count": candidate.source_count,
                        "primary_item_id": str(candidate.primary_item_id)
                        if candidate.primary_item_id
                        else None,
                        "primary_source_type": candidate.primary_source_type,
                        "primary_source_name": candidate.primary_source_name,
                        "primary_url": candidate.primary_url,
                        "canonical_url": candidate.canonical_url,
                    },
                )
            )
        self._session.flush()
        return self._digest_to_dto(digest)

    def get_published_digest(
        self,
        *,
        digest_date: date,
        version: int | None,
    ) -> DigestDetailDTO | None:
        conditions = [Digest.digest_date == digest_date, Digest.status == DigestStatus.PUBLISHED]
        if version is not None:
            conditions.append(Digest.version == version)
        digest = self._session.scalar(
            select(Digest).where(*conditions).order_by(Digest.version.desc()).limit(1)
        )
        if digest is None:
            return None

        items = self._session.scalars(
            select(DigestItem)
            .where(DigestItem.digest_id == digest.id)
            .order_by(DigestItem.rank.asc())
        ).all()
        return DigestDetailDTO(
            digest=self._digest_to_dto(digest),
            items=[self._digest_item_to_dto(item) for item in items],
        )

    def _next_version(self, digest_date: date) -> int:
        current_version = self._session.scalar(
            select(func.max(Digest.version)).where(Digest.digest_date == digest_date)
        )
        return int(current_version or 0) + 1

    def _topic_to_candidate(
        self,
        topic: Topic,
        primary_item: Item | None,
        primary_source: Source | None = None,
    ) -> DigestCandidateDTO:
        return DigestCandidateDTO(
            topic_id=topic.id,
            title=topic.title,
            summary_zh=topic.summary_zh or (primary_item.summary_zh if primary_item else None),
            importance_zh=topic.importance_zh
            or (primary_item.importance_zh if primary_item else None),
            category=str(topic.category.value if hasattr(topic.category, "value") else topic.category),
            score=topic.score,
            source_count=topic.source_count,
            primary_item_id=topic.primary_item_id,
            primary_source_type=str(
                primary_source.type.value if hasattr(primary_source.type, "value") else primary_source.type
            )
            if primary_source is not None
            else None,
            primary_source_name=primary_source.name if primary_source is not None else None,
            primary_url=primary_item.url if primary_item is not None else None,
            canonical_url=primary_item.canonical_url if primary_item is not None else None,
        )

    def _digest_to_dto(self, digest: Digest) -> DigestDTO:
        return DigestDTO(
            id=digest.id,
            digest_date=digest.digest_date,
            version=digest.version,
            status=str(digest.status.value if hasattr(digest.status, "value") else digest.status),
            title=digest.title,
            overview_zh=digest.overview_zh,
            stats=digest.stats,
            job_run_id=digest.job_run_id,
            generated_at=digest.generated_at,
            published_at=digest.published_at,
            created_at=digest.created_at,
        )

    def _digest_item_to_dto(self, item: DigestItem) -> DigestItemDTO:
        return DigestItemDTO(
            id=item.id,
            item_id=item.item_id,
            topic_id=item.topic_id,
            item_type=item.item_type,
            rank=item.rank,
            score_snapshot=item.score_snapshot,
            title_snapshot=item.title_snapshot,
            summary_snapshot_zh=item.summary_snapshot_zh,
            importance_snapshot_zh=item.importance_snapshot_zh,
            category_snapshot=str(
                item.category_snapshot.value
                if hasattr(item.category_snapshot, "value")
                else item.category_snapshot
            ),
            source_snapshot=item.source_snapshot,
            created_at=item.created_at,
        )


def select_evenly_by_source(
    candidates: list[tuple[DigestCandidateDTO, UUID | None, datetime]],
    *,
    limit: int,
) -> list[DigestCandidateDTO]:
    if limit <= 0 or not candidates:
        return []

    grouped: dict[UUID | None, list[tuple[DigestCandidateDTO, datetime]]] = defaultdict(list)
    for candidate, source_id, last_collected_at in candidates:
        grouped[source_id].append((candidate, last_collected_at))

    for source_candidates in grouped.values():
        source_candidates.sort(key=_digest_candidate_sort_key, reverse=True)

    ordered_source_ids = sorted(
        grouped,
        key=lambda source_id: _digest_candidate_sort_key(grouped[source_id][0]),
        reverse=True,
    )

    selected: list[DigestCandidateDTO] = []
    round_index = 0
    while len(selected) < limit:
        appended = False
        for source_id in ordered_source_ids:
            source_candidates = grouped[source_id]
            if round_index >= len(source_candidates):
                continue
            selected.append(source_candidates[round_index][0])
            appended = True
            if len(selected) >= limit:
                break
        if not appended:
            break
        round_index += 1

    return selected


def _digest_candidate_sort_key(
    candidate_with_time: tuple[DigestCandidateDTO, datetime],
) -> tuple[float, datetime, str]:
    candidate, last_collected_at = candidate_with_time
    return float(candidate.score), last_collected_at, str(candidate.topic_id)
