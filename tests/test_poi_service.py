from sqlalchemy.orm import Session
from db.models import Campaign
from dto.poi_dto import POICreate
from dto.world_event_dto import WorldEventCreate
from services.poi_service import POIService
from services.world_event_service import WorldEventService
from tests.factories import make_map_with_two_hexes

def test_poi_defaults_to_active(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign); poi=POIService(db).create(POICreate(hex_id=h.id,name="Old Tower",kind="RUIN")); s=POIService(db).state_at(poi.id,campaign_id=campaign.id,game_minute=50); assert s.state=="ACTIVE" and s.exists

def test_poi_destroyed_then_rebuilt_is_temporal(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign); ps=POIService(db); poi=ps.create(POICreate(hex_id=h.id,name="Old Tower")); ws=WorldEventService(db)
    ws.create(campaign.id,WorldEventCreate(game_minute=100,event_type="POI_DESTROYED",target_type="POI",target_id=poi.id,payload={}))
    ws.create(campaign.id,WorldEventCreate(game_minute=300,event_type="POI_REBUILT",target_type="POI",target_id=poi.id,payload={}))
    assert ps.state_at(poi.id,campaign_id=campaign.id,game_minute=99).exists
    destroyed = ps.state_at(poi.id,campaign_id=campaign.id,game_minute=200)
    assert not destroyed.exists and destroyed.state == "DESTROYED"
    assert ps.state_at(poi.id,campaign_id=campaign.id,game_minute=350).state=="ACTIVE"

def test_generic_poi_state_change(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign); ps=POIService(db); poi=ps.create(POICreate(hex_id=h.id,name="Fort")); WorldEventService(db).create(campaign.id,WorldEventCreate(game_minute=200,event_type="POI_STATE_CHANGED",target_type="POI",target_id=poi.id,payload={"state":"occupied"})); s=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=200); assert s.state=="OCCUPIED" and s.exists


def test_poi_visibility_changes_independently_from_state(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign)
    ps=POIService(db)
    poi=ps.create(POICreate(hex_id=h.id,name="Lit Village",is_landmark=True))
    ws=WorldEventService(db)
    ws.create(campaign.id,WorldEventCreate(game_minute=100,event_type="POI_DESTROYED",target_type="POI",target_id=poi.feature_id,payload={"visible_at_distance":False}))
    before=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=99)
    destroyed=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=100)
    ws.create(campaign.id,WorldEventCreate(game_minute=200,event_type="POI_VISIBILITY_CHANGED",target_type="POI",target_id=poi.feature_id,payload={"visible_at_distance":True}))
    later=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=200)
    assert before.state=="ACTIVE" and before.visible_at_distance is True
    assert destroyed.state=="DESTROYED" and destroyed.visible_at_distance is False
    assert later.state=="DESTROYED" and later.visible_at_distance is True


def test_poi_created_event_hides_poi_before_creation(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign)
    ps=POIService(db)
    poi=ps.create(POICreate(hex_id=h.id,name="New Settlement",is_landmark=True))
    WorldEventService(db).create(
        campaign.id,
        WorldEventCreate(
            game_minute=518400 + 2*43200 + 6*1440,
            event_type="POI_CREATED",
            target_type="POI",
            target_id=poi.feature_id,
            payload={"visible_at_distance": True},
        ),
    )
    creation_minute=518400 + 2*43200 + 6*1440
    before=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=creation_minute-1)
    at_creation=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=creation_minute)
    assert before.exists is False
    assert at_creation.exists is True
    assert at_creation.state == "ACTIVE"
    assert at_creation.visible_at_distance is True

def test_poi_without_created_event_keeps_legacy_existence(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign)
    ps=POIService(db)
    poi=ps.create(POICreate(hex_id=h.id,name="Ancient Ruin"))
    assert ps.state_at(poi.id,campaign_id=campaign.id,game_minute=0).exists is True
