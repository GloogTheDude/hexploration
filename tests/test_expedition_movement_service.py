from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Campaign, Movement, WorldEvent
from services.errors import MovementBlockedError
from services.expedition_movement_service import ExpeditionMovementService, InvalidMovementError
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _add_bridge_and_events(
    db: Session,
    *,
    campaign_id: int,
    map_version_id: int,
) -> tuple[WorldEvent, WorldEvent]:
    from db.models import MapEdge

    edge = MapEdge(
        map_version_id=map_version_id,
        from_q=0,
        from_r=0,
        to_q=1,
        to_r=0,
        feature_type="BRIDGE",
        feature_id=17,
        name="North Bridge",
        extra_data={},
    )
    db.add(edge)
    db.flush()

    destroyed = WorldEvent(
        campaign_id=campaign_id,
        expedition_id=None,
        game_minute=200,
        event_type="BRIDGE_DESTROYED",
        target_type="BRIDGE",
        target_id=17,
        payload={},
        dm_note=None,
    )
    repaired = WorldEvent(
        campaign_id=campaign_id,
        expedition_id=None,
        game_minute=400,
        event_type="BRIDGE_REPAIRED",
        target_type="BRIDGE",
        target_id=17,
        payload={},
        dm_note=None,
    )
    db.add_all([destroyed, repaired])
    db.commit()
    return destroyed, repaired


def test_destroyed_bridge_blocks_move_without_mutating_expedition(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    destroyed, _ = _add_bridge_and_events(
        db,
        campaign_id=campaign.id,
        map_version_id=version.id,
    )
    expedition, character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=250,
    )
    service = ExpeditionMovementService(db)

    with pytest.raises(MovementBlockedError) as exc_info:
        service.move(
            expedition_id=expedition.id,
            to_q=1,
            to_r=0,
            base_duration_minutes=60,
        )

    db.refresh(expedition)
    assert (expedition.current_q, expedition.current_r) == (0, 0)
    assert expedition.current_game_minute == 250

    assert character is not None
    db.refresh(character)
    assert character.current_game_minute == 250

    assert db.scalar(select(Movement).where(Movement.expedition_id == expedition.id)) is None
    assert exc_info.value.detail == {
        "code": "MOVEMENT_BLOCKED",
        "reason": "BRIDGE_DESTROYED",
        "target_type": "BRIDGE",
        "target_id": 17,
        "edge_id": exc_info.value.detail["edge_id"],
        "game_minute": 250,
        "world_event_id": destroyed.id,
    }


def test_repaired_bridge_allows_move_and_advances_character_clock(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    _add_bridge_and_events(
        db,
        campaign_id=campaign.id,
        map_version_id=version.id,
    )
    expedition, character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=450,
    )
    service = ExpeditionMovementService(db)

    movement = service.move(
        expedition_id=expedition.id,
        to_q=1,
        to_r=0,
        base_duration_minutes=60,
    )

    assert movement.departure_game_minute == 450
    assert movement.arrival_game_minute == 510
    assert movement.effective_duration_minutes == 60
    assert movement.modifiers == [
        {"type": "terrain", "terrain_key": "PLAIN", "multiplier": 1.0}
    ]

    db.refresh(expedition)
    assert (expedition.current_q, expedition.current_r) == (1, 0)
    assert expedition.current_game_minute == 510

    assert character is not None
    db.refresh(character)
    assert character.current_game_minute == 510


def test_movement_uses_weather_at_expedition_departure_time(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(
        db,
        campaign,
        destination_terrain="FOREST",
        destination_travel_cost=1.5,
    )
    db.add_all(
        [
            WorldEvent(
                campaign_id=campaign.id,
                expedition_id=None,
                game_minute=100,
                event_type="WEATHER_CHANGED",
                target_type=None,
                target_id=None,
                payload={"weather_key": "RAIN"},
                dm_note=None,
            ),
            WorldEvent(
                campaign_id=campaign.id,
                expedition_id=None,
                game_minute=300,
                event_type="WEATHER_CHANGED",
                target_type=None,
                target_id=None,
                payload={"weather_key": "STORM"},
                dm_note=None,
            ),
        ]
    )
    db.commit()

    expedition, _ = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=150,
        with_character=False,
    )
    service = ExpeditionMovementService(db)

    movement = service.move(
        expedition_id=expedition.id,
        to_q=1,
        to_r=0,
        base_duration_minutes=60,
    )

    # ceil(60 * FOREST 1.5 * RAIN 1.15) == 104
    assert movement.effective_duration_minutes == 104
    assert movement.arrival_game_minute == 254
    assert movement.modifiers == [
        {"type": "terrain", "terrain_key": "FOREST", "multiplier": 1.5},
        {"type": "weather", "weather_key": "RAIN", "multiplier": 1.15},
    ]


def test_undo_last_move_restores_position_and_clocks(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=100)
    assert character is not None
    service = ExpeditionMovementService(db)

    movement = service.move(
        expedition_id=expedition.id,
        to_q=1,
        to_r=0,
        base_duration_minutes=60,
    )
    assert expedition.current_game_minute == movement.arrival_game_minute

    undone = service.undo_last_move(expedition.id)

    assert undone.id == movement.id
    db.refresh(expedition)
    db.refresh(character)
    assert (expedition.current_q, expedition.current_r) == (0, 0)
    assert expedition.current_game_minute == 100
    assert character.current_game_minute == 100
    assert db.scalar(select(Movement).where(Movement.id == movement.id)) is None
    from dto.movement_dto import MovementResponse
    assert MovementResponse.model_validate(undone).id == movement.id


def test_invalid_destination_does_not_mutate_expedition(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=100)
    service = ExpeditionMovementService(db)

    with pytest.raises(InvalidMovementError, match="adjacent"):
        service.move(
            expedition_id=expedition.id,
            to_q=2,
            to_r=0,
            base_duration_minutes=60,
        )

    db.refresh(expedition)
    assert (expedition.current_q, expedition.current_r, expedition.current_game_minute) == (0, 0, 100)
    assert db.scalar(select(Movement).where(Movement.expedition_id == expedition.id)) is None


def test_non_positive_movement_duration_is_rejected(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=100)

    with pytest.raises(InvalidMovementError, match="greater than zero"):
        ExpeditionMovementService(db).move(
            expedition_id=expedition.id,
            to_q=1,
            to_r=0,
            base_duration_minutes=0,
        )

    db.refresh(expedition)
    assert expedition.current_game_minute == 100
