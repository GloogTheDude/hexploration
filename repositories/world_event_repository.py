from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Campaign, Expedition, WorldEvent


class WorldEventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_campaign(self, campaign_id: int) -> Campaign | None:
        return self.db.get(Campaign, campaign_id)

    def get_expedition(self, expedition_id: int) -> Expedition | None:
        return self.db.get(Expedition, expedition_id)

    def get(self, event_id: int) -> WorldEvent | None:
        return self.db.get(WorldEvent, event_id)

    def add(self, event: WorldEvent) -> WorldEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def delete(self, event: WorldEvent) -> None:
        self.db.delete(event)

    def list_for_campaign(
        self,
        campaign_id: int,
        *,
        from_game_minute: int | None = None,
        to_game_minute: int | None = None,
        event_type: str | None = None,
        target_type: str | None = None,
        target_id: int | None = None,
    ) -> list[WorldEvent]:
        stmt = select(WorldEvent).where(WorldEvent.campaign_id == campaign_id)

        if from_game_minute is not None:
            stmt = stmt.where(WorldEvent.game_minute >= from_game_minute)
        if to_game_minute is not None:
            stmt = stmt.where(WorldEvent.game_minute <= to_game_minute)
        if event_type is not None:
            stmt = stmt.where(WorldEvent.event_type == event_type)
        if target_type is not None:
            stmt = stmt.where(WorldEvent.target_type == target_type)
        if target_id is not None:
            stmt = stmt.where(WorldEvent.target_id == target_id)

        stmt = stmt.order_by(WorldEvent.game_minute, WorldEvent.id)
        return list(self.db.scalars(stmt))

    def events_up_to(
        self,
        campaign_id: int,
        game_minute: int,
    ) -> list[WorldEvent]:
        stmt = (
            select(WorldEvent)
            .where(
                WorldEvent.campaign_id == campaign_id,
                WorldEvent.game_minute <= game_minute,
            )
            .order_by(WorldEvent.game_minute, WorldEvent.id)
        )
        return list(self.db.scalars(stmt))


    def latest_target_event_of_types(
        self,
        campaign_id: int,
        *,
        game_minute: int,
        target_type: str,
        target_id: int,
        event_types: set[str],
    ) -> WorldEvent | None:
        if not event_types:
            return None

        stmt = (
            select(WorldEvent)
            .where(
                WorldEvent.campaign_id == campaign_id,
                WorldEvent.game_minute <= game_minute,
                WorldEvent.target_type == target_type,
                WorldEvent.target_id == target_id,
                WorldEvent.event_type.in_(event_types),
            )
            .order_by(WorldEvent.game_minute.desc(), WorldEvent.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def latest_event(
        self,
        campaign_id: int,
        *,
        game_minute: int,
        event_type: str,
    ) -> WorldEvent | None:
        stmt = (
            select(WorldEvent)
            .where(
                WorldEvent.campaign_id == campaign_id,
                WorldEvent.game_minute <= game_minute,
                WorldEvent.event_type == event_type,
            )
            .order_by(WorldEvent.game_minute.desc(), WorldEvent.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
