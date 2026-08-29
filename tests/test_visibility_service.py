from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    Character,
    CharacterStatus,
    ExpeditionCharacter,
    MapHex,
    User,
    WorldEvent,
)
from dto.poi_dto import POICreate
from services.expedition_movement_service import ExpeditionMovementService
from services.knowledge_service import KnowledgeService
from services.poi_service import POIService
from services.visibility_service import VisibilityService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _extend_line(
    db: Session,
    version_id: int,
    *,
    through_q: int,
    visibility_score: int = 3,
    elevation: int = 1,
) -> dict[int, MapHex]:
    result: dict[int, MapHex] = {}
    for q in range(2, through_q + 1):
        hex_tile = MapHex(
            map_version_id=version_id,
            q=q,
            r=0,
            terrain_key="PLAIN",
            elevation=elevation,
            visibility_score=visibility_score,
            travel_cost=1.0,
            extra_data={},
        )
        db.add(hex_tile)
        db.flush()
        result[q] = hex_tile
    db.commit()
    return result


def _poi(db: Session, hex_tile: MapHex, name: str, *, landmark: bool = False):
    return POIService(db).create(
        POICreate(
            hex_id=hex_tile.id,
            name=name,
            kind="TEST",
            is_landmark=landmark,
        )
    )


def test_plain_visibility_uses_distance_and_origin_visibility_score(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    extra = _extend_line(db, version.id, through_q=4)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)

    near = _poi(db, extra[3], "Three Hex Shrine")
    far = _poi(db, extra[4], "Four Hex Shrine")

    scan = VisibilityService(db).scan(expedition.id)
    visible_ids = {item.poi.id for item in scan.visible_pois}

    assert near.id in visible_ids
    assert far.id not in visible_ids
    assert scan.origin_visibility_score == 3


def test_landmark_extends_visibility_range(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    extra = _extend_line(db, version.id, through_q=5)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)

    landmark = _poi(db, extra[5], "Black Spire", landmark=True)
    normal = _poi(db, extra[5], "Hidden Camp", landmark=False)

    scan = VisibilityService(db).scan(expedition.id)
    by_id = {item.poi.id: item for item in scan.visible_pois}

    assert landmark.id in by_id
    assert by_id[landmark.id].distance == 5
    assert by_id[landmark.id].landmark_bonus == 2
    assert normal.id not in by_id


def test_fog_reduces_range_but_current_hex_is_always_observable(
    db: Session,
    campaign: Campaign,
):
    _, version, source, destination = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=100)
    here = _poi(db, source, "Camp Marker")
    adjacent = _poi(db, destination, "Nearby Statue")
    db.add(
        WorldEvent(
            campaign_id=campaign.id,
            expedition_id=None,
            game_minute=50,
            event_type="WEATHER_CHANGED",
            target_type=None,
            target_id=None,
            payload={"weather_key": "FOG"},
            dm_note=None,
        )
    )
    db.commit()

    scan = VisibilityService(db).scan(expedition.id)
    visible_ids = {item.poi.id for item in scan.visible_pois}

    assert scan.weather_key == "FOG"
    assert here.id in visible_ids
    assert adjacent.id not in visible_ids


def test_concealing_target_terrain_reduces_visibility(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    extra = _extend_line(db, version.id, through_q=3)
    extra[3].terrain_key = "FOREST"
    extra[3].visibility_score = 2
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, extra[3], "Forest Ruin")

    scan = VisibilityService(db).scan(expedition.id)
    assert poi.id not in {item.poi.id for item in scan.visible_pois}


def test_observer_elevation_advantage_extends_range(
    db: Session,
    campaign: Campaign,
):
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    source.elevation = 3
    extra = _extend_line(db, version.id, through_q=4, elevation=1)
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, extra[4], "Valley Tower")

    scan = VisibilityService(db).scan(expedition.id)
    item = next(item for item in scan.visible_pois if item.poi.id == poi.id)
    assert item.elevation_bonus == 2
    assert item.max_visible_distance == 5


