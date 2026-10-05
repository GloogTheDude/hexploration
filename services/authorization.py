from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    CampaignMembership,
    CampaignRole,
    Character,
    Expedition,
    ExpeditionCharacter,
    MapEdge,
    MapHex,
    MapVersion,
    PointOfInterest,
    WorldEvent,
    User,
)
from db.session import get_db
from services.auth_dependencies import get_current_user


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def campaign_membership(
    db: Session, campaign_id: int, user_id: int
) -> CampaignMembership | None:
    return db.scalar(
        select(CampaignMembership).where(
            CampaignMembership.campaign_id == campaign_id,
            CampaignMembership.user_id == user_id,
        )
    )


def require_campaign_member(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignMembership:
    membership = campaign_membership(db, campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Campaign not found")
    return membership


def require_campaign_dm(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignMembership:
    membership = campaign_membership(db, campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Campaign not found")
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return membership


@dataclass(frozen=True)
class ExpeditionAccess:
    expedition: Expedition
    membership: CampaignMembership
    is_participant: bool

    @property
    def is_dm(self) -> bool:
        return self.membership.role == CampaignRole.DM


def expedition_access(
    db: Session, expedition_id: int, user_id: int
) -> ExpeditionAccess:
    expedition = db.get(Expedition, expedition_id)
    if expedition is None:
        raise _not_found("Expedition not found")

    membership = campaign_membership(db, expedition.campaign_id, user_id)
    if membership is None:
        raise _not_found("Expedition not found")

    participant = db.scalar(
        select(ExpeditionCharacter.id)
        .join(Character, ExpeditionCharacter.character_id == Character.id)
        .where(
            ExpeditionCharacter.expedition_id == expedition.id,
            ExpeditionCharacter.left_game_minute.is_(None),
            Character.owner_user_id == user_id,
        )
        .limit(1)
    )
    is_participant = participant is not None
    if membership.role != CampaignRole.DM and not is_participant:
        raise _forbidden("Active expedition participation required")

    return ExpeditionAccess(expedition, membership, is_participant)


def require_expedition_access(
    expedition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpeditionAccess:
    return expedition_access(db, expedition_id, current_user.id)


def require_expedition_dm(
    expedition_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpeditionAccess:
    access = expedition_access(db, expedition_id, current_user.id)
    if not access.is_dm:
        raise _forbidden("Campaign DM membership required")
    return access


def require_expedition_character_access(
    expedition_id: int,
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpeditionAccess:
    access = expedition_access(db, expedition_id, current_user.id)
    participant = db.scalar(
        select(ExpeditionCharacter)
        .join(Character, ExpeditionCharacter.character_id == Character.id)
        .where(
            ExpeditionCharacter.expedition_id == expedition_id,
            ExpeditionCharacter.character_id == character_id,
            ExpeditionCharacter.left_game_minute.is_(None),
        )
    )
    if participant is None:
        raise _forbidden("Character is not an active expedition participant")
    if not access.is_dm:
        character = db.get(Character, character_id)
        if character is None or character.owner_user_id != current_user.id:
            raise _forbidden("Character ownership required")
    return access


def require_character_access(
    character_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Character:
    character = db.get(Character, character_id)
    if character is None:
        raise _not_found("Character not found")

    membership = campaign_membership(db, character.campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Character not found")
    if (
        membership.role != CampaignRole.DM
        and character.owner_user_id != current_user.id
    ):
        raise _forbidden("Character ownership required")
    return character


def _campaign_for_map_version(db: Session, map_version_id: int) -> int:
    version = db.get(MapVersion, map_version_id)
    if version is None or version.map is None:
        raise _not_found("Map version not found")
    return version.map.campaign_id


def require_map_version_dm(
    map_version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MapVersion:
    version = db.get(MapVersion, map_version_id)
    if version is None or version.map is None:
        raise _not_found("Map version not found")
    membership = campaign_membership(db, version.map.campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Map version not found")
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return version


def require_hex_dm(
    hex_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MapHex:
    tile = db.get(MapHex, hex_id)
    if tile is None or tile.map_version is None or tile.map_version.map is None:
        raise _not_found("Map hex not found")
    membership = campaign_membership(db, tile.map_version.map.campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Map hex not found")
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return tile


def require_map_edge_dm(
    edge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MapEdge:
    edge = db.get(MapEdge, edge_id)
    if edge is None or edge.map_version is None or edge.map_version.map is None:
        raise _not_found("Map edge not found")
    membership = campaign_membership(db, edge.map_version.map.campaign_id, current_user.id)
    if membership is None:
        raise _not_found("Map edge not found")
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return edge


def require_world_event_member(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorldEvent:
    event = db.get(WorldEvent, event_id)
    if event is None:
        raise _not_found("World event not found")
    if campaign_membership(db, event.campaign_id, current_user.id) is None:
        raise _not_found("World event not found")
    return event


def require_world_event_dm(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorldEvent:
    event = require_world_event_member(event_id, current_user, db)
    membership = campaign_membership(db, event.campaign_id, current_user.id)
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return event


def require_poi_member(
    poi_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointOfInterest:
    poi = db.get(PointOfInterest, poi_id)
    if poi is None:
        raise _not_found("POI not found")
    tile = poi.hex
    version = tile.map_version if tile is not None else None
    world_map = version.map if version is not None else None
    if world_map is None or campaign_membership(db, world_map.campaign_id, current_user.id) is None:
        raise _not_found("POI not found")
    return poi


def require_poi_dm(
    poi_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PointOfInterest:
    poi = require_poi_member(poi_id, current_user, db)
    world_map = poi.hex.map_version.map
    membership = campaign_membership(db, world_map.campaign_id, current_user.id)
    if membership.role != CampaignRole.DM:
        raise _forbidden("Campaign DM membership required")
    return poi


def require_same_user(requested_user_id: int, current_user: User) -> None:
    if requested_user_id != current_user.id:
        raise _forbidden("The requested user does not match the authenticated user")
