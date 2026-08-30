from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole, MapArea, MapEdge, MapFeature, MapHex, MapVersion, User, WorldMap
from dto.dm_dashboard_dto import DMAreaFeatureCreate, DMHexCoord, DMLinearFeatureCreate
from services.dm_dashboard_service import DMDashboardService


def make_dm_and_sparse_map(db: Session, campaign: Campaign):
    dm = User(username="feature_dm", email="feature_dm@example.com", password_hash="x")
    db.add(dm); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    world_map = WorldMap(campaign_id=campaign.id, name="Feature map", description=None)
    db.add(world_map); db.flush()
    version = MapVersion(map_id=world_map.id, version=1, name="v1", width=8, height=8, hex_size=32, default_terrain_key="SEA", effective_from_game_minute=0)
    db.add(version); db.commit()
    return dm, world_map, version


def test_linear_feature_interpolates_waypoints_and_keeps_one_semantic_identity(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    created = DMDashboardService(db).create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(
            feature_type="ROAD", name="King's road",
            waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=0, r=0), DMHexCoord(q=2, r=-1)],
        ),
    )
    assert len(created) >= 4
    assert {edge.feature_id for edge in created} == {created[0].feature_id}
    assert [edge.segment_index for edge in created] == list(range(len(created)))
    assert len(list(db.scalars(select(MapHex).where(MapHex.map_version_id == version.id)))) >= 5


def test_road_and_river_can_share_same_geometric_corridor(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    waypoints = [DMHexCoord(q=-1, r=0), DMHexCoord(q=1, r=-1)]
    road = service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(feature_type="ROAD", name="Riverside road", waypoints=waypoints))
    river = service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(feature_type="RIVER", name="Blue river", waypoints=waypoints))
    assert len(road) == len(river)
    assert {(e.from_q, e.from_r, e.to_q, e.to_r) for e in road} == {(e.from_q, e.from_r, e.to_q, e.to_r) for e in river}
    assert road[0].feature_id != river[0].feature_id or road[0].feature_type != river[0].feature_type


def test_area_feature_persists_selected_cells(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    result = DMDashboardService(db).create_area_feature(
        campaign.id, dm.id, version.id,
        DMAreaFeatureCreate(
            feature_type="LAKE", name="Lake Shadow",
            cells=[DMHexCoord(q=0, r=0), DMHexCoord(q=1, r=0), DMHexCoord(q=1, r=0)],
        ),
    )
    assert result["feature_type"] == "LAKE"
    assert len(result["cells"]) == 2
    row = db.scalar(select(MapArea).where(MapArea.id == result["id"]))
    assert row is not None
    assert row.name == "Lake Shadow"


def test_workbench_exposes_linear_segments_and_areas(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(feature_type="RIVER", name="R", waypoints=[DMHexCoord(q=0, r=0), DMHexCoord(q=1, r=0)]))
    service.create_area_feature(campaign.id, dm.id, version.id, DMAreaFeatureCreate(feature_type="INLAND_SEA", name="Sea", cells=[DMHexCoord(q=0, r=0)]))
    result = service.get_map_workbench(campaign.id, dm.id, version.id)
    assert result.edges[0].feature_type == "RIVER"
    assert result.edges[0].segment_index == 0
    assert result.areas[0].feature_type == "INLAND_SEA"


def test_river_requires_explicit_sea_endpoint(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    db.add_all([
        MapHex(map_version_id=version.id, q=-1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
    ])
    db.commit()
    service = DMDashboardService(db)
    land_only = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="No guessed mouth", waypoints=[DMHexCoord(q=-1, r=0), DMHexCoord(q=0, r=0)]),
    )
    assert len(land_only) == 1
    assert "outlet" not in (land_only[-1].extra_data or {})

    explicit = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Explicit mouth", waypoints=[DMHexCoord(q=0, r=0), DMHexCoord(q=1, r=0)]),
    )
    assert explicit[-1].extra_data["outlet"]["type"] == "SEA"
    assert explicit[-1].extra_data["outlet"]["q"] == 1

