from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import CharacterKnowledgeObservation, Expedition, ExpeditionStatus, MapVersion, WorldMap
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
        return sorted(latest.values(), key=lambda item: item.target_id)

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
        return PlayerMapState(
            expedition=expedition,
            world_map=world_map,
            map_version=version,
            hexes=hexes,
            pois=pois,
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

        # Existing map knowledge means this expedition has already entered the
        # fog-of-war system. Re-running bootstrap should not manufacture a new
        # historical observation.
        if state.hexes:
            return False, 0, 0

        result = self.visibility.observe_visible_pois(expedition_id)
        return True, len(result.map_observations), len(result.observations)

