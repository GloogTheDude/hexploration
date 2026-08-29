from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import MapEdge, MapFeature, MapHex, MapVersion, PointOfInterest, WorldMap
from services.errors import NotFoundError


class MapFeatureService:
    """Allocate and register semantic feature identities.

    WorldEvent.target_id continues to use a compact integer, but that integer is
    now explicitly registered per campaign + feature type and survives concrete
    MapVersion rows being recreated.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def normalize_type(feature_type: str) -> str:
        value = feature_type.strip().upper()
        if not value:
            raise ValueError("feature_type cannot be empty")
        return value

    def ensure(
        self,
        *,
        campaign_id: int,
        map_id: int,
        feature_type: str,
        feature_id: int,
    ) -> MapFeature:
        feature_type = self.normalize_type(feature_type)
        if feature_id <= 0:
            raise ValueError("feature_id must be positive")
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != campaign_id:
            raise ValueError("Map does not belong to campaign")

        existing = self.db.scalar(
            select(MapFeature).where(
                MapFeature.campaign_id == campaign_id,
                MapFeature.feature_type == feature_type,
                MapFeature.feature_id == feature_id,
            )
        )
        if existing is not None:
            if existing.map_id != map_id:
                raise ValueError(
                    f"{feature_type} #{feature_id} is already registered on another map"
                )
            return existing

        feature = MapFeature(
            campaign_id=campaign_id,
            map_id=map_id,
            feature_type=feature_type,
            feature_id=feature_id,
        )
        self.db.add(feature)
        self.db.flush()
        return feature

    def allocate(self, *, campaign_id: int, map_id: int, feature_type: str) -> MapFeature:
        feature_type = self.normalize_type(feature_type)
        registry_max = self.db.scalar(
            select(func.max(MapFeature.feature_id)).where(
                MapFeature.campaign_id == campaign_id,
                MapFeature.feature_type == feature_type,
            )
        ) or 0
        if feature_type == "POI":
            concrete_max = self.db.scalar(
                select(func.max(PointOfInterest.feature_id))
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .join(MapVersion, MapHex.map_version_id == MapVersion.id)
                .join(WorldMap, MapVersion.map_id == WorldMap.id)
                .where(WorldMap.campaign_id == campaign_id)
            ) or 0
        else:
            concrete_max = self.db.scalar(
                select(func.max(MapEdge.feature_id))
                .join(MapVersion, MapEdge.map_version_id == MapVersion.id)
                .join(WorldMap, MapVersion.map_id == WorldMap.id)
                .where(
                    WorldMap.campaign_id == campaign_id,
                    MapEdge.feature_type == feature_type,
                )
            ) or 0
        max_id = max(registry_max, concrete_max)
        return self.ensure(
            campaign_id=campaign_id,
            map_id=map_id,
            feature_type=feature_type,
            feature_id=max_id + 1,
        )
