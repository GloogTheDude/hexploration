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
    assert not ps.state_at(poi.id,campaign_id=campaign.id,game_minute=200).exists
    assert ps.state_at(poi.id,campaign_id=campaign.id,game_minute=350).state=="ACTIVE"

def test_generic_poi_state_change(db:Session,campaign:Campaign):
    _,v,_,h=make_map_with_two_hexes(db,campaign); ps=POIService(db); poi=ps.create(POICreate(hex_id=h.id,name="Fort")); WorldEventService(db).create(campaign.id,WorldEventCreate(game_minute=200,event_type="POI_STATE_CHANGED",target_type="POI",target_id=poi.id,payload={"state":"occupied"})); s=ps.state_at(poi.id,campaign_id=campaign.id,game_minute=200); assert s.state=="OCCUPIED" and s.exists