def test_river_does_not_extend_when_last_waypoint_is_already_water(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    # Both waypoints are implicit SEA on this sparse version.
    created = DMDashboardService(db).create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(
            feature_type="RIVER", name="Estuary",
            waypoints=[DMHexCoord(q=-1, r=0), DMHexCoord(q=0, r=0)],
        ),
    )
    assert len(created) == 1


def test_river_can_empty_into_explicit_lake_hex(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    db.add_all([
        MapHex(map_version_id=version.id, q=-1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
    ])
    db.commit()
    area = service.create_area_feature(
        campaign.id, dm.id, version.id,
        DMAreaFeatureCreate(feature_type="LAKE", name="Lake", cells=[DMHexCoord(q=1, r=0)]),
    )
    created = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Tributary", waypoints=[DMHexCoord(q=-1, r=0), DMHexCoord(q=1, r=0)]),
    )
    last = max(created, key=lambda edge: edge.segment_index)
    assert (last.extra_data["path_to"]["q"], last.extra_data["path_to"]["r"]) == (1, 0)
    assert last.extra_data["outlet"]["type"] == "LAKE"
    assert last.extra_data["outlet"]["feature_id"] == area["feature_id"]

def test_dm_can_delete_whole_linear_feature_by_one_segment(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    created = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="Temporary road", waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=2, r=-1)]),
    )
    feature_id = created[0].feature_id
    service.delete_linear_feature(campaign.id, dm.id, created[0].id)
    assert list(db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id, MapEdge.feature_type == "ROAD", MapEdge.feature_id == feature_id))) == []


