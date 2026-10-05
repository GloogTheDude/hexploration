from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from db.session import get_db
from dto.poi_dto import POICreate, POIResponse, POITemporalStateResponse
from services.errors import NotFoundError
from services.poi_service import POIService
from services.authorization import require_campaign_member, require_hex_dm, require_map_version_dm, require_poi_member
router = APIRouter(tags=["points of interest"])
@router.post("/api/pois", response_model=POIResponse, status_code=status.HTTP_201_CREATED)
def create_poi(data: POICreate, _hex = Depends(require_hex_dm), db: Session=Depends(get_db)):
    try: return POIService(db).create(data)
    except NotFoundError as exc: raise HTTPException(404, str(exc)) from exc
@router.get("/api/map-versions/{map_version_id}/pois", response_model=list[POIResponse])
def list_pois(map_version_id:int, _version = Depends(require_map_version_dm), db:Session=Depends(get_db)): return POIService(db).list_for_map_version(map_version_id)
@router.get("/api/pois/{poi_id}", response_model=POIResponse)
def get_poi(poi_id:int, _poi = Depends(require_poi_member), db:Session=Depends(get_db)):
    try: return POIService(db).get(poi_id)
    except NotFoundError as exc: raise HTTPException(404, str(exc)) from exc
@router.get("/api/campaigns/{campaign_id}/pois/{poi_id}/state", response_model=POITemporalStateResponse)
def poi_state(campaign_id:int, poi_id:int, game_minute:int=Query(ge=0), _membership = Depends(require_campaign_member), _poi = Depends(require_poi_member), db:Session=Depends(get_db)):
    try: s=POIService(db).state_at(poi_id,campaign_id=campaign_id,game_minute=game_minute)
    except NotFoundError as exc: raise HTTPException(404,str(exc)) from exc
    return {"poi":s.poi,"game_minute":s.game_minute,"state":s.state,"exists":s.exists,"visible_at_distance":s.visible_at_distance,"latest_event": None if s.latest_event is None else {"id":s.latest_event.id,"event_type":s.latest_event.event_type,"game_minute":s.latest_event.game_minute,"payload":s.latest_event.payload}}
