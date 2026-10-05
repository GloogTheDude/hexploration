import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import (
    CampaignMembership, CampaignRole, MapEdge, MapHex, MapVersion,
    PointOfInterest, User, WorldMap,
)
from dto.world_event_dto import WorldEventCreate
from services.dm_dashboard_service import DMDashboardService
from services.map_persistence_service import MapPersistenceService
from services.poi_service import POIService
from services.world_event_service import WorldEventService


def make_dm(db: Session, campaign):
    dm = User(username="version_dm", email="version_dm@example.com", password_hash="x")
    db.add(dm); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.commit()
    return dm


def seed_version(db: Session, campaign):
    world_map = WorldMap(campaign_id=campaign.id, name="Semantic map", description=None)
    db.add(world_map); db.flush()
    v1 = MapVersion(map_id=world_map.id, parent_version_id=None, version=1, name="v1", width=2, height=1, hex_size=32, effective_from_game_minute=0)
    db.add(v1); db.flush()
    h0 = MapHex(map_version_id=v1.id, q=-1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={})
    h1 = MapHex(map_version_id=v1.id, q=0, r=0, terrain_key="FOREST", elevation=1, visibility_score=2, travel_cost=1.5, extra_data={})
    db.add_all([h0, h1]); db.flush()
    poi = PointOfInterest(feature_id=5, hex_id=h0.id, name="Old Tower", kind="RUIN", dm_description="secret", is_landmark=True)
    edge = MapEdge(map_version_id=v1.id, from_q=-1, from_r=0, to_q=0, to_r=0, feature_type="BRIDGE", feature_id=17, name="Old Bridge", extra_data={})
    db.add_all([poi, edge]); db.commit()
    return world_map, v1, poi, edge


def test_new_map_version_preserves_semantic_poi_and_edge_ids(db: Session, campaign):
    world_map, v1, poi_v1, edge_v1 = seed_version(db, campaign)
    _, v2, count, pois, edges = MapPersistenceService(db).clone_map_version(
        map_id=world_map.id,
        parent_version_id=v1.id,
        version_name="v2",
        effective_from_game_minute=100,
    )

    poi_v2 = db.scalar(select(PointOfInterest).join(MapHex).where(MapHex.map_version_id == v2.id))
    edge_v2 = db.scalar(select(MapEdge).where(MapEdge.map_version_id == v2.id))
    assert (v2.version, v2.parent_version_id, count, pois, edges) == (2, v1.id, 2, 1, 1)
    assert poi_v2.id != poi_v1.id
    assert poi_v2.feature_id == poi_v1.feature_id == 5
    assert edge_v2.id != edge_v1.id
    assert (edge_v2.feature_type, edge_v2.feature_id) == ("BRIDGE", 17)


def test_world_event_on_old_poi_identity_resolves_on_new_version(db: Session, campaign):
    world_map, v1, poi_v1, _ = seed_version(db, campaign)
    _, v2, *_ = MapPersistenceService(db).clone_map_version(
        map_id=world_map.id, parent_version_id=v1.id, version_name="v2", effective_from_game_minute=100
    )
    poi_v2 = db.scalar(select(PointOfInterest).join(MapHex).where(MapHex.map_version_id == v2.id))
    WorldEventService(db).create(campaign.id, WorldEventCreate(
        game_minute=50, event_type="POI_DESTROYED", target_type="POI", target_id=poi_v1.feature_id, payload={}
    ))
    state = POIService(db).state_at(poi_v2.id, campaign_id=campaign.id, game_minute=150)
    assert state.state == "DESTROYED"
    assert state.exists is False


def test_dm_can_load_persisted_version_into_editor(db: Session, campaign):
    dm = make_dm(db, campaign)
    _, v1, _, _ = seed_version(db, campaign)
    loaded = DMDashboardService(db).get_map_workbench(campaign.id, dm.id, v1.id)
    assert loaded.map_version_id == v1.id
    assert len(loaded.hexes) == 2
    assert {(row.q, row.r, row.terrain_key) for row in loaded.hexes} == {(-1, 0, "PLAIN"), (0, 0, "FOREST")}


