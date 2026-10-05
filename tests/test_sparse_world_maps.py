from sqlalchemy import func, select

from db.models import MapHex
from services.map_persistence_service import MapPersistenceService


def test_10000_square_map_persists_only_materialized_overrides(db, campaign):
    service = MapPersistenceService(db)
    world_map, version, logical_count = service.create_map(
        campaign_id=campaign.id,
        name="World",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
        width=10_000,
        height=10_000,
        hex_size=16,
    )
    service.paint_hexes(campaign_id=campaign.id, map_id=world_map.id, map_version_id=version.id, centers=[(0, 0)], terrain_key="FOREST", radius=1)

    stored = db.scalar(select(func.count(MapHex.id)).where(MapHex.map_version_id == version.id))
    assert logical_count == 100_000_000
    assert stored == 1
    assert version.default_terrain_key == "SEA"


def test_sparse_world_map_load_keeps_logical_dimensions_without_dense_allocation(db, campaign):
    service = MapPersistenceService(db)
    world_map, version, _ = service.create_map(
        campaign_id=campaign.id,
        name="World",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
        width=10_000,
        height=10_000,
        hex_size=16,
    )
    service.paint_hexes(campaign_id=campaign.id, map_id=world_map.id, map_version_id=version.id, centers=[(12, -6)], terrain_key="FOREST", radius=1)

    logical_count = version.width * version.height
    assert logical_count == 100_000_000
    row = db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == 12, MapHex.r == -6))
    assert row.terrain_key == "FOREST"


def test_sparse_world_export_is_bounded(db, campaign):
    from services.map_export_service import MapExportService

    world_map, version, _ = MapPersistenceService(db).create_map(
        campaign_id=campaign.id, name="World export", description=None,
        version_name="v1", effective_from_game_minute=0,
        width=10_000, height=10_000, hex_size=16,
    )
    data, media, filename = MapExportService(db).render(version.id, "png")
    assert media == "image/png"
    assert filename.endswith(".png")
    assert len(data) < 2_000_000
