from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Campaign, Character, CharacterStatus, Expedition, ExpeditionCharacter, ExpeditionStatus, MapHex, MapVersion, User, WorldMap

def make_map_with_two_hexes(
    db: Session,
    campaign: Campaign,
    *,
    destination_terrain: str = "PLAIN",
    destination_travel_cost: float = 1.0,
) -> tuple[WorldMap, MapVersion, MapHex, MapHex]:
    world_map = WorldMap(
        campaign_id=campaign.id,
        name="Test Map",
        description=None,
    )
    db.add(world_map)
    db.flush()

    version = MapVersion(
        map_id=world_map.id,
        version=1,
        name="v1",
        width=2,
        height=1,
        hex_size=32,
        effective_from_game_minute=0,
    )
    db.add(version)
    db.flush()

    source = MapHex(
        map_version_id=version.id,
        q=0,
        r=0,
        terrain_key="PLAIN",
        elevation=1,
        travel_cost=1.0,
        extra_data={},
    )
    destination = MapHex(
        map_version_id=version.id,
        q=1,
        r=0,
        terrain_key=destination_terrain,
        elevation=1,
        travel_cost=destination_travel_cost,
        extra_data={},
    )
    db.add_all([source, destination])
    db.commit()
    return world_map, version, source, destination


def make_active_expedition(
    db: Session,
    campaign: Campaign,
    map_version: MapVersion,
    *,
    game_minute: int,
    with_character: bool = True,
) -> tuple[Expedition, Character | None]:
    expedition = Expedition(
        campaign_id=campaign.id,
        name=f"Expedition @ {game_minute}",
        status=ExpeditionStatus.ACTIVE,
        start_game_minute=game_minute,
        current_game_minute=game_minute,
        return_game_minute=None,
        current_map_version_id=map_version.id,
        current_q=0,
        current_r=0,
        weather_key=None,
        transport_key=None,
    )
    db.add(expedition)
    db.flush()

    character = None
    if with_character:
        user = User(
            username=f"pytest_user_{game_minute}_{expedition.id}",
            email=f"pytest_{game_minute}_{expedition.id}@example.com",
            password_hash="not-used-in-service-tests",
        )
        db.add(user)
        db.flush()

        character = Character(
            campaign_id=campaign.id,
            owner_user_id=user.id,
            name="Temporal Walker",
            race="Human",
            character_class="Ranger",
            level=1,
            description=None,
            status=CharacterStatus.ACTIVE,
            current_game_minute=game_minute,
        )
        db.add(character)
        db.flush()

        participant = ExpeditionCharacter(
            expedition_id=expedition.id,
            character_id=character.id,
            joined_game_minute=game_minute,
            left_game_minute=None,
        )
        db.add(participant)

    db.commit()
    return expedition, character
