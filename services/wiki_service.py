from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from db.models import (
    CharacterKnowledgeObservation,
    ExpeditionReport,
    ExpeditionStatus,
    WikiPage,
    WikiRevision,
)
from dto.wiki_dto import ExpeditionReportCreate
from repositories.campaign_repository import CampaignRepository
from repositories.expedition_repository import ExpeditionRepository
from repositories.knowledge_repository import KnowledgeRepository
from repositories.wiki_repository import WikiRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


class WikiService:
    """Publish expedition knowledge into temporal campaign hub knowledge.

    CharacterKnowledgeObservation remains private/expedition knowledge. A returned
    expedition can publish one report. The latest observation per target from that
    expedition is projected into a campaign wiki revision whose effective minute is
    the expedition's in-world return minute.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = WikiRepository(db)
        self.knowledge = KnowledgeRepository(db)
        self.expeditions = ExpeditionRepository(db)
        self.campaigns = CampaignRepository(db)

    @staticmethod
    def _latest_by_target(
        observations: Iterable[CharacterKnowledgeObservation],
    ) -> list[CharacterKnowledgeObservation]:
        latest: dict[tuple[str, int], CharacterKnowledgeObservation] = {}
        for observation in observations:
            key = (observation.target_type, observation.target_id)
            previous = latest.get(key)
            if previous is None or (
                observation.observed_game_minute,
                observation.id,
            ) > (
                previous.observed_game_minute,
                previous.id,
            ):
                latest[key] = observation
        return sorted(
            latest.values(),
            key=lambda item: (item.target_type, item.target_id),
        )

    @staticmethod
    def _poi_page_content(observation: CharacterKnowledgeObservation) -> str:
        data = observation.knowledge
        lines = [f"# {data.get('name') or f'POI #{observation.target_id}'}"]
        if data.get("kind"):
            lines.append(f"- Type: {data['kind']}")
        if data.get("state"):
            lines.append(f"- État observé: {data['state']}")
        if "exists" in data:
            lines.append(f"- Existe: {'oui' if data['exists'] else 'non'}")
        if data.get("q") is not None and data.get("r") is not None:
            lines.append(f"- Coordonnées: ({data['q']}, {data['r']})")
        lines.append(f"- Observation: minute {observation.observed_game_minute}")
        return "\n".join(lines)

    def _publish_observation(
        self,
        *,
        campaign_id: int,
        report: ExpeditionReport,
        observation: CharacterKnowledgeObservation,
    ) -> tuple[WikiPage, WikiRevision] | None:
        # v10 intentionally only projects POI knowledge. The model is generic so
        # future target types can add dedicated renderers without changing schema.
        if observation.target_type != "POI":
            return None

        slug = f"poi-{observation.target_id}"
        title = observation.knowledge.get("name") or f"POI #{observation.target_id}"
        page = self.repo.get_page_by_slug(campaign_id, slug)
        if page is None:
            page = self.repo.add_page(
                WikiPage(
                    campaign_id=campaign_id,
                    slug=slug,
                    title=title,
                    category="POI",
                )
            )
        else:
            page.title = title

        revision = self.repo.add_revision(
            WikiRevision(
                page_id=page.id,
                revision=self.repo.next_revision_number(page.id),
                effective_from_game_minute=report.published_game_minute,
                source_report_id=report.id,
                content=self._poi_page_content(observation),
            )
        )
        return page, revision

    def publish_expedition_report(
        self,
        expedition_id: int,
        data: ExpeditionReportCreate,
    ) -> tuple[ExpeditionReport, list[tuple[WikiPage, WikiRevision]]]:
        expedition = self.expeditions.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.status != ExpeditionStatus.RETURNED:
            raise ConflictError("Only a returned expedition can publish a report")
        if expedition.return_game_minute is None:
            raise ConflictError("Returned expedition has no return game minute")
        if self.repo.get_report_for_expedition(expedition_id) is not None:
            raise ConflictError("Expedition already has a published report")

        title = data.title.strip()
        content = data.content.strip()
        if not title:
            raise ValueError("title cannot be empty")
        if not content:
            raise ValueError("content cannot be empty")

        report = self.repo.add_report(
            ExpeditionReport(
                expedition_id=expedition.id,
                published_game_minute=expedition.return_game_minute,
                title=title,
                content=content,
            )
        )

        published: list[tuple[WikiPage, WikiRevision]] = []
        if data.publish_knowledge:
            observations = self.knowledge.list_for_expedition(expedition.id)
            for observation in self._latest_by_target(observations):
                projection = self._publish_observation(
                    campaign_id=expedition.campaign_id,
                    report=report,
                    observation=observation,
                )
                if projection is not None:
                    published.append(projection)

        self.db.commit()
        self.db.refresh(report)
        for page, revision in published:
            self.db.refresh(page)
            self.db.refresh(revision)
        return report, published

    def get_expedition_report(self, expedition_id: int) -> ExpeditionReport:
        if self.expeditions.get(expedition_id) is None:
            raise NotFoundError("Expedition not found")
        report = self.repo.get_report_for_expedition(expedition_id)
        if report is None:
            raise NotFoundError("Expedition report not found")
        return report

    def get_page_state(
        self,
        page_id: int,
        *,
        campaign_id: int | None = None,
        as_of_game_minute: int | None = None,
    ) -> tuple[WikiPage, WikiRevision]:
        if as_of_game_minute is not None and as_of_game_minute < 0:
            raise ValueError("as_of_game_minute must be >= 0")
        page = self.repo.get_page(page_id)
        if page is None:
            raise NotFoundError("Wiki page not found")
        if campaign_id is not None and page.campaign_id != campaign_id:
            raise ForbiddenOperationError("Wiki page belongs to another campaign")
        revision = self.repo.latest_revision(
            page.id,
            as_of_game_minute=as_of_game_minute,
        )
        if revision is None:
            raise NotFoundError("Wiki page was not available at this game minute")
        return page, revision

    def list_campaign_wiki(
        self,
        campaign_id: int,
        *,
        as_of_game_minute: int | None = None,
    ) -> list[tuple[WikiPage, WikiRevision]]:
        if as_of_game_minute is not None and as_of_game_minute < 0:
            raise ValueError("as_of_game_minute must be >= 0")
        if self.campaigns.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")

        states: list[tuple[WikiPage, WikiRevision]] = []
        for page in self.repo.list_pages(campaign_id):
            revision = self.repo.latest_revision(
                page.id,
                as_of_game_minute=as_of_game_minute,
            )
            if revision is not None:
                states.append((page, revision))
        return states
