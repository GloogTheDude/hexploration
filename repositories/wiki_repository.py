from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import ExpeditionReport, KnowledgeRecall, WikiPage, WikiRevision


class WikiRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_report_for_expedition(self, expedition_id: int) -> ExpeditionReport | None:
        stmt = select(ExpeditionReport).where(
            ExpeditionReport.expedition_id == expedition_id
        )
        return self.db.scalar(stmt)

    def add_report(self, report: ExpeditionReport) -> ExpeditionReport:
        self.db.add(report)
        self.db.flush()
        return report

    def get_page(self, page_id: int) -> WikiPage | None:
        return self.db.get(WikiPage, page_id)

    def get_page_by_slug(self, campaign_id: int, slug: str) -> WikiPage | None:
        stmt = select(WikiPage).where(
            WikiPage.campaign_id == campaign_id,
            WikiPage.slug == slug,
        )
        return self.db.scalar(stmt)

    def add_page(self, page: WikiPage) -> WikiPage:
        self.db.add(page)
        self.db.flush()
        return page

    def list_pages(self, campaign_id: int) -> list[WikiPage]:
        stmt = (
            select(WikiPage)
            .where(WikiPage.campaign_id == campaign_id)
            .order_by(WikiPage.title.asc(), WikiPage.id.asc())
        )
        return list(self.db.scalars(stmt))

    def next_revision_number(self, page_id: int) -> int:
        stmt = select(func.max(WikiRevision.revision)).where(
            WikiRevision.page_id == page_id
        )
        current = self.db.scalar(stmt)
        return (current or 0) + 1

    def add_revision(self, revision: WikiRevision) -> WikiRevision:
        self.db.add(revision)
        self.db.flush()
        return revision

    def latest_revision(
        self,
        page_id: int,
        *,
        as_of_game_minute: int | None = None,
    ) -> WikiRevision | None:
        stmt = select(WikiRevision).where(WikiRevision.page_id == page_id)
        if as_of_game_minute is not None:
            stmt = stmt.where(
                WikiRevision.effective_from_game_minute <= as_of_game_minute
            )
        stmt = stmt.order_by(
            WikiRevision.effective_from_game_minute.desc(),
            WikiRevision.revision.desc(),
            WikiRevision.id.desc(),
        )
        return self.db.scalar(stmt)


    def get_recall(
        self,
        *,
        expedition_id: int,
        character_id: int,
        page_id: int,
    ) -> KnowledgeRecall | None:
        stmt = select(KnowledgeRecall).where(
            KnowledgeRecall.expedition_id == expedition_id,
            KnowledgeRecall.character_id == character_id,
            KnowledgeRecall.page_id == page_id,
        )
        return self.db.scalar(stmt)

    def get_any_recall_for_page(
        self,
        expedition_id: int,
        page_id: int,
    ) -> KnowledgeRecall | None:
        stmt = (
            select(KnowledgeRecall)
            .where(
                KnowledgeRecall.expedition_id == expedition_id,
                KnowledgeRecall.page_id == page_id,
            )
            .order_by(KnowledgeRecall.id.asc())
        )
        return self.db.scalar(stmt)

    def add_recall(self, recall: KnowledgeRecall) -> KnowledgeRecall:
        self.db.add(recall)
        self.db.flush()
        return recall

    def count_recalls_for_character(
        self,
        expedition_id: int,
        character_id: int,
    ) -> int:
        stmt = select(func.count(KnowledgeRecall.id)).where(
            KnowledgeRecall.expedition_id == expedition_id,
            KnowledgeRecall.character_id == character_id,
        )
        return int(self.db.scalar(stmt) or 0)

    def list_recalls_for_expedition(
        self,
        expedition_id: int,
    ) -> list[KnowledgeRecall]:
        stmt = (
            select(KnowledgeRecall)
            .where(KnowledgeRecall.expedition_id == expedition_id)
            .order_by(KnowledgeRecall.recalled_at_game_minute.asc(), KnowledgeRecall.id.asc())
        )
        return list(self.db.scalars(stmt))
