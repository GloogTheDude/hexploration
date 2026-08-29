from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import ExpeditionStatus, KnowledgeRecall, WikiPage, WikiRevision
from repositories.expedition_repository import ExpeditionRepository
from repositories.wiki_repository import WikiRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


DEFAULT_RECALL_LIMIT_PER_CHARACTER = 3


@dataclass(frozen=True)
class RecallPageState:
    recall: KnowledgeRecall
    page: WikiPage
    revision: WikiRevision


@dataclass(frozen=True)
class RecallStatus:
    character_id: int
    expedition_id: int
    limit: int
    used: int
    remaining: int
    knowledge_cutoff_game_minute: int


class RecallService:
    """Temporal hub-knowledge recall for characters who are away from the hub.

    A character may unlock a limited number of wiki pages while an expedition is
    ACTIVE. The page is resolved against the campaign wiki as it existed when the
    expedition departed, never against later hub revisions. Once recalled, that
    exact temporal page remains available to the whole expedition.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.expeditions = ExpeditionRepository(db)
        self.wiki = WikiRepository(db)

    @staticmethod
    def _normalize_query(query: str) -> str:
        return query.strip().lower()

    def _active_expedition(self, expedition_id: int):
        expedition = self.expeditions.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Knowledge recall is only available during an active expedition")
        return expedition

    def _active_participant(self, expedition_id: int, character_id: int):
        participant = self.expeditions.get_participant(expedition_id, character_id)
        if participant is None:
            raise ForbiddenOperationError("Character is not part of this expedition")
        if participant.left_game_minute is not None:
            raise ForbiddenOperationError("Character is no longer active in this expedition")
        return participant

    def status(self, expedition_id: int, character_id: int) -> RecallStatus:
        expedition = self._active_expedition(expedition_id)
        self._active_participant(expedition_id, character_id)
        used = self.wiki.count_recalls_for_character(expedition_id, character_id)
        return RecallStatus(
            character_id=character_id,
            expedition_id=expedition_id,
            limit=DEFAULT_RECALL_LIMIT_PER_CHARACTER,
            used=used,
            remaining=max(DEFAULT_RECALL_LIMIT_PER_CHARACTER - used, 0),
            knowledge_cutoff_game_minute=expedition.start_game_minute,
        )

    def search_available(
        self,
        expedition_id: int,
        character_id: int,
        query: str,
    ) -> list[tuple[WikiPage, WikiRevision]]:
        expedition = self._active_expedition(expedition_id)
        self._active_participant(expedition_id, character_id)

        needle = self._normalize_query(query)
        if not needle:
            raise ValueError("query cannot be empty")

        matches: list[tuple[WikiPage, WikiRevision]] = []
        for page in self.wiki.list_pages(expedition.campaign_id):
            revision = self.wiki.latest_revision(
                page.id,
                as_of_game_minute=expedition.start_game_minute,
            )
            if revision is None:
                continue
            haystack = " ".join(
                value
                for value in (page.title, page.slug, page.category or "")
                if value
            ).lower()
            if needle in haystack:
                matches.append((page, revision))
        return matches

    def recall_page(
        self,
        expedition_id: int,
        character_id: int,
        page_id: int,
    ) -> RecallPageState:
        expedition = self._active_expedition(expedition_id)
        self._active_participant(expedition_id, character_id)

        page = self.wiki.get_page(page_id)
        if page is None:
            raise NotFoundError("Wiki page not found")
        if page.campaign_id != expedition.campaign_id:
            raise ForbiddenOperationError("Wiki page belongs to another campaign")

        existing = self.wiki.get_recall(
            expedition_id=expedition_id,
            character_id=character_id,
            page_id=page_id,
        )
        if existing is not None:
            revision = self.wiki.latest_revision(
                page.id,
                as_of_game_minute=existing.knowledge_cutoff_game_minute,
            )
            if revision is None:
                raise NotFoundError("Recalled wiki page is no longer resolvable")
            return RecallPageState(existing, page, revision)

        # If another member already recalled the page, it is shared with the whole
        # expedition and does not consume another character's recall slot.
        shared = self.wiki.get_any_recall_for_page(expedition_id, page_id)
        if shared is not None:
            revision = self.wiki.latest_revision(
                page.id,
                as_of_game_minute=shared.knowledge_cutoff_game_minute,
            )
            if revision is None:
                raise NotFoundError("Recalled wiki page is no longer resolvable")
            return RecallPageState(shared, page, revision)

        status = self.status(expedition_id, character_id)
        if status.remaining <= 0:
            raise ConflictError("Character has no knowledge recalls remaining")

        revision = self.wiki.latest_revision(
            page.id,
            as_of_game_minute=expedition.start_game_minute,
        )
        if revision is None:
            raise NotFoundError("Wiki page was not known at expedition departure")

        recall = self.wiki.add_recall(
            KnowledgeRecall(
                expedition_id=expedition.id,
                character_id=character_id,
                page_id=page.id,
                knowledge_cutoff_game_minute=expedition.start_game_minute,
                recalled_at_game_minute=expedition.current_game_minute,
            )
        )
        self.db.commit()
        self.db.refresh(recall)
        return RecallPageState(recall, page, revision)

    def list_unlocked(self, expedition_id: int) -> list[RecallPageState]:
        expedition = self.expeditions.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        states: list[RecallPageState] = []
        seen_pages: set[int] = set()
        for recall in self.wiki.list_recalls_for_expedition(expedition_id):
            if recall.page_id in seen_pages:
                continue
            page = self.wiki.get_page(recall.page_id)
            if page is None:
                continue
            revision = self.wiki.latest_revision(
                page.id,
                as_of_game_minute=recall.knowledge_cutoff_game_minute,
            )
            if revision is None:
                continue
            states.append(RecallPageState(recall, page, revision))
            seen_pages.add(recall.page_id)
        return states
