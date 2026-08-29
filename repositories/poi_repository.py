from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import MapHex, PointOfInterest

class POIRepository:
    def __init__(self, db: Session): self.db = db
    def get(self, poi_id: int): return self.db.get(PointOfInterest, poi_id)
    def get_hex(self, hex_id: int): return self.db.get(MapHex, hex_id)
    def add(self, poi: PointOfInterest): self.db.add(poi); self.db.flush(); return poi
    def list_for_map_version(self, map_version_id: int):
        stmt = select(PointOfInterest).join(MapHex).where(MapHex.map_version_id == map_version_id).order_by(PointOfInterest.id)
        return list(self.db.scalars(stmt))
