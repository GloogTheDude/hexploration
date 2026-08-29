from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    Character,
    CharacterMapHexObservation,
    ExpeditionCharacter,
    MapHex,
    MapVersion,
    User,
)
from dto.movement_dto import ExpeditionPositionSet
from services.expedition_movement_service import ExpeditionMovementService
from services.map_knowledge_service import MapKnowledgeService
from services.visibility_service import VisibilityService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _add_character(db: Session, campaign: Campaign, expedition_id: int, minute: int) -> Character:
    user = User(
        username=f"map_knower_{expedition_id}_{minute}",
        email=f"map_knower_{expedition_id}_{minute}@example.com",
        password_hash="x",
    )
    db.add(user)
    db.flush()
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=user.id,
        name="Cartographer",
        race="Human",
        character_class="Ranger",
        level=1,
        description=None,
        current_game_minute=minute,
    )
    db.add(character)
    db.flush()
    db.add(
        ExpeditionCharacter(
            expedition_id=expedition_id,
            character_id=character.id,
            joined_game_minute=minute,
            left_game_minute=None,
        )
    )
    db.commit()
    return character


def test_visibility_records_visited_origin_and_seen_neighbor(db: Session, campaign: Campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=10)
    assert character is not None

    VisibilityService(db).observe_visible_pois(expedition.id)
    known = MapKnowledgeService(db).character_map(character_id=character.id, map_id=world_map.id)
    by_coord = {(row.q, row.r): row for row in known}

    assert by_coord[(0, 0)].discovery_state == "VISITED"
    assert by_coord[(1, 0)].discovery_state == "SEEN"


def test_occluded_hex_is_not_added_to_fog_of_war_knowledge(db: Session, campaign: Campaign):
    world_map, version, source, blocker = make_map_with_two_hexes(db, campaign)
    source.visibility_score = 6
    blocker.terrain_key = "FOREST"
    blocker.visibility_score = 2
    target = MapHex(
        map_version_id=version.id,
        q=2,
        r=0,
        terrain_key="PLAIN",
        elevation=1,
        visibility_score=3,
        travel_cost=1.0,
        extra_data={},
    )
    db.add(target)
    db.commit()
    expedition, character = make_active_expedition(db, campaign, version, game_minute=10)
    assert character is not None

    VisibilityService(db).observe_visible_pois(expedition.id)
    known = MapKnowledgeService(db).character_map(character_id=character.id, map_id=world_map.id)
    assert (2, 0) not in {(row.q, row.r) for row in known}


def test_movement_promotes_seen_hex_to_visited(db: Session, campaign: Campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=10)
    assert character is not None
    visibility = VisibilityService(db)
    visibility.observe_visible_pois(expedition.id)

    before = MapKnowledgeService(db).character_hex(
        character_id=character.id, map_id=world_map.id, q=1, r=0
    )
    assert before.discovery_state == "SEEN"

    ExpeditionMovementService(db).move(
        expedition_id=expedition.id,
        to_q=1,
        to_r=0,
        base_duration_minutes=10,
    )
    after = MapKnowledgeService(db).character_hex(
        character_id=character.id, map_id=world_map.id, q=1, r=0
    )
    assert after.discovery_state == "VISITED"
    assert after.observed_game_minute == 20


def test_unchanged_visibility_does_not_spam_map_history(db: Session, campaign: Campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=10)
    assert character is not None
    visibility = VisibilityService(db)

    first = visibility.observe_visible_pois(expedition.id)
    second = visibility.observe_visible_pois(expedition.id)

    assert len(first.map_observations) == 2
    assert second.map_observations == []
    history = MapKnowledgeService(db).character_history(
        character_id=character.id, map_id=world_map.id, q=1, r=0
    )
    assert len(history) == 1


def test_old_hex_appearance_persists_until_new_version_is_seen(db: Session, campaign: Campaign):
    world_map, version1, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version1, game_minute=10)
    assert character is not None
    VisibilityService(db).observe_visible_pois(expedition.id)

    version2 = MapVersion(
        map_id=world_map.id,
        parent_version_id=version1.id,
        version=2,
        name="v2",
        width=2,
        height=1,
        hex_size=32,
        effective_from_game_minute=100,
    )
    db.add(version2)
    db.flush()
    db.add_all([
        MapHex(
            map_version_id=version2.id, q=0, r=0, terrain_key="PLAIN",
            elevation=1, visibility_score=3, travel_cost=1.0, extra_data={}
        ),
        MapHex(
            map_version_id=version2.id, q=1, r=0, terrain_key="FOREST",
            elevation=1, visibility_score=2, travel_cost=1.5, extra_data={"changed": True}
        ),
    ])
    expedition.current_map_version_id = version2.id
    expedition.current_game_minute = 100
    db.commit()

    service = MapKnowledgeService(db)
    old = service.character_hex(
        character_id=character.id, map_id=world_map.id, q=1, r=0, as_of_game_minute=50
    )
    assert old.terrain_key == "PLAIN"

    VisibilityService(db).observe_visible_pois(expedition.id)
    current = service.character_hex(character_id=character.id, map_id=world_map.id, q=1, r=0)
    assert current.terrain_key == "FOREST"
    assert current.map_version_id == version2.id

    still_old = service.character_hex(
        character_id=character.id, map_id=world_map.id, q=1, r=0, as_of_game_minute=50
    )
    assert still_old.terrain_key == "PLAIN"
    assert len(service.character_history(character_id=character.id, map_id=world_map.id, q=1, r=0)) == 2


def test_visited_state_is_monotonic_when_hex_is_seen_again(db: Session, campaign: Campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=10)
    assert character is not None
    visibility = VisibilityService(db)
    visibility.observe_visible_pois(expedition.id)
    ExpeditionMovementService(db).move(
        expedition_id=expedition.id, to_q=1, to_r=0, base_duration_minutes=10
    )
    ExpeditionMovementService(db).move(
        expedition_id=expedition.id, to_q=0, to_r=0, base_duration_minutes=10
    )

    known = MapKnowledgeService(db).character_hex(
        character_id=character.id, map_id=world_map.id, q=1, r=0
    )
    assert known.discovery_state == "VISITED"


def test_map_visibility_is_shared_with_all_active_expedition_members(db: Session, campaign: Campaign):
    world_map, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, first = make_active_expedition(db, campaign, version, game_minute=10)
    assert first is not None
    second = _add_character(db, campaign, expedition.id, 10)

    VisibilityService(db).observe_visible_pois(expedition.id)
    service = MapKnowledgeService(db)
    first_map = service.character_map(character_id=first.id, map_id=world_map.id)
    second_map = service.character_map(character_id=second.id, map_id=world_map.id)

    assert [(r.q, r.r, r.discovery_state) for r in first_map] == [
        (r.q, r.r, r.discovery_state) for r in second_map
    ]
