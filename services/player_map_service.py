from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from sqlalchemy import select

from db.models import CharacterKnowledgeObservation, Expedition, ExpeditionStatus, MapArea, MapEdge, MapVersion, WorldMap
from repositories.expedition_repository import ExpeditionRepository
from repositories.knowledge_repository import KnowledgeRepository
from services.errors import ConflictError, NotFoundError
from services.map_knowledge_service import MapKnowledgeService
from services.visibility_service import VisibilityService


@dataclass(frozen=True)
class PlayerMapState:
    expedition: Expedition
    world_map: WorldMap
    map_version: MapVersion
    hexes: list
    pois: list[CharacterKnowledgeObservation]
    edges: list[MapEdge]
    areas: list[dict]
    visible_hex_coords: set[tuple[int, int]]


class PlayerMapService:
    """Build the player-facing map strictly from already-known information.

    The service deliberately does not enumerate canonical MapHex or POI rows.
    Unknown world geometry must remain unknown to the client. Map dimensions are
    metadata only; the rendered tiles come exclusively from fog-of-war knowledge.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.expeditions = ExpeditionRepository(db)
        self.knowledge = KnowledgeRepository(db)
        self.map_knowledge = MapKnowledgeService(db)
        self.visibility = VisibilityService(db)

    @staticmethod
    def _latest_pois(
        observations: list[CharacterKnowledgeObservation],
        *,
        game_minute: int,
        map_version_id: int,
    ) -> list[CharacterKnowledgeObservation]:
        latest: dict[int, CharacterKnowledgeObservation] = {}
        for observation in observations:
            if observation.target_type != "POI":
                continue
            if observation.observed_game_minute > game_minute:
                continue
            if observation.knowledge.get("map_version_id") != map_version_id:
                continue
            previous = latest.get(observation.target_id)
            if previous is None or (
                observation.observed_game_minute,
                observation.id,
            ) > (
                previous.observed_game_minute,
                previous.id,
            ):
                latest[observation.target_id] = observation
        return sorted(
            (item for item in latest.values() if not item.knowledge.get("hidden_from_players", False)),
            key=lambda item: item.target_id,
        )

    def get(self, expedition_id: int) -> PlayerMapState:
        expedition = self.expeditions.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if (
            expedition.current_map_version_id is None
            or expedition.current_q is None
            or expedition.current_r is None
        ):
            raise ConflictError("Expedition has no current map position")

        version = self.db.get(MapVersion, expedition.current_map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != expedition.campaign_id:
            raise ConflictError("Expedition map belongs to another campaign")

        hexes = self.map_knowledge.expedition_map(
            expedition_id=expedition.id,
            map_id=world_map.id,
            as_of_game_minute=expedition.current_game_minute,
        )
        pois = self._latest_pois(
            self.knowledge.list_for_expedition(expedition.id),
            game_minute=expedition.current_game_minute,
            map_version_id=version.id,
        )

        # Roads/rivers are obvious map geometry once both endpoint hexes have
        # actually been observed.  Filtering against the historical knowledge
        # set prevents the player API from leaking canonical geometry outside
        # the explored area.  Temporal events remain separate world truth and
        # are therefore not projected into stale SEEN tiles.
        known_coords = {(row.q, row.r) for row in hexes}
        candidate_edges = list(
            self.db.scalars(
                select(MapEdge)
                .where(MapEdge.map_version_id == version.id)
                .order_by(MapEdge.feature_type, MapEdge.feature_id, MapEdge.segment_index, MapEdge.id)
            )
        )
        edges = [
            edge for edge in candidate_edges
            if (edge.from_q, edge.from_r) in known_coords
            and (edge.to_q, edge.to_r) in known_coords
            and edge.feature_type in {"ROAD", "RIVER", "BRIDGE", "PASSAGE", "TRAVERSAL"}
        ]
        # Area geometry is clipped to cells the group has actually observed.
        # This preserves lakes/wetlands/regions without leaking the unexplored
        # extent of a semantic area.
        candidate_areas = list(
            self.db.scalars(
                select(MapArea)
                .where(MapArea.map_version_id == version.id)
                .order_by(MapArea.feature_type, MapArea.feature_id, MapArea.id)
            )
        )
        areas: list[dict] = []
        for area in candidate_areas:
            cells = [
                {"q": int(cell["q"]), "r": int(cell["r"])}
                for cell in (area.cells or [])
                if (int(cell.get("q", 10**9)), int(cell.get("r", 10**9))) in known_coords
            ]
            if cells:
                areas.append({
                    "feature_type": area.feature_type,
                    "feature_id": area.feature_id,
                    "name": area.name,
                    "cells": cells,
                })
        scan = self.visibility.scan(expedition.id) if expedition.status == ExpeditionStatus.ACTIVE else None
        visible_hex_coords = ({(item.hex.q, item.hex.r) for item in scan.visible_hexes} if scan else set())
        return PlayerMapState(
            expedition=expedition,
            world_map=world_map,
            map_version=version,
            hexes=hexes,
            pois=pois,
            edges=edges,
            areas=areas,
            visible_hex_coords=visible_hex_coords,
        )
    def bootstrap(self, expedition_id: int) -> tuple[bool, int, int]:
        """Initialize fog-of-war for an already-running positioned expedition.

        This is intentionally explicit and idempotent. It does not reconstruct
        past travel: it records only what the party can observe *now*, at the
        expedition current game minute and position.
        """
        state = self.get(expedition_id)
        expedition = state.expedition
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can bootstrap visibility")

        # Re-running visibility bootstrap is intentionally idempotent. This also
        # repairs older sparse-map expeditions whose implicit default terrain
        # (notably SEA) was never materialised/observed by the legacy renderer.
        result = self.visibility.observe_visible_pois(expedition_id)
        created = len(result.map_observations) + len(result.observations)
        return created > 0, len(result.map_observations), len(result.observations)

