from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Campaign, MapHex, MapVersion, WorldMap
from models.constants import BASE_TERRAINS
from services.errors import NotFoundError


class MapPersistenceError(Exception):
    pass


class MapPersistenceService:
    """
    Bridge between the existing in-memory editor and the persistent map model.

    Terrain.travel_cost is copied into MapHex.travel_cost when a snapshot is
    created. This freezes the movement rules for that map version, which is
    useful for historical consistency.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _terrain_key(terrain: object) -> str:
        for key, known in BASE_TERRAINS.items():
            if terrain is known:
                return key

        terrain_type = getattr(terrain, "type", None)
        if terrain_type is not None:
            for key, known in BASE_TERRAINS.items():
                if getattr(known, "type", None) == terrain_type:
                    return key

        raise MapPersistenceError(
            f"Unable to resolve terrain key for terrain {terrain!r}"
        )

    @staticmethod
    def _travel_cost(terrain: object) -> float:
        if not hasattr(terrain, "travel_cost"):
            raise MapPersistenceError(
                f"Terrain {terrain!r} has no travel_cost attribute"
            )

        value = float(getattr(terrain, "travel_cost"))

        if value <= 0:
            raise MapPersistenceError(
                "Terrain travel_cost must be greater than 0"
            )

        return value

    def snapshot_current_editor_map(
        self,
        *,
        campaign_id: int,
        name: str,
        description: str | None,
        version_name: str | None,
        effective_from_game_minute: int,
    ) -> tuple[WorldMap, MapVersion, int]:
        if self.db.get(Campaign, campaign_id) is None:
            raise NotFoundError("Campaign not found")

        # Import the module because /api/newmap reassigns map_routes.hexmap.
        import routes.map_routes as map_routes

        editor_map = map_routes.hexmap

        world_map = WorldMap(
            campaign_id=campaign_id,
            name=name.strip(),
            description=description,
        )
        self.db.add(world_map)
        self.db.flush()

        version = MapVersion(
            map_id=world_map.id,
            parent_version_id=None,
            version=1,
            name=version_name,
            width=editor_map.width,
            height=editor_map.height,
            hex_size=editor_map.hex_size,
            effective_from_game_minute=effective_from_game_minute,
        )
        self.db.add(version)
        self.db.flush()

        count = 0

        for editor_hex in editor_map.hexes.values():
            terrain = editor_hex.terrain

            self.db.add(
                MapHex(
                    map_version_id=version.id,
                    q=editor_hex.q,
                    r=editor_hex.r,
                    terrain_key=self._terrain_key(terrain),
                    elevation=int(getattr(terrain, "elevation", 0)),
                    travel_cost=self._travel_cost(terrain),
                    extra_data={},
                )
            )

            count += 1

        self.db.commit()
        self.db.refresh(world_map)
        self.db.refresh(version)

        return world_map, version, count
