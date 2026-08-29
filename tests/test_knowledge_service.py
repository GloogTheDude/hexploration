from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    Character,
    CharacterStatus,
    ExpeditionCharacter,
    User,
)
from dto.poi_dto import POICreate
from dto.world_event_dto import WorldEventCreate
from services.errors import ConflictError, NotFoundError
from services.knowledge_service import KnowledgeService
from services.poi_service import POIService
from services.world_event_service import WorldEventService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _poi_on_expedition_hex(db: Session, campaign: Campaign):
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=100,
    )
    poi = POIService(db).create(
        POICreate(
            hex_id=source.id,
            name="Old Watchtower",
            kind="RUIN",
            is_landmark=True,
        )
    )
    assert character is not None
    return expedition, character, poi


def test_undiscovered_poi_is_not_character_knowledge(
    db: Session,
    campaign: Campaign,
):
    _, character, poi = _poi_on_expedition_hex(db, campaign)

    with pytest.raises(NotFoundError):
        KnowledgeService(db).latest_for_target(character.id, "POI", poi.id)


def test_discovery_snapshots_world_truth_without_future_updates(
    db: Session,
    campaign: Campaign,
):
    expedition, character, poi = _poi_on_expedition_hex(db, campaign)
    world = WorldEventService(db)
    world.create(
        campaign.id,
        WorldEventCreate(
            game_minute=200,
            event_type="POI_DESTROYED",
            target_type="POI",
            target_id=poi.id,
            payload={"reason": "dragon"},
        ),
    )

    knowledge = KnowledgeService(db)
    observations = knowledge.discover_poi(expedition.id, poi.id)
    assert len(observations) == 1
    assert observations[0].character_id == character.id
    assert observations[0].observed_game_minute == 100
    assert observations[0].knowledge["state"] == "ACTIVE"
    assert observations[0].knowledge["exists"] is True

    # The world changes at minute 200, but knowledge does not magically update.
    assert POIService(db).state_at(
        poi.id,
        campaign_id=campaign.id,
        game_minute=250,
    ).state == "DESTROYED"
    still_known = knowledge.latest_for_target(character.id, "POI", poi.id)
    assert still_known.observed_game_minute == 100
    assert still_known.knowledge["state"] == "ACTIVE"


def test_reobservation_updates_latest_knowledge_but_preserves_history(
    db: Session,
    campaign: Campaign,
):
    expedition, character, poi = _poi_on_expedition_hex(db, campaign)
    knowledge = KnowledgeService(db)
    knowledge.discover_poi(expedition.id, poi.id)

    WorldEventService(db).create(
        campaign.id,
        WorldEventCreate(
            game_minute=200,
            event_type="POI_DESTROYED",
            target_type="POI",
            target_id=poi.id,
            payload={},
        ),
    )
    expedition.current_game_minute = 250
    character.current_game_minute = 250
    db.commit()

    knowledge.discover_poi(expedition.id, poi.id)

    latest = knowledge.latest_for_target(character.id, "POI", poi.id)
    assert latest.observed_game_minute == 250
    assert latest.knowledge["state"] == "DESTROYED"
    assert latest.knowledge["exists"] is False

    history = knowledge.history_for_target(character.id, "POI", poi.id)
    assert [item.observed_game_minute for item in history] == [100, 250]
    assert [item.knowledge["state"] for item in history] == [
        "ACTIVE",
        "DESTROYED",
    ]

    # Historical knowledge can still be resolved as-of a past character time.
    old_view = knowledge.latest_for_target(
        character.id,
        "POI",
        poi.id,
        as_of_game_minute=150,
    )
    assert old_view.knowledge["state"] == "ACTIVE"


def test_discovery_is_shared_with_all_active_expedition_characters(
    db: Session,
    campaign: Campaign,
):
    expedition, first_character, poi = _poi_on_expedition_hex(db, campaign)

    user = User(
        username="second_explorer",
        email="second@example.com",
        password_hash="unused",
    )
    db.add(user)
    db.flush()
    second_character = Character(
        campaign_id=campaign.id,
        owner_user_id=user.id,
        name="Second Explorer",
        race="Elf",
        character_class="Wizard",
        level=1,
        description=None,
        status=CharacterStatus.ACTIVE,
        current_game_minute=100,
    )
    db.add(second_character)
    db.flush()
    db.add(
        ExpeditionCharacter(
            expedition_id=expedition.id,
            character_id=second_character.id,
            joined_game_minute=100,
            left_game_minute=None,
        )
    )
    db.commit()

    observations = KnowledgeService(db).discover_poi(expedition.id, poi.id)
    assert {item.character_id for item in observations} == {
        first_character.id,
        second_character.id,
    }

    for character in (first_character, second_character):
        known = KnowledgeService(db).latest_for_target(
            character.id,
            "POI",
            poi.id,
        )
        assert known.knowledge["name"] == "Old Watchtower"


def test_discovery_requires_expedition_to_be_on_poi_hex(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=100,
    )
    poi = POIService(db).create(
        POICreate(hex_id=destination.id, name="Far Away Shrine")
    )

    with pytest.raises(ConflictError, match="current hex"):
        KnowledgeService(db).discover_poi(expedition.id, poi.id)