def test_dm_can_delete_area_feature(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    result = service.create_area_feature(
        campaign.id, dm.id, version.id,
        DMAreaFeatureCreate(feature_type="LAKE", name="Mistake", cells=[DMHexCoord(q=0, r=0), DMHexCoord(q=1, r=0)]),
    )
    service.delete_area_feature(campaign.id, dm.id, result["id"])
    assert db.scalar(select(MapArea).where(MapArea.id == result["id"])) is None


def test_river_does_not_guess_across_coastal_gap(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    db.add_all([
        MapHex(map_version_id=version.id, q=-2, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=-1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
        MapHex(map_version_id=version.id, q=1, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}),
    ])
    db.commit()
    created = DMDashboardService(db).create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Coastal river", waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=-1, r=0)]),
    )
    last = max(created, key=lambda edge: edge.segment_index)
    assert (last.extra_data["path_to"]["q"], last.extra_data["path_to"]["r"]) == (-1, 0)
    assert "outlet" not in (last.extra_data or {})

def test_tributary_stops_at_first_existing_river_and_links_downstream(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    # Make the whole test corridor land so automatic SEA completion cannot
    # interfere with the confluence assertion.
    for q, r in [(-2, 1), (-1, 1), (0, 0), (1, 0), (2, 0), (0, 1)]:
        db.add(MapHex(map_version_id=version.id, q=q, r=r, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    service = DMDashboardService(db)
    main = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Main", waypoints=[DMHexCoord(q=-2, r=1), DMHexCoord(q=2, r=0)]),
    )
    main_id = main[0].feature_id

    tributary = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        # Deliberately draw *past* the main river. The stored tributary must
        # stop at the first intersecting river node instead of overlapping it.
        DMLinearFeatureCreate(feature_type="RIVER", name="Tributary", waypoints=[DMHexCoord(q=0, r=1), DMHexCoord(q=0, r=-1)]),
    )
    tributary_id = tributary[0].feature_id
    identity = db.scalar(select(MapFeature).where(
        MapFeature.campaign_id == campaign.id,
        MapFeature.feature_type == "RIVER",
        MapFeature.feature_id == tributary_id,
    ))
    assert identity is not None
    assert identity.downstream_feature_type == "RIVER"
    assert identity.downstream_feature_id == main_id
    last = max(tributary, key=lambda edge: edge.segment_index)
    assert last.extra_data["outlet"]["type"] == "RIVER"
    assert last.extra_data["downstream_river_feature_id"] == main_id

    main_nodes = set()
    for edge in main:
        main_nodes.add((edge.extra_data["path_from"]["q"], edge.extra_data["path_from"]["r"]))
        main_nodes.add((edge.extra_data["path_to"]["q"], edge.extra_data["path_to"]["r"]))
    terminal = (last.extra_data["path_to"]["q"], last.extra_data["path_to"]["r"])
    assert terminal in main_nodes
    # Only the terminal confluence node may overlap; no downstream edge is copied.
    tributary_edges = {
        frozenset({(e.from_q, e.from_r), (e.to_q, e.to_r)}) for e in tributary
    }
    main_edges = {frozenset({(e.from_q, e.from_r), (e.to_q, e.to_r)}) for e in main}
    assert tributary_edges.isdisjoint(main_edges)


def test_river_links_to_existing_river_when_authored_path_reaches_it(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    for q, r in [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (0, 1), (0, 2)]:
        db.add(MapHex(map_version_id=version.id, q=q, r=r, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    service = DMDashboardService(db)
    main = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Main", waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=2, r=0)]),
    )
    trib = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="RIVER", name="Trib", waypoints=[DMHexCoord(q=0, r=2), DMHexCoord(q=0, r=0)]),
    )
    identity = db.scalar(select(MapFeature).where(
        MapFeature.campaign_id == campaign.id, MapFeature.feature_type == "RIVER", MapFeature.feature_id == trib[0].feature_id,
    ))
    assert identity is not None
    assert identity.downstream_feature_id == main[0].feature_id

def test_river_records_water_endpoint_at_start_and_end(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    for q in range(-1, 3):
        db.add(MapHex(map_version_id=version.id, q=q, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    lake = service.create_area_feature(campaign.id, dm.id, version.id, DMAreaFeatureCreate(feature_type="LAKE", name="Lake", cells=[DMHexCoord(q=-1, r=0)]))
    # q=3 is implicit SEA on the sparse map. The DM explicitly selects both water cells.
    created = service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(
        feature_type="RIVER", name="Lake to sea", waypoints=[DMHexCoord(q=-1, r=0), DMHexCoord(q=3, r=0)]
    ))
    first=min(created,key=lambda e:e.segment_index); last=max(created,key=lambda e:e.segment_index)
    assert first.extra_data["source"]["type"] == "LAKE"
    assert first.extra_data["source"]["feature_id"] == lake["feature_id"]
    assert last.extra_data["outlet"]["type"] == "SEA"


def test_cannot_delete_river_that_still_has_tributaries(db: Session, campaign: Campaign):
    from services.errors import ConflictError

    dm, _, version = make_dm_and_sparse_map(db, campaign)
    for q, r in [(-2, 1), (-1, 1), (0, 0), (1, 0), (2, 0), (0, 1)]:
        db.add(MapHex(map_version_id=version.id, q=q, r=r, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    service = DMDashboardService(db)
    main = service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(feature_type="RIVER", name="Main", waypoints=[DMHexCoord(q=-2, r=1), DMHexCoord(q=2, r=0)]))
    service.create_linear_feature(campaign.id, dm.id, version.id, DMLinearFeatureCreate(feature_type="RIVER", name="Trib", waypoints=[DMHexCoord(q=0, r=1), DMHexCoord(q=0, r=-1)]))
    import pytest
    with pytest.raises(ConflictError, match="tributaries"):
        service.delete_linear_feature(campaign.id, dm.id, main[0].id)


def test_merge_connected_roads_keeps_first_semantic_identity(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    first = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="Old north road", waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=0, r=0)]),
    )
    second = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="Road fragment", waypoints=[DMHexCoord(q=0, r=0), DMHexCoord(q=2, r=-1)]),
    )
    first_id, second_id = first[0].feature_id, second[0].feature_id

    merged = service.merge_linear_features(campaign.id, dm.id, [first[0].id, second[0].id])

    assert len(merged) == len(first) + len(second)
    assert {edge.feature_id for edge in merged} == {first_id}
    assert [edge.segment_index for edge in merged] == list(range(len(merged)))
    assert merged[0].name == "Old north road"
    assert db.scalar(select(MapEdge.id).where(
        MapEdge.map_version_id == version.id,
        MapEdge.feature_type == "ROAD",
        MapEdge.feature_id == second_id,
    ).limit(1)) is None
    assert db.scalar(select(MapFeature.id).where(
        MapFeature.campaign_id == campaign.id,
        MapFeature.feature_type == "ROAD",
        MapFeature.feature_id == second_id,
    ).limit(1)) is None


