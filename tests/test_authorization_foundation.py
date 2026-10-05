from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import (
    CampaignMembership,
    CampaignRole,
    Character,
    CharacterMapHexObservation,
    CharacterStatus,
    Expedition,
    ExpeditionCharacter,
    ExpeditionStatus,
    User,
)
from dto.campaign_dto import CampaignCreate
from dto.user_dto import UserCreate
from routes.campaign_routes import create_campaign, list_user_campaigns
from routes.player_map_routes import player_map
from services.authorization import expedition_access
from services.user_service import UserService
from tests.factories import make_map_with_two_hexes


def _user(db: Session, suffix: str) -> User:
    return UserService(db).create(
        UserCreate(
            username=f"authz_{suffix}",
            email=f"authz_{suffix}@example.com",
            password="correct-horse-battery-staple",
        )
    )


def _expedition_fixture(db: Session, campaign):
    dm = _user(db, "dm")
    player = _user(db, "player")
    non_participant = _user(db, "nonparticipant")
    outsider = _user(db, "outsider")
    other_campaign = campaign.__class__(name="Other", epoch_name="Day 1")
    db.add(other_campaign)
    db.flush()
    db.add_all(
        [
            CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM),
            CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER),
            CampaignMembership(campaign_id=campaign.id, user_id=non_participant.id, role=CampaignRole.PLAYER),
            CampaignMembership(campaign_id=other_campaign.id, user_id=outsider.id, role=CampaignRole.PLAYER),
        ]
    )
    world_map, version, source, _destination = make_map_with_two_hexes(db, campaign)
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=player.id,
        name="Player Scout",
        status=CharacterStatus.ACTIVE,
        current_game_minute=0,
    )
    db.add(character)
    db.flush()
    expedition = Expedition(
        campaign_id=campaign.id,
        name="Protected Expedition",
        status=ExpeditionStatus.ACTIVE,
        start_game_minute=0,
        current_game_minute=0,
        current_map_version_id=version.id,
        current_q=source.q,
        current_r=source.r,
    )
    db.add(expedition)
    db.flush()
    db.add(
        ExpeditionCharacter(
            expedition_id=expedition.id,
            character_id=character.id,
            joined_game_minute=0,
        )
    )
    db.commit()
    return dm, player, non_participant, outsider, expedition, character, world_map, version, source


def test_expedition_access_distinguishes_dm_participant_nonparticipant_and_nonmember(db, campaign):
    dm, player, non_participant, outsider, expedition, *_ = _expedition_fixture(db, campaign)

    dm_access = expedition_access(db, expedition.id, dm.id)
    player_access = expedition_access(db, expedition.id, player.id)
    assert dm_access.is_dm is True
    assert dm_access.is_participant is False
    assert player_access.is_participant is True

    with pytest.raises(HTTPException) as nonparticipant_error:
        expedition_access(db, expedition.id, non_participant.id)
    assert nonparticipant_error.value.status_code == 403

    with pytest.raises(HTTPException) as outsider_error:
        expedition_access(db, expedition.id, outsider.id)
    assert outsider_error.value.status_code == 404


def test_campaign_creation_uses_authenticated_creator_not_payload_user(db, campaign):
    caller = _user(db, "caller")
    target = _user(db, "target")

    created = create_campaign(
        CampaignCreate(
            creator_user_id=target.id,
            name="Session-owned campaign",
            epoch_name="Day 1",
        ),
        current_user=caller,
        db=db,
    )

    membership = db.query(CampaignMembership).filter_by(
        campaign_id=created.id,
        role=CampaignRole.DM,
    ).one()
    assert membership.user_id == caller.id
    assert membership.user_id != target.id


def test_user_scoped_campaign_listing_rejects_impersonated_path_id(db, campaign):
    caller = _user(db, "listing_caller")
    target = _user(db, "listing_target")

    with pytest.raises(HTTPException) as error:
        list_user_campaigns(target.id, current_user=caller, db=db)
    assert error.value.status_code == 403


def test_player_map_access_is_authorized_before_filtered_payload_is_returned(db, campaign):
    dm, player, _non_participant, _outsider, expedition, character, world_map, version, source = _expedition_fixture(db, campaign)
    db.add(
        CharacterMapHexObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            map_id=world_map.id,
            map_version_id=version.id,
            q=source.q,
            r=source.r,
            observed_game_minute=0,
            discovery_state="VISITED",
            terrain_key=source.terrain_key,
            elevation=source.elevation,
            visibility_score=source.visibility_score,
            extra_data={"dm_secret": "must not be serialized"},
        )
    )
    db.commit()

    dm_payload = player_map(expedition.id, expedition_access(db, expedition.id, dm.id), db)
    player_payload = player_map(expedition.id, expedition_access(db, expedition.id, player.id), db)

    assert dm_payload.model_dump() == player_payload.model_dump()
    assert len(player_payload.hexes) == 1
    assert "dm_secret" not in player_payload.model_dump_json()
    assert player_payload.dm_ping_q is None
    assert player_payload.dm_ping_user_id is None
