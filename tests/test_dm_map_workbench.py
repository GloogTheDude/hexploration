from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole, MapEdge, MapHex, MapVersion, PointOfInterest, User, WorldMap
from dto.dm_dashboard_dto import DMFeatureEdgeCreate, DMPOICreate, DMPOIUpdate, DMTargetWorldEventCreate
from services.dm_dashboard_service import DMDashboardService
from services.errors import ForbiddenOperationError


def make_dm(db: Session, campaign: Campaign, suffix: str = "mapdm") -> User:
    user = User(username=f"{suffix}", email=f"{suffix}@example.com", password_hash="x")
    db.add(user); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=user.id, role=CampaignRole.DM))
    db.commit()
    return user


def make_map(db: Session, campaign: Campaign):
    world_map = WorldMap(campaign_id=campaign.id, name="Workbench", description=None)
    db.add(world_map); db.flush()
    version = MapVersion(map_id=world_map.id, version=1, name="v1", width=2, height=1, hex_size=32, effective_from_game_minute=0)
    db.add(version); db.flush()
    h0 = MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={})
    h1 = MapHex(map_version_id=version.id, q=1, r=0, terrain_key="FOREST", elevation=1, visibility_score=2, travel_cost=1.5, extra_data={})
    db.add_all([h0, h1]); db.commit()
    return world_map, version, h0, h1


def test_dm_map_workbench_returns_hexes_pois_and_edges(db: Session, campaign):
    dm = make_dm(db, campaign)
    _, version, h0, _ = make_map(db, campaign)
    db.add(PointOfInterest(feature_id=1, hex_id=h0.id, name="Shrine", kind="SHRINE", dm_description="secret", is_landmark=True))
    db.add(MapEdge(map_version_id=version.id, from_q=0, from_r=0, to_q=1, to_r=0, feature_type="ROAD", feature_id=4, name="Old road", extra_data={}))
    db.commit()

    result = DMDashboardService(db).get_map_workbench(campaign.id, dm.id, version.id)

    assert len(result.hexes) == 2
    assert result.pois[0].name == "Shrine"
    assert result.pois[0].q == 0
    assert result.edges[0].feature_id == 4


def test_dm_can_create_and_update_poi_by_hex_coordinates(db: Session, campaign):
    dm = make_dm(db, campaign, "poi_dm")
    _, version, _, _ = make_map(db, campaign)
    service = DMDashboardService(db)

    poi = service.create_poi(campaign.id, dm.id, version.id, DMPOICreate(q=1, r=0, name="watch tower", kind="ruin", is_landmark=False))
    updated = service.update_poi(campaign.id, dm.id, poi.id, DMPOIUpdate(name="Watch Tower", is_landmark=True))

    assert updated.name == "Watch Tower"
    assert updated.kind == "RUIN"
    assert updated.is_landmark is True


def test_dm_feature_edge_auto_allocates_campaign_feature_id(db: Session, campaign):
    dm = make_dm(db, campaign, "edge_dm")
    _, version, _, _ = make_map(db, campaign)
    db.add(MapEdge(map_version_id=version.id, from_q=0, from_r=0, to_q=1, to_r=0, feature_type="BRIDGE", feature_id=7, name="Existing", extra_data={}))
    db.commit()
    # Need a second adjacent pair, so add another hex and create on 1,0 -> 2,0.
    db.add(MapHex(map_version_id=version.id, q=2, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()

    edge = DMDashboardService(db).create_feature_edge(campaign.id, dm.id, version.id, DMFeatureEdgeCreate(from_q=1, from_r=0, to_q=2, to_r=0, feature_type="bridge", name="New bridge"))

    assert edge.feature_type == "BRIDGE"
    assert edge.feature_id == 8


def test_dm_feature_events_target_semantic_feature_not_internal_edge(db: Session, campaign):
    dm = make_dm(db, campaign, "event_dm")
    _, version, h0, _ = make_map(db, campaign)
    poi = PointOfInterest(feature_id=2, hex_id=h0.id, name="Gate", kind="FORT", dm_description=None, is_landmark=False)
    edge = MapEdge(map_version_id=version.id, from_q=0, from_r=0, to_q=1, to_r=0, feature_type="BRIDGE", feature_id=17, name="Gate bridge", extra_data={})
    db.add_all([poi, edge]); db.commit()
    service = DMDashboardService(db)

    poi_event = service.create_poi_world_event(campaign.id, dm.id, poi.id, DMTargetWorldEventCreate(game_minute=100, event_type="POI_DESTROYED", payload={}, dm_note=None))
    edge_event = service.create_edge_world_event(campaign.id, dm.id, edge.id, DMTargetWorldEventCreate(game_minute=120, event_type="BRIDGE_DESTROYED", payload={}, dm_note=None))

    assert (poi_event.target_type, poi_event.target_id) == ("POI", poi.feature_id)
    assert (edge_event.target_type, edge_event.target_id) == ("BRIDGE", 17)


def test_map_workbench_rejects_non_dm(db: Session, campaign):
    player = User(username="not_dm", email="not_dm@example.com", password_hash="x")
    db.add(player); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER))
    _, version, _, _ = make_map(db, campaign)
    db.commit()

    try:
        DMDashboardService(db).get_map_workbench(campaign.id, player.id, version.id)
    except ForbiddenOperationError:
        pass
    else:
        raise AssertionError("Expected DM-only map workbench to reject player")
