from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole, MapArea, MapHex, MapVersion, PointOfInterest, User, WorldMap
from dto.dm_dashboard_dto import DMWorldEditorSnapshot
from services.dm_dashboard_service import DMDashboardService


def make_world(db: Session, campaign: Campaign):
    dm = User(username="undo_dm", email="undo_dm@example.com", password_hash="x")
    db.add(dm); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    world = WorldMap(campaign_id=campaign.id, name="Undo map", description=None)
    db.add(world); db.flush()
    version = MapVersion(map_id=world.id, version=1, name="v1", width=5, height=5, hex_size=32, default_terrain_key="PLAIN", effective_from_game_minute=0)
    db.add(version); db.commit()
    return dm, world, version


def test_world_editor_snapshot_restore_round_trips_semantic_state(db: Session, campaign: Campaign):
    dm, _, version = make_world(db, campaign)
    service = DMDashboardService(db)
    h = service._ensure_map_hex(version, 0, 0)
    db.add(PointOfInterest(feature_id=7, hex_id=h.id, name="Old shrine", kind="RUIN", dm_description="x", is_landmark=False))
    db.commit()
    snap = DMWorldEditorSnapshot.model_validate(service.world_editor_snapshot(campaign.id, dm.id, version.id))

    poi = db.scalar(select(PointOfInterest).where(PointOfInterest.hex_id == h.id))
    poi.name = "Changed"
    db.add(MapArea(map_version_id=version.id, feature_type="LAKE", feature_id=3, name="Temporary", cells=[{"q": 1, "r": 0}], extra_data={}))
    db.commit()

    service.restore_world_editor_snapshot(campaign.id, dm.id, version.id, snap)
    workbench = service.get_map_workbench(campaign.id, dm.id, version.id)
    assert [p.name for p in workbench.pois] == ["Old shrine"]
    assert workbench.areas == []


def test_delete_on_hex_removes_poi_and_only_that_lake_cell(db: Session, campaign: Campaign):
    dm, _, version = make_world(db, campaign)
    service = DMDashboardService(db)
    h = service._ensure_map_hex(version, 0, 0)
    db.add(PointOfInterest(feature_id=11, hex_id=h.id, name="Marker", kind=None, dm_description=None, is_landmark=False))
    db.add(MapArea(map_version_id=version.id, feature_type="LAKE", feature_id=4, name="Lake", cells=[{"q": 0, "r": 0}, {"q": 1, "r": 0}], extra_data={}))
    db.commit()

    service.clear_hex_features(campaign.id, dm.id, version.id, 0, 0)

    assert db.scalar(select(PointOfInterest).where(PointOfInterest.hex_id == h.id)) is None
    area = db.scalar(select(MapArea).where(MapArea.map_version_id == version.id, MapArea.feature_id == 4))
    assert area is not None
    assert area.cells == [{"q": 1, "r": 0}]


def test_world_editor_frontend_has_global_history_and_hex_delete():
    js = Path("static/js/world.js").read_text()
    html = Path("static/world.html").read_text()
    assert "undoStack" in js and "redoStack" in js
    assert "world-editor-snapshot" in js
    assert "clearSelectedHex" in js
    assert "hex-features" in js
    assert "e.altKey" in js
    assert "area=(workbench?.areas||[]).find" in js
    assert "/js/world.js?v=444" in html
