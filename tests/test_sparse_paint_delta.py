import pytest
from sqlalchemy import select

from db.models import CampaignMembership, CampaignRole, MapHex, PointOfInterest, User
from services.dm_dashboard_service import DMDashboardService
from services.errors import ForbiddenOperationError
from services.map_persistence_service import MapPersistenceService


def make_dm(db, campaign, suffix="paint_dm"):
    dm = User(username=suffix, email=f"{suffix}@example.com", password_hash="x")
    db.add(dm)
    db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.commit()
    return dm


def make_sparse_map(db, campaign):
    return MapPersistenceService(db).create_map(
        campaign_id=campaign.id,
        name="Sparse paint map",
        description=None,
        version_name="v1",
        effective_from_game_minute=0,
        width=4,
        height=4,
        hex_size=32,
    )


def test_exact_batch_deduplicates_and_returns_sparse_delta(db, campaign):
    world_map, version, _ = make_sparse_map(db, campaign)
    service = MapPersistenceService(db)

    created = service.paint_hexes_exact_delta(
        campaign_id=campaign.id,
        map_id=world_map.id,
        map_version_id=version.id,
        changes=[(0, 0, "FOREST"), (0, 0, "HILL"), (1, 0, "SEA")],
    )

    assert [(row["q"], row["r"], row["terrain_key"]) for row in created["upserted"]] == [(0, 0, "HILL")]
    assert created["removed"] == []
    assert db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == 0, MapHex.r == 0)).terrain_key == "HILL"
    assert db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == 1, MapHex.r == 0)) is None

    removed = service.paint_hexes_exact_delta(
        campaign_id=campaign.id,
        map_id=world_map.id,
        map_version_id=version.id,
        changes=[(0, 0, "SEA")],
    )
    assert removed["upserted"] == []
    assert removed["removed"] == [{"q": 0, "r": 0}]


def test_exact_batch_preserves_poi_support_hex_when_reset_to_default(db, campaign):
    world_map, version, _ = make_sparse_map(db, campaign)
    service = MapPersistenceService(db)
    service.paint_hexes_exact_delta(
        campaign_id=campaign.id,
        map_id=world_map.id,
        map_version_id=version.id,
        changes=[(0, 0, "FOREST")],
    )
    row = db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == 0, MapHex.r == 0))
    db.add(PointOfInterest(feature_id=1, hex_id=row.id, name="Shrine", is_landmark=False))
    db.commit()

    delta = service.paint_hexes_exact_delta(
        campaign_id=campaign.id,
        map_id=world_map.id,
        map_version_id=version.id,
        changes=[(0, 0, "SEA")],
    )

    assert delta["removed"] == []
    assert delta["upserted"][0]["terrain_key"] == "SEA"
    assert db.scalar(select(PointOfInterest).where(PointOfInterest.hex_id == row.id)) is not None
    assert db.get(MapHex, row.id).terrain_key == "SEA"


def test_exact_batch_is_atomic_before_persisting_any_change(db, campaign):
    world_map, version, _ = make_sparse_map(db, campaign)
    service = MapPersistenceService(db)

    with pytest.raises(ValueError, match="outside the map"):
        service.paint_hexes_exact_delta(
            campaign_id=campaign.id,
            map_id=world_map.id,
            map_version_id=version.id,
            changes=[(0, 0, "FOREST"), (999, 999, "HILL")],
        )

    assert db.scalar(select(MapHex).where(MapHex.map_version_id == version.id)) is None


def test_exact_batch_rejects_invalid_terrain_and_empty_batch_is_a_noop(db, campaign):
    world_map, version, _ = make_sparse_map(db, campaign)
    service = MapPersistenceService(db)

    assert service.paint_hexes_exact_delta(
        campaign_id=campaign.id, map_id=world_map.id, map_version_id=version.id, changes=[]
    ) == {"upserted": [], "removed": []}
    with pytest.raises(ValueError, match="Unknown terrain"):
        service.paint_hexes_exact_delta(
            campaign_id=campaign.id,
            map_id=world_map.id,
            map_version_id=version.id,
            changes=[(0, 0, "NOT_A_TERRAIN")],
        )


def test_dashboard_batch_keeps_campaign_and_dm_authorization(db, campaign):
    dm = make_dm(db, campaign, "authorized_paint_dm")
    world_map, version, _ = make_sparse_map(db, campaign)
    service = DMDashboardService(db)
    data = type("Paint", (), {"q": 0, "r": 0, "terrain_key": "FOREST"})()

    delta = service.paint_persistent_map_exact(campaign.id, dm.id, world_map.id, version.id, [data])
    assert delta["upserted"][0]["terrain_key"] == "FOREST"

    player = User(username="paint_player", email="paint_player@example.com", password_hash="x")
    db.add(player)
    db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER))
    db.commit()
    with pytest.raises(ForbiddenOperationError):
        service.paint_persistent_map_exact(campaign.id, player.id, world_map.id, version.id, [data])


def test_dashboard_batch_hides_a_version_from_another_campaign(db, campaign):
    dm = make_dm(db, campaign, "cross_campaign_paint_dm")
    other = type(campaign)(name="Other", description=None, epoch_name="Day 1")
    db.add(other)
    db.commit()
    other_map, other_version, _ = make_sparse_map(db, other)
    data = type("Paint", (), {"q": 0, "r": 0, "terrain_key": "FOREST"})()

    with pytest.raises(ForbiddenOperationError):
        DMDashboardService(db).paint_persistent_map_exact(
            campaign.id, dm.id, other_map.id, other_version.id, [data]
        )
