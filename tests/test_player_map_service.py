from sqlalchemy.orm import Session

from db.models import CharacterKnowledgeObservation, CharacterMapHexObservation, MapHex
from services.errors import ConflictError
from services.player_map_service import PlayerMapService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def test_player_map_exposes_only_known_hexes(db: Session, campaign):
    world_map, version, source, destination = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=100)
    assert character is not None

    db.add(
        CharacterMapHexObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            map_id=world_map.id,
            map_version_id=version.id,
            q=source.q,
            r=source.r,
            observed_game_minute=100,
            discovery_state="VISITED",
            terrain_key=source.terrain_key,
            elevation=source.elevation,
            visibility_score=source.visibility_score,
            extra_data={},
        )
    )
    db.commit()

    state = PlayerMapService(db).get(expedition.id)

    assert [(row.q, row.r) for row in state.hexes] == [(0, 0)]
    assert (destination.q, destination.r) not in [(row.q, row.r) for row in state.hexes]


def test_player_map_uses_latest_known_poi_snapshot(db: Session, campaign):
    world_map, version, source, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None

    db.add_all([
        CharacterKnowledgeObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            target_type="POI",
            target_id=9,
            observed_game_minute=120,
            source_type="DISCOVERY",
            knowledge={
                "name": "Old Tower",
                "kind": "RUIN",
                "map_version_id": version.id,
                "q": source.q,
                "r": source.r,
                "state": "ACTIVE",
                "exists": True,
            },
        ),
        CharacterKnowledgeObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            target_type="POI",
            target_id=9,
            observed_game_minute=180,
            source_type="DISCOVERY",
            knowledge={
                "name": "Old Tower",
                "kind": "RUIN",
                "map_version_id": version.id,
                "q": source.q,
                "r": source.r,
                "state": "DESTROYED",
                "exists": False,
            },
        ),
    ])
    db.commit()

    state = PlayerMapService(db).get(expedition.id)

    assert len(state.pois) == 1
    assert state.pois[0].observed_game_minute == 180
    assert state.pois[0].knowledge["state"] == "DESTROYED"


def test_player_map_ignores_future_and_other_version_poi_knowledge(db: Session, campaign):
    world_map, version, source, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None

    db.add_all([
        CharacterKnowledgeObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            target_type="POI",
            target_id=1,
            observed_game_minute=250,
            source_type="DISCOVERY",
            knowledge={"name": "Future", "map_version_id": version.id, "q": 0, "r": 0},
        ),
        CharacterKnowledgeObservation(
            character_id=character.id,
            expedition_id=expedition.id,
            target_type="POI",
            target_id=2,
            observed_game_minute=150,
            source_type="DISCOVERY",
            knowledge={"name": "Other map version", "map_version_id": version.id + 999, "q": 0, "r": 0},
        ),
    ])
    db.commit()

    state = PlayerMapService(db).get(expedition.id)
    assert state.pois == []


def test_player_map_requires_position(db: Session, campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=100)
    expedition.current_map_version_id = None
    expedition.current_q = None
    expedition.current_r = None
    db.commit()

    try:
        PlayerMapService(db).get(expedition.id)
    except ConflictError as exc:
        assert "current map position" in str(exc)
    else:
        raise AssertionError("Expected ConflictError")


def test_player_map_bootstrap_initializes_legacy_active_expedition(db: Session, campaign):
    world_map, version, source, destination = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=90)
    assert character is not None
    assert PlayerMapService(db).get(expedition.id).hexes == []

    initialized, map_count, poi_count = PlayerMapService(db).bootstrap(expedition.id)

    assert initialized is True
    assert map_count >= 1
    assert poi_count == 0
    state = PlayerMapService(db).get(expedition.id)
    coords = {(row.q, row.r): row.discovery_state for row in state.hexes}
    assert coords[(0, 0)] == "VISITED"
    assert (1, 0) in coords


def test_player_map_bootstrap_is_idempotent_once_knowledge_exists(db: Session, campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=90)

    assert PlayerMapService(db).bootstrap(expedition.id)[0] is True
    initialized, map_count, poi_count = PlayerMapService(db).bootstrap(expedition.id)

    assert initialized is False
    assert map_count == 0
    assert poi_count == 0