def test_merge_linear_features_rejects_disconnected_roads(db: Session, campaign: Campaign):
    from services.errors import ConflictError
    import pytest

    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    first = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="A", waypoints=[DMHexCoord(q=-3, r=0), DMHexCoord(q=-2, r=0)]),
    )
    second = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="B", waypoints=[DMHexCoord(q=2, r=-1), DMHexCoord(q=3, r=-1)]),
    )

    with pytest.raises(ConflictError, match="not connected"):
        service.merge_linear_features(campaign.id, dm.id, [first[0].id, second[0].id])


def test_merge_connected_branching_roads_into_one_network(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    service = DMDashboardService(db)
    trunk = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="Crossroads", waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=0, r=0)]),
    )
    east = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="East arm", waypoints=[DMHexCoord(q=0, r=0), DMHexCoord(q=2, r=-1)]),
    )
    south = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(feature_type="ROAD", name="South arm", waypoints=[DMHexCoord(q=0, r=0), DMHexCoord(q=0, r=2)]),
    )

    merged = service.merge_linear_features(campaign.id, dm.id, [trunk[0].id, east[0].id, south[0].id])

    assert len(merged) == len(trunk) + len(east) + len(south)
    assert {edge.feature_id for edge in merged} == {trunk[0].feature_id}
    nodes = {}
    for edge in merged:
        data = edge.extra_data or {}
        a = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
        b = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
        for node in ((a["q"], a["r"]), (b["q"], b["r"])):
            nodes[node] = nodes.get(node, 0) + 1
    assert max(nodes.values()) >= 3


def test_merge_branching_rivers_into_one_acyclic_network(db: Session, campaign: Campaign):
    dm, _, version = make_dm_and_sparse_map(db, campaign)
    # Materialize the authored river corridors as land; leave (2, 0) implicit
    # SEA so the retained trunk has one explicit downstream outlet.
    land = [
        (-2, 0), (-1, 0), (0, 0), (1, 0),
        (0, 1), (0, 2),
        (-1, 1), (-1, 2),
    ]
    for q, r in land:
        db.add(MapHex(
            map_version_id=version.id, q=q, r=r, terrain_key="PLAIN",
            elevation=0, visibility_score=3, travel_cost=1.0, extra_data={},
        ))
    db.commit()

    service = DMDashboardService(db)
    trunk = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(
            feature_type="RIVER", name="Main river",
            waypoints=[DMHexCoord(q=-2, r=0), DMHexCoord(q=2, r=0)],
        ),
    )
    north = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(
            feature_type="RIVER", name="North tributary",
            waypoints=[DMHexCoord(q=0, r=2), DMHexCoord(q=0, r=0)],
        ),
    )
    northwest = service.create_linear_feature(
        campaign.id, dm.id, version.id,
        DMLinearFeatureCreate(
            feature_type="RIVER", name="Northwest tributary",
            waypoints=[DMHexCoord(q=-1, r=2), DMHexCoord(q=-1, r=0)],
        ),
    )
    primary_id = trunk[0].feature_id
    absorbed_ids = {north[0].feature_id, northwest[0].feature_id}

    merged = service.merge_linear_features(
        campaign.id, dm.id,
        [trunk[0].id, north[0].id, northwest[0].id],
    )

    assert {edge.feature_id for edge in merged} == {primary_id}
    assert [edge.segment_index for edge in merged] == list(range(len(merged)))
    degree = {}
    outlets = []
    for edge in merged:
        data = edge.extra_data or {}
        a = data["path_from"]
        b = data["path_to"]
        for node in ((a["q"], a["r"]), (b["q"], b["r"])):
            degree[node] = degree.get(node, 0) + 1
        if "outlet" in data:
            outlets.append(data["outlet"])
    assert max(degree.values()) >= 3
    assert len(outlets) == 1
    assert outlets[0]["type"] == "SEA"
    for absorbed_id in absorbed_ids:
        assert db.scalar(select(MapFeature.id).where(
            MapFeature.campaign_id == campaign.id,
            MapFeature.feature_type == "RIVER",
            MapFeature.feature_id == absorbed_id,
        ).limit(1)) is None
