from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    Character,
    Expedition,
    ExpeditionCharacter,
    ExpeditionStatus,
)


OPEN_EXPEDITION_STATUSES = (
    ExpeditionStatus.PLANNING,
    ExpeditionStatus.ACTIVE,
    ExpeditionStatus.DEBRIEFING,
)


class ExpeditionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, expedition_id: int) -> Expedition | None:
        return self.db.get(Expedition, expedition_id)

    def get_for_update(self, expedition_id: int) -> Expedition | None:
        stmt = (
            select(Expedition)
            .where(Expedition.id == expedition_id)
            .with_for_update()
        )
        return self.db.scalar(stmt)

    def add(self, expedition: Expedition) -> Expedition:
        self.db.add(expedition)
        self.db.flush()
        return expedition

    def list_for_campaign(self, campaign_id: int) -> list[Expedition]:
        stmt = (
            select(Expedition)
            .where(Expedition.campaign_id == campaign_id)
            .order_by(Expedition.created_at.desc(), Expedition.id.desc())
        )
        return list(self.db.scalars(stmt))

    def list_for_user(self, campaign_id: int, user_id: int) -> list[Expedition]:
        stmt = (
            select(Expedition)
            .join(ExpeditionCharacter, ExpeditionCharacter.expedition_id == Expedition.id)
            .join(Character, Character.id == ExpeditionCharacter.character_id)
            .where(
                Expedition.campaign_id == campaign_id,
                Character.owner_user_id == user_id,
            )
            .distinct()
            .order_by(Expedition.created_at.desc(), Expedition.id.desc())
        )
        return list(self.db.scalars(stmt))

    def get_participant(
        self,
        expedition_id: int,
        character_id: int,
    ) -> ExpeditionCharacter | None:
        stmt = select(ExpeditionCharacter).where(
            ExpeditionCharacter.expedition_id == expedition_id,
            ExpeditionCharacter.character_id == character_id,
        )
        return self.db.scalar(stmt)

    def add_participant(
        self,
        participant: ExpeditionCharacter,
    ) -> ExpeditionCharacter:
        self.db.add(participant)
        self.db.flush()
        return participant

    def list_participants(self, expedition_id: int) -> list[ExpeditionCharacter]:
        stmt = (
            select(ExpeditionCharacter)
            .where(ExpeditionCharacter.expedition_id == expedition_id)
            .order_by(ExpeditionCharacter.id)
        )
        return list(self.db.scalars(stmt))

    def active_expedition_for_character(
        self,
        character_id: int,
    ) -> ExpeditionCharacter | None:
        stmt = (
            select(ExpeditionCharacter)
            .join(Expedition, Expedition.id == ExpeditionCharacter.expedition_id)
            .where(
                ExpeditionCharacter.character_id == character_id,
                ExpeditionCharacter.left_game_minute.is_(None),
                Expedition.status.in_(OPEN_EXPEDITION_STATUSES),
            )
            .order_by(ExpeditionCharacter.id.desc())
        )
        return self.db.scalar(stmt)

    def get_character(self, character_id: int) -> Character | None:
        return self.db.get(Character, character_id)
