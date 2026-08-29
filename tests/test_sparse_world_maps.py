from sqlalchemy import func, select

from db.models import MapHex
from models.constants import FOREST
from models.hexmap import Hexmap
from services.map_persistence_service import MapPersistenceService


def test_10000_square_map_persists_only_materialized_overrides(db, campaign):
    import routes.map_routes as map_routes

    map_routes.hexmap = Hexmap(10_000, 10_000, 16)
    map_routes.hexmap.paint_hex(0, 0, FOREST)

    world_map, version, logical_count = MapPersistenceService(db).snapshot_current_editor_map(
        campaign_id=campaign.id,
        name="World",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
    )

    stored = db.scalar(select(func.count(MapHex.id)).where(MapHex.map_version_id == version.id))
    assert logical_count == 100_000_000
    assert stored == 1
    assert version.default_terrain_key == "SEA"


def test_sparse_world_map_load_keeps_logical_dimensions_without_dense_allocation(db, campaign):
    import routes.map_routes as map_routes

    map_routes.hexmap = Hexmap(10_000, 10_000, 16)
    map_routes.hexmap.paint_hex(12, -6, FOREST)
    _, version, _ = MapPersistenceService(db).snapshot_current_editor_map(
        campaign_id=campaign.id,
        name="World",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
    )

    _, _, logical_count = MapPersistenceService(db).load_version_into_editor(version.id)
    assert logical_count == 100_000_000
    assert map_routes.hexmap.width == 10_000
    assert map_routes.hexmap.height == 10_000
    assert len(map_routes.hexmap.hexes) == 1
    assert map_routes.hexmap.get_hex(12, -6).terrain.type == FOREST.type


def test_sparse_world_export_is_bounded(db, campaign):
    import routes.map_routes as map_routes
    from services.map_export_service import MapExportService

    map_routes.hexmap = Hexmap(10_000, 10_000, 16)
    _, version, _ = MapPersistenceService(db).snapshot_current_editor_map(
        campaign_id=campaign.id, name="World export", description=None,
        version_name="v1", effective_from_game_minute=0,
    )
    data, media, filename = MapExportService(db).render(version.id, "png")
    assert media == "image/png"
    assert filename.endswith(".png")
    assert len(data) < 2_000_000
