import pytest
from pydantic import ValidationError
from sqlalchemy import select

from db.models import MapHex, MapVersion, WorldMap
from dto.movement_dto import MapSnapshotCreate
from models.hexmap import Hexmap
from services.map_persistence_service import MapPersistenceService
from services.errors import NotFoundError


def test_world_creation_persists_map_and_initial_version(db, campaign):
    import routes.map_routes as map_routes

    previous_map = map_routes.hexmap
    try:
        map_routes.hexmap = Hexmap(2, 3, 32)
        world_map, version, hex_count = MapPersistenceService(db).snapshot_current_editor_map(
            campaign_id=campaign.id,
            name="  First World  ",
            description="The campaign world",
            version_name="Initial",
            effective_from_game_minute=0,
        )
    finally:
        map_routes.hexmap = previous_map

    assert world_map.campaign_id == campaign.id
    assert world_map.name == "First World"
    assert world_map.description == "The campaign world"
    assert version.map_id == world_map.id
    assert version.version == 1
    assert version.parent_version_id is None
    assert (version.width, version.height, version.hex_size) == (2, 3, 32)
    assert version.default_terrain_key == "SEA"
    assert version.effective_from_game_minute == 0
    assert hex_count == 6
    assert db.scalar(select(MapHex.id).where(MapHex.map_version_id == version.id)) is None


def test_world_creation_rejects_unknown_campaign(db):
    import routes.map_routes as map_routes

    with pytest.raises(NotFoundError, match="Campaign not found"):
        MapPersistenceService(db).snapshot_current_editor_map(
            campaign_id=999999,
            name="World",
            description=None,
            version_name="Initial",
            effective_from_game_minute=0,
        )


def test_world_creation_rejects_negative_effective_time(db, campaign):
    with pytest.raises(ValueError, match="must be >= 0"):
        MapPersistenceService(db).snapshot_current_editor_map(
            campaign_id=campaign.id,
            name="World",
            description=None,
            version_name="Initial",
            effective_from_game_minute=-1,
        )


@pytest.mark.parametrize("dto", [MapSnapshotCreate,])
def test_world_creation_rejects_whitespace_only_name(dto):
    with pytest.raises(ValidationError):
        dto(name="   ")
