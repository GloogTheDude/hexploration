from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Campaign
from dto.world_event_dto import WorldEventCreate
from services.world_event_service import WorldEventService


def _event(
    service: WorldEventService,
    campaign_id: int,
    *,
    game_minute: int,
    event_type: str,
    target_type: str | None = None,
    target_id: int | None = None,
    payload: dict | None = None,
):
    return service.create(
        campaign_id,
        WorldEventCreate(
            game_minute=game_minute,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
        ),
    )


def test_weather_is_resolved_at_requested_campaign_minute(
    db: Session,
    campaign: Campaign,
):
    service = WorldEventService(db)

    _event(
        service,
        campaign.id,
        game_minute=100,
        event_type="WEATHER_CHANGED",
        payload={"weather_key": "rain"},
    )
    _event(
        service,
        campaign.id,
        game_minute=300,
        event_type="WEATHER_CHANGED",
        payload={"weather_key": "storm"},
    )

    assert service.weather_at(campaign.id, 99) is None
    assert service.weather_at(campaign.id, 100) == "RAIN"
    assert service.weather_at(campaign.id, 299) == "RAIN"
    assert service.weather_at(campaign.id, 300) == "STORM"
    assert service.weather_at(campaign.id, 900) == "STORM"


def test_destroyed_bridge_blocks_until_latest_repair(
    db: Session,
    campaign: Campaign,
):
    service = WorldEventService(db)

    destroyed = _event(
        service,
        campaign.id,
        game_minute=200,
        event_type="BRIDGE_DESTROYED",
        target_type="bridge",
        target_id=17,
    )
    repaired = _event(
        service,
        campaign.id,
        game_minute=400,
        event_type="BRIDGE_REPAIRED",
        target_type="BRIDGE",
        target_id=17,
    )

    before = service.traversal_state_for_target(
        campaign.id,
        game_minute=199,
        target_type="BRIDGE",
        target_id=17,
    )
    during = service.traversal_state_for_target(
        campaign.id,
        game_minute=250,
        target_type="bridge",
        target_id=17,
    )
    after = service.traversal_state_for_target(
        campaign.id,
        game_minute=450,
        target_type="BRIDGE",
        target_id=17,
    )

    assert before.allowed is True
    assert before.event is None

    assert during.allowed is False
    assert during.event is not None
    assert during.event.id == destroyed.id
    assert during.event.event_type == "BRIDGE_DESTROYED"

    assert after.allowed is True
    assert after.event is not None
    assert after.event.id == repaired.id
    assert after.event.event_type == "BRIDGE_REPAIRED"


def test_resolve_state_uses_latest_event_per_target(
    db: Session,
    campaign: Campaign,
):
    service = WorldEventService(db)

    _event(
        service,
        campaign.id,
        game_minute=200,
        event_type="BRIDGE_DESTROYED",
        target_type="BRIDGE",
        target_id=17,
    )
    _event(
        service,
        campaign.id,
        game_minute=300,
        event_type="ROAD_BLOCKED",
        target_type="ROAD",
        target_id=5,
    )
    repaired = _event(
        service,
        campaign.id,
        game_minute=400,
        event_type="BRIDGE_REPAIRED",
        target_type="BRIDGE",
        target_id=17,
    )

    state = service.resolve_state(campaign.id, 450)
    by_target = {
        (event.target_type, event.target_id): event
        for event in state.latest_target_events
    }

    assert by_target[("BRIDGE", 17)].id == repaired.id
    assert by_target[("ROAD", 5)].event_type == "ROAD_BLOCKED"
    assert len(by_target) == 2