def test_persistent_paint_is_saved_and_cannot_cross_campaigns(db: Session, campaign):
    from services.errors import ForbiddenOperationError

    dm = make_dm(db, campaign)
    # Create a distinct campaign and map without relying on frontend-supplied
    # campaign identifiers for authorization.
    from db.models import Campaign
    other_campaign = Campaign(name="Other campaign", description=None, epoch_name="Day 1")
    db.add(other_campaign)
    db.flush()
    other = WorldMap(campaign_id=other_campaign.id, name="Other map", description=None)
    db.add(other)
    db.flush()
    other_version = MapVersion(map_id=other.id, version=1, name="v1", width=2, height=1, hex_size=32, effective_from_game_minute=0)
    db.add(other_version)
    db.commit()

    service = MapPersistenceService(db)
    with pytest.raises(ForbiddenOperationError, match="does not belong"):
        DMDashboardService(db).paint_persistent_map(
            campaign.id,
            dm.id,
            other.id,
            other_version.id,
            type("Paint", (), {"centers": [type("Center", (), {"q": 0, "r": 0})()], "terrain_key": "FOREST", "radius": 1})(),
        )

    world_map, version, _ = service.create_map(
        campaign_id=campaign.id,
        name="Owned map",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
        width=2,
        height=1,
        hex_size=32,
    )
    service.paint_hexes(campaign_id=campaign.id, map_id=world_map.id, map_version_id=version.id, centers=[(0, 0)], terrain_key="FOREST", radius=1)
    row = db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == 0, MapHex.r == 0))
    assert row is not None and row.terrain_key == "FOREST"


def test_unused_leaf_map_version_can_be_updated_in_place(db: Session, campaign):
    world_map, v1, poi, edge = seed_version(db, campaign)
    service = MapPersistenceService(db)
    service.paint_hexes(campaign_id=campaign.id, map_id=world_map.id, map_version_id=v1.id, centers=[(-1, 0)], terrain_key="HILL", radius=1)
    _, updated, count = service.update_version_metadata(
        map_id=world_map.id,
        map_version_id=v1.id,
        map_name="Updated map",
        version_name="edited v1",
        effective_from_game_minute=0,
    )

    rows = list(db.scalars(select(MapHex).where(MapHex.map_version_id == v1.id)))
    poi_after = db.get(PointOfInterest, poi.id)
    edge_after = db.get(MapEdge, edge.id)
    assert updated.id == v1.id
    assert updated.version == 1
    assert updated.name == "edited v1"
    assert world_map.name == "Updated map"
    assert count == 2
    assert {row.terrain_key for row in rows} == {"HILL", "FOREST"}
    assert poi_after is not None and poi_after.feature_id == 5
    assert edge_after is not None and edge_after.feature_id == 17


def test_map_version_with_child_is_immutable_in_place(db: Session, campaign):
    from services.errors import ConflictError

    world_map, v1, _, _ = seed_version(db, campaign)
    v2 = MapVersion(
        map_id=world_map.id,
        parent_version_id=v1.id,
        version=2,
        name="v2",
        width=2,
        height=1,
        hex_size=32,
        effective_from_game_minute=10,
    )
    db.add(v2)
    db.commit()
    import pytest
    with pytest.raises(ConflictError, match="create a new version"):
        MapPersistenceService(db).update_version_metadata(
            map_id=world_map.id,
            map_version_id=v1.id,
            map_name=world_map.name,
            version_name=v1.name,
            effective_from_game_minute=0,
        )


def test_map_version_update_cannot_move_before_parent_time(db: Session, campaign):
    from services.errors import ConflictError

    world_map, v1, _, _ = seed_version(db, campaign)
    v1.effective_from_game_minute = 100
    db.flush()
    v2 = MapVersion(
        map_id=world_map.id,
        parent_version_id=v1.id,
        version=2,
        name="v2",
        width=2,
        height=1,
        hex_size=32,
        effective_from_game_minute=100,
    )
    db.add(v2)
    db.commit()

    import pytest

    with pytest.raises(ConflictError, match="after its parent"):
        MapPersistenceService(db).update_version_metadata(
            map_id=world_map.id,
            map_version_id=v2.id,
            map_name=world_map.name,
            version_name=v2.name,
            effective_from_game_minute=50,
        )


def test_tracked_editor_update_only_persists_dirty_hexes(db: Session, campaign):
    world_map, v1, _, _ = seed_version(db, campaign)
    service = MapPersistenceService(db)
    service.paint_hexes(campaign_id=campaign.id, map_id=world_map.id, map_version_id=v1.id, centers=[(-1, 0)], terrain_key="HILL", radius=1)
    service.update_version_metadata(
        map_id=world_map.id,
        map_version_id=v1.id,
        map_name=world_map.name,
        version_name=v1.name,
        effective_from_game_minute=0,
    )

    rows = {(row.q, row.r): row for row in db.scalars(select(MapHex).where(MapHex.map_version_id == v1.id))}
    assert rows[(-1, 0)].terrain_key == "HILL"
    assert rows[(0, 0)].terrain_key == "FOREST"
