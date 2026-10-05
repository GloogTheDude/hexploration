from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import CampaignMembership, CampaignRole, Character, Expedition, ExpeditionCharacter, ExpeditionStatus, MapVersion, User
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.map_hex_service import contains
from services.visibility_service import axial_hex_distance

PING_TTL_SECONDS = 4


@dataclass(frozen=True)
class ExpeditionPingState:
    expedition_id: int
    q: int | None
    r: int | None
    game_minute: int | None
    user_id: int | None
    username: str | None
    color: str | None
    created_at: datetime | None


class ExpeditionPingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get(self, expedition_id: int) -> Expedition:
        expedition = self.db.get(Expedition, expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        return expedition

    def _user_for_campaign(self, expedition: Expedition, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        membership = self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == expedition.campaign_id,
                CampaignMembership.user_id == user_id,
            )
        )
        if membership is None:
            participant_owner = self.db.scalar(
                select(Character.id)
                .join(ExpeditionCharacter, ExpeditionCharacter.character_id == Character.id)
                .where(
                    ExpeditionCharacter.expedition_id == expedition.id,
                    ExpeditionCharacter.left_game_minute.is_(None),
                    Character.owner_user_id == user_id,
                )
                .limit(1)
            )
            if participant_owner is None:
                raise ForbiddenOperationError("User is not a member of this expedition campaign")
        return user

    @staticmethod
    def _is_fresh(expedition: Expedition) -> bool:
        created_at = expedition.ping_created_at
        if created_at is None or expedition.ping_q is None or expedition.ping_r is None:
            return False
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - created_at <= timedelta(seconds=PING_TTL_SECONDS)

    def get_ping(self, expedition_id: int) -> ExpeditionPingState:
        expedition = self._get(expedition_id)
        if not self._is_fresh(expedition):
            return ExpeditionPingState(expedition.id, None, None, None, None, None, None, None)
        user = self.db.get(User, expedition.ping_user_id) if expedition.ping_user_id else None
        return ExpeditionPingState(
            expedition.id,
            expedition.ping_q,
            expedition.ping_r,
            expedition.ping_game_minute,
            user.id if user else None,
            user.username if user else None,
            user.ping_color if user else "#ff4f64",
            expedition.ping_created_at,
        )

    def set_ping(self, expedition_id: int, user_id: int, q: int, r: int) -> ExpeditionPingState:
        expedition = self._get(expedition_id)
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can receive a destination ping")
        user = self._user_for_campaign(expedition, user_id)
        if expedition.current_map_version_id is None or expedition.current_q is None or expedition.current_r is None:
            raise ConflictError("Expedition has no current map position")
        version = self.db.get(MapVersion, expedition.current_map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        if not contains(version, q, r):
            raise ValueError("Ping is outside the current map")
        if axial_hex_distance(expedition.current_q, expedition.current_r, q, r) != 1:
            raise ConflictError("The next hex ping must be adjacent to the expedition")
        expedition.ping_q = q
        expedition.ping_r = r
        expedition.ping_game_minute = expedition.current_game_minute
        expedition.ping_user_id = user.id
        expedition.ping_created_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(expedition)
        return self.get_ping(expedition.id)

    @staticmethod
    def _is_dm_ping_fresh(expedition: Expedition) -> bool:
        created_at = expedition.dm_ping_created_at
        if created_at is None or expedition.dm_ping_q is None or expedition.dm_ping_r is None:
            return False
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        return datetime.now(UTC) - created_at <= timedelta(seconds=PING_TTL_SECONDS)

    def get_dm_ping(self, expedition_id: int) -> ExpeditionPingState:
        expedition = self._get(expedition_id)
        if not self._is_dm_ping_fresh(expedition):
            return ExpeditionPingState(expedition.id, None, None, None, None, None, None, None)
        user = self.db.get(User, expedition.dm_ping_user_id) if expedition.dm_ping_user_id else None
        return ExpeditionPingState(
            expedition.id, expedition.dm_ping_q, expedition.dm_ping_r,
            expedition.dm_ping_game_minute, user.id if user else None,
            user.username if user else None, user.ping_color if user else "#55c7ff",
            expedition.dm_ping_created_at,
        )

    def set_dm_ping(self, expedition_id: int, user_id: int, q: int, r: int) -> ExpeditionPingState:
        expedition = self._get(expedition_id)
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can receive a DM ping")
        user = self.db.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        membership = self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == expedition.campaign_id,
                CampaignMembership.user_id == user_id,
                CampaignMembership.role == CampaignRole.DM,
            )
        )
        if membership is None:
            raise ForbiddenOperationError("Only a campaign DM can place a DM ping")
        if expedition.current_map_version_id is None or expedition.current_q is None or expedition.current_r is None:
            raise ConflictError("Expedition has no current map position")
        version = self.db.get(MapVersion, expedition.current_map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        if not contains(version, q, r):
            raise ValueError("Ping is outside the current map")
        if axial_hex_distance(expedition.current_q, expedition.current_r, q, r) != 1:
            raise ConflictError("The DM ping must be adjacent to the expedition")
        expedition.dm_ping_q = q
        expedition.dm_ping_r = r
        expedition.dm_ping_game_minute = expedition.current_game_minute
        expedition.dm_ping_user_id = user.id
        expedition.dm_ping_created_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(expedition)
        return self.get_dm_ping(expedition.id)

    def clear_ping(self, expedition_id: int) -> ExpeditionPingState:
        expedition = self._get(expedition_id)
        expedition.ping_q = None
        expedition.ping_r = None
        expedition.ping_game_minute = None
        expedition.ping_user_id = None
        expedition.ping_created_at = None
        self.db.commit()
        self.db.refresh(expedition)
        return ExpeditionPingState(expedition.id, None, None, None, None, None, None, None)