def test_observe_visible_pois_is_shared_and_deduplicates_unchanged_state(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    expedition, first = make_active_expedition(db, campaign, version, game_minute=100)
    assert first is not None
    poi = _poi(db, destination, "Roadside Chapel")

    user = User(
        username="visibility_second",
        email="visibility_second@example.com",
        password_hash="unused",
    )
    db.add(user)
    db.flush()
    second = Character(
        campaign_id=campaign.id,
        owner_user_id=user.id,
        name="Second Scout",
        race="Elf",
        character_class="Ranger",
        level=1,
        description=None,
        status=CharacterStatus.ACTIVE,
        current_game_minute=100,
    )
    db.add(second)
    db.flush()
    db.add(
        ExpeditionCharacter(
            expedition_id=expedition.id,
            character_id=second.id,
            joined_game_minute=100,
            left_game_minute=None,
        )
    )
    db.commit()

    service = VisibilityService(db)
    first_scan = service.observe_visible_pois(expedition.id)
    second_scan = service.observe_visible_pois(expedition.id)

    assert {item.character_id for item in first_scan.observations} == {
        first.id,
        second.id,
    }
    assert second_scan.observations == []
    for character in (first, second):
        known = KnowledgeService(db).latest_for_target(character.id, "POI", poi.id)
        assert known.source_type == "AUTO_VISIBILITY"
        assert known.knowledge["name"] == "Roadside Chapel"


def test_movement_automatically_observes_world_state_at_arrival_minute(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=0)
    assert character is not None
    poi = _poi(db, destination, "Fallen Tower")
    db.add(
        WorldEvent(
            campaign_id=campaign.id,
            expedition_id=None,
            game_minute=30,
            event_type="POI_DESTROYED",
            target_type="POI",
            target_id=poi.id,
            payload={},
            dm_note=None,
        )
    )
    db.commit()

    movement = ExpeditionMovementService(db).move(
        expedition_id=expedition.id,
        to_q=1,
        to_r=0,
        base_duration_minutes=60,
    )

    assert movement.arrival_game_minute == 60
    known = KnowledgeService(db).latest_for_target(character.id, "POI", poi.id)
    assert known.observed_game_minute == 60
    assert known.source_type == "AUTO_VISIBILITY"
    assert known.knowledge["state"] == "DESTROYED"
    assert known.knowledge["exists"] is False


def test_dense_intermediate_terrain_occludes_poi_behind_it(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    destination.terrain_key = "FOREST"
    destination.visibility_score = 2
    extra = _extend_line(db, version.id, through_q=3)
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, extra[3], "Temple Beyond Forest")

    scan = VisibilityService(db).scan(expedition.id)
    assert poi.id not in {item.poi.id for item in scan.visible_pois}
    blocked = next(item for item in scan.occluded_pois if item.poi.id == poi.id)
    assert (blocked.blocker_q, blocked.blocker_r) == (1, 0)
    assert blocked.blocker_reason == "TERRAIN_CONCEALMENT"
    assert blocked.los_path == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_high_intermediate_hex_occludes_lower_target(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    destination.elevation = 4
    extra = _extend_line(db, version.id, through_q=3, elevation=1)
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, extra[3], "Valley Beacon")

    scan = VisibilityService(db).scan(expedition.id)
    blocked = next(item for item in scan.occluded_pois if item.poi.id == poi.id)
    assert blocked.blocker_reason == "ELEVATION"
    assert blocked.blocker_elevation == 4.0
    assert blocked.sightline_elevation == 1.0


def test_high_observer_can_see_over_dense_intermediate_terrain(
    db: Session,
    campaign: Campaign,
):
    _, version, source, destination = make_map_with_two_hexes(db, campaign)
    source.elevation = 5
    destination.terrain_key = "FOREST"
    destination.visibility_score = 2
    extra = _extend_line(db, version.id, through_q=3, elevation=1)
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, extra[3], "Lowland Keep")

    scan = VisibilityService(db).scan(expedition.id)
    visible = next(item for item in scan.visible_pois if item.poi.id == poi.id)
    assert visible.los_path == [(0, 0), (1, 0), (2, 0), (3, 0)]


def test_missing_intermediate_hex_is_opaque(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    target = MapHex(
        map_version_id=version.id,
        q=3,
        r=0,
        terrain_key="PLAIN",
        elevation=1,
        visibility_score=3,
        travel_cost=1.0,
        extra_data={},
    )
    db.add(target)
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, target, "Across The Void")

    scan = VisibilityService(db).scan(expedition.id)
    blocked = next(item for item in scan.occluded_pois if item.poi.id == poi.id)
    # q=1 exists from the factory; q=2 does not.
    assert (blocked.blocker_q, blocked.blocker_r) == (2, 0)
    assert blocked.blocker_reason == "MISSING_HEX"


def test_adjacent_poi_never_has_intermediate_los_blocker(
    db: Session,
    campaign: Campaign,
):
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    destination.elevation = 20
    destination.visibility_score = 0
    db.commit()
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)
    poi = _poi(db, destination, "Cliff Face")

    # Destination terrain may make a distant POI harder to see, but there is no
    # intervening cell between adjacent hexes. Current v13 LOS therefore cannot
    # occlude it once it passes the range model.
    destination.visibility_score = 3
    db.commit()
    scan = VisibilityService(db).scan(expedition.id)
    visible = next(item for item in scan.visible_pois if item.poi.id == poi.id)
    assert visible.los_path == [(0, 0), (1, 0)]
