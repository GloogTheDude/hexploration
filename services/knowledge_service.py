from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import (
    Character,
    CharacterKnowledgeObservation,
    ExpeditionStatus,
    MapHex,
    MapVersion,
    PointOfInterest,
)
from repositories.expedition_repository import ExpeditionRepository
from repositories.knowledge_repository import KnowledgeRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.poi_service import POIService


class KnowledgeService:
    """Character knowledge derived from explicit in-world observations.

    WorldEvent/POI state remains canonical world truth. Knowledge observations
    are immutable snapshots of what a character learned at a specific campaign
    minute. Later changes to world truth do not retroactively change knowledge.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = KnowledgeRepository(db)
        self.expeditions = ExpeditionRepository(db)
        self.pois = POIService(db)

    @staticmethod
    def _normalize_target_type(target_type: str) -> str:
        normalized = target_type.strip().upper()
        if not normalized:
            raise ValueError("target_type cannot be empty")
        return normalized

    def _get_character(self, character_id: int) -> Character:
        character = self.db.get(Character, character_id)
        if character is None:
            raise NotFoundError("Character not found")
        return character

    def _poi_campaign_and_position(
        self,
        poi: PointOfInterest,
    ) -> tuple[int, int, int, int]:
        hex_tile = self.db.get(MapHex, poi.hex_id)
        if hex_tile is None:
            raise NotFoundError("POI map hex not found")

        map_version = self.db.get(MapVersion, hex_tile.map_version_id)
        if map_version is None or map_version.map is None:
            raise NotFoundError("POI map version not found")

        return map_version.map.campaign_id, map_version.id, hex_tile.q, hex_tile.r

    def discover_poi(
        self,
        expedition_id: int,
        poi_id: int,
    ) -> list[CharacterKnowledgeObservation]:
        expedition = self.expeditions.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can discover a POI")
        if (
            expedition.current_map_version_id is None
            or expedition.current_q is None
            or expedition.current_r is None
        ):
            raise ConflictError("Expedition has no current map position")

        poi = self.pois.get(poi_id)
        poi_campaign_id, map_version_id, q, r = self._poi_campaign_and_position(poi)

        if poi_campaign_id != expedition.campaign_id:
            raise ForbiddenOperationError(
                "POI and expedition must belong to the same campaign"
            )
        if map_version_id != expedition.current_map_version_id:
            raise ConflictError("POI is not on the expedition's current map version")
        if (q, r) != (expedition.current_q, expedition.current_r):
            raise ConflictError("POI can only be discovered from its current hex")

        participants = [
            participant
            for participant in self.expeditions.list_participants(expedition_id)
            if participant.left_game_minute is None
            and participant.joined_game_minute <= expedition.current_game_minute
        ]
        if not participants:
            raise ConflictError("Expedition has no active characters")

        state = self.pois.state_at(
            poi_id,
            campaign_id=expedition.campaign_id,
            game_minute=expedition.current_game_minute,
        )
        snapshot = {
            "name": poi.name,
            "kind": poi.kind,
            "map_version_id": map_version_id,
            "q": q,
            "r": r,
            "state": state.state,
            "exists": state.exists,
            "world_event_id": (
                state.latest_event.id if state.latest_event is not None else None
            ),
        }

        observations: list[CharacterKnowledgeObservation] = []
        for participant in participants:
            existing = self.repo.get_exact(
                character_id=participant.character_id,
                expedition_id=expedition.id,
                target_type="POI",
                target_id=poi.feature_id,
                observed_game_minute=expedition.current_game_minute,
            )
            if existing is not None:
                observations.append(existing)
                continue

            observation = CharacterKnowledgeObservation(
                character_id=participant.character_id,
                expedition_id=expedition.id,
                target_type="POI",
                target_id=poi.feature_id,
                observed_game_minute=expedition.current_game_minute,
                source_type="DISCOVERY",
                knowledge=dict(snapshot),
            )
            self.repo.add(observation)
            observations.append(observation)

        self.db.commit()
        for observation in observations:
            self.db.refresh(observation)
        return observations

    def latest_for_target(
        self,
        character_id: int,
        target_type: str,
        target_id: int,
        *,
        as_of_game_minute: int | None = None,
    ) -> CharacterKnowledgeObservation:
        self._get_character(character_id)
        if as_of_game_minute is not None and as_of_game_minute < 0:
            raise ValueError("as_of_game_minute must be >= 0")

        observation = self.repo.latest_for_target(
            character_id=character_id,
            target_type=self._normalize_target_type(target_type),
            target_id=target_id,
            as_of_game_minute=as_of_game_minute,
        )
        if observation is None:
            raise NotFoundError("Character has no knowledge of this target")
        return observation

    def history_for_target(
        self,
        character_id: int,
        target_type: str,
        target_id: int,
    ) -> list[CharacterKnowledgeObservation]:
        self._get_character(character_id)
        return self.repo.history_for_target(
            character_id=character_id,
            target_type=self._normalize_target_type(target_type),
            target_id=target_id,
        )

    def list_latest_for_character(
        self,
        character_id: int,
        *,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterKnowledgeObservation]:
        self._get_character(character_id)
        if as_of_game_minute is not None and as_of_game_minute < 0:
            raise ValueError("as_of_game_minute must be >= 0")

        observations = self.repo.list_for_character(
            character_id,
            as_of_game_minute=as_of_game_minute,
        )
        latest_by_target: dict[tuple[str, int], CharacterKnowledgeObservation] = {}
        for observation in observations:
            latest_by_target[(observation.target_type, observation.target_id)] = (
                observation
            )
        return sorted(
            latest_by_target.values(),
            key=lambda item: (
                item.observed_game_minute,
                item.target_type,
                item.target_id,
            ),
        )
