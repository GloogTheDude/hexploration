from sqlalchemy import select

from db.models import CampaignMembership, CampaignRole, MapHex, MapVersion, User, WorldEvent, WorldMap
from dto.dm_dashboard_dto import DMPOICreate
from services.dm_dashboard_service import DMDashboardService


def setup_world(db, campaign, suffix):
    dm = User(username=suffix, email=f"{suffix}@example.com", password_hash="x")
    db.add(dm); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    world_map = WorldMap(campaign_id=campaign.id, name="Temporal map", description=None)
    db.add(world_map); db.flush()
    version = MapVersion(map_id=world_map.id, version=1, name="v1", width=1, height=1, hex_size=32, effective_from_game_minute=0)
    db.add(version); db.flush()
    db.add(MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    return dm, version


def test_new_poi_creates_birth_event_at_active_world_minute(db, campaign):
    dm, version = setup_world(db, campaign, "birth_dm")
    poi = DMDashboardService(db).create_poi(
        campaign.id, dm.id, version.id,
        DMPOICreate(q=0, r=0, name="New village", kind="TOWN", creation_game_minute=9876, is_landmark=True),
    )
    event = db.scalar(select(WorldEvent).where(
        WorldEvent.campaign_id == campaign.id,
        WorldEvent.target_type == "POI",
        WorldEvent.target_id == poi.feature_id,
        WorldEvent.event_type == "POI_CREATED",
    ))
    assert event is not None
    assert event.game_minute == 9876
    assert event.payload == {"visible_at_distance": True}


def test_pristine_poi_with_only_automatic_birth_event_can_still_be_deleted(db, campaign):
    dm, version = setup_world(db, campaign, "delete_birth_dm")
    service = DMDashboardService(db)
    poi = service.create_poi(campaign.id, dm.id, version.id, DMPOICreate(q=0, r=0, name="Temporary", creation_game_minute=42))
    feature_id = poi.feature_id
    service.delete_poi(campaign.id, dm.id, poi.id)
    assert db.scalar(select(WorldEvent.id).where(
        WorldEvent.campaign_id == campaign.id,
        WorldEvent.target_type == "POI",
        WorldEvent.target_id == feature_id,
    )) is None


def test_world_editor_sends_active_minute_when_creating_poi():
    js = open("static/js/world.js", encoding="utf-8").read()
    html = open("static/world.html", encoding="utf-8").read()
    assert "creation_game_minute:worldMinute" in js
    assert "Création / apparition a été ajouté automatiquement" in js
    assert "/js/world.js?v=460" in html
