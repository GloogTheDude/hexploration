from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from db.models import CharacterMapHexObservation, MapHex
from repositories.map_knowledge_repository import MapKnowledgeRepository
from services.errors import ForbiddenOperationError, NotFoundError


STATE_RANK = {"UNKNOWN": 0, "SEEN": 1, "VISITED": 2}


@dataclass(frozen=True)
class MapObservationCandidate:
    hex: MapHex
    state: str


class MapKnowledgeService:
    """Immutable fog-of-war knowledge for map geometry.

    Identity is `(map_id, q, r)`, not `MapHex.id`. That is deliberate: a new
    MapVersion creates new MapHex rows, but player knowledge should still refer
    to the same physical coordinate and keep the last appearance actually seen.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MapKnowledgeRepository(db)

    @staticmethod
    def _same_visual_state(
        previous: CharacterMapHexObservation,
        tile: MapHex,
    ) -> bool:
        return (
            previous.terrain_key == tile.terrain_key
            and previous.elevation == tile.elevation
            and previous.visibility_score == tile.visibility_score
            and previous.extra_data == tile.extra_data
        )

    def record_visible_hexes(
        self,
        *,
        expedition_id: int,
        map_version_id: int,
        game_minute: int,
        origin_q: int,
        origin_r: int,
        visible_hexes: Iterable[MapHex],
        commit: bool = True,
    ) -> list[CharacterMapHexObservation]:
        expedition = self.repo.get_expedition(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        version = self.repo.get_map_version(map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")

        participants = self.repo.active_participants(expedition_id, game_minute)
        observations: list[CharacterMapHexObservation] = []

        for tile in visible_hexes:
            candidate_state = (
                "VISITED" if (tile.q, tile.r) == (origin_q, origin_r) else "SEEN"
            )
            for participant in participants:
                exact = self.repo.get_exact(
                    character_id=participant.character_id,
                    expedition_id=expedition_id,
                    map_id=version.map_id,
                    q=tile.q,
                    r=tile.r,
                    observed_game_minute=game_minute,
                )
                if exact is not None:
                    if STATE_RANK.get(candidate_state, 0) > STATE_RANK.get(exact.discovery_state, 0):
                        exact.discovery_state = candidate_state
                    exact.map_version_id = map_version_id
                    exact.terrain_key = tile.terrain_key
                    exact.elevation = tile.elevation
                    exact.visibility_score = tile.visibility_score
                    exact.extra_data = dict(tile.extra_data or {})
                    continue

                latest = self.repo.latest_for_hex(
                    character_id=participant.character_id,
                    map_id=version.map_id,
                    q=tile.q,
                    r=tile.r,
                )

                state = candidate_state
                if latest is not None and STATE_RANK.get(latest.discovery_state, 0) > STATE_RANK[state]:
                    state = latest.discovery_state

                if (
                    latest is not None
                    and latest.expedition_id == expedition_id
                    and latest.discovery_state == state
                    and self._same_visual_state(latest, tile)
                ):
                    continue

                observation = CharacterMapHexObservation(
                    character_id=participant.character_id,
                    expedition_id=expedition_id,
                    map_id=version.map_id,
                    map_version_id=map_version_id,
                    q=tile.q,
                    r=tile.r,
                    observed_game_minute=game_minute,
                    discovery_state=state,
                    terrain_key=tile.terrain_key,
                    elevation=tile.elevation,
                    visibility_score=tile.visibility_score,
                    extra_data=dict(tile.extra_data or {}),
                )
                self.repo.add(observation)
                observations.append(observation)

        if commit:
            self.db.commit()
            for observation in observations:
                self.db.refresh(observation)

        return observations

    def character_hex(
        self,
        *,
        character_id: int,
        map_id: int,
        q: int,
        r: int,
        as_of_game_minute: int | None = None,
    ) -> CharacterMapHexObservation:
        character = self.repo.get_character(character_id)
        if character is None:
            raise NotFoundError("Character not found")
        world_map = self.repo.get_map(map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != character.campaign_id:
            raise ForbiddenOperationError("Character and map must belong to the same campaign")

        observation = self.repo.latest_for_hex(
            character_id=character_id,
            map_id=map_id,
            q=q,
            r=r,
            as_of_game_minute=as_of_game_minute,
        )
        if observation is None:
            raise NotFoundError("Hex is unknown to this character")
        return observation

    def character_history(
        self,
        *,
        character_id: int,
        map_id: int,
        q: int,
        r: int,
    ) -> list[CharacterMapHexObservation]:
        self.character_hex(character_id=character_id, map_id=map_id, q=q, r=r)
        return self.repo.history_for_hex(
            character_id=character_id,
            map_id=map_id,
            q=q,
            r=r,
        )

    def character_map(
        self,
        *,
        character_id: int,
        map_id: int,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterMapHexObservation]:
        character = self.repo.get_character(character_id)
        if character is None:
            raise NotFoundError("Character not found")
        world_map = self.repo.get_map(map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != character.campaign_id:
            raise ForbiddenOperationError("Character and map must belong to the same campaign")

        rows = self.repo.list_for_character_map(
            character_id=character_id,
            map_id=map_id,
            as_of_game_minute=as_of_game_minute,
        )
        latest: dict[tuple[int, int], CharacterMapHexObservation] = {}
        for row in rows:
            latest.setdefault((row.q, row.r), row)
        return sorted(latest.values(), key=lambda item: (item.q, item.r))

    def expedition_map(
        self,
        *,
        expedition_id: int,
        map_id: int,
        as_of_game_minute: int | None = None,
    ) -> list[CharacterMapHexObservation]:
        expedition = self.repo.get_expedition(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        world_map = self.repo.get_map(map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != expedition.campaign_id:
            raise ForbiddenOperationError("Expedition and map must belong to the same campaign")

        minute = expedition.current_game_minute if as_of_game_minute is None else as_of_game_minute
        participants = self.repo.participants_at(expedition_id, minute)
        merged: dict[tuple[int, int], CharacterMapHexObservation] = {}
        for participant in participants:
            rows = self.character_map(
                character_id=participant.character_id,
                map_id=map_id,
                as_of_game_minute=minute,
            )
            for row in rows:
                key = (row.q, row.r)
                previous = merged.get(key)
                if previous is None:
                    merged[key] = row
                    continue
                previous_rank = STATE_RANK.get(previous.discovery_state, 0)
                row_rank = STATE_RANK.get(row.discovery_state, 0)
                if row_rank > previous_rank or (
                    row_rank == previous_rank
                    and (row.observed_game_minute, row.id) > (previous.observed_game_minute, previous.id)
                ):
                    merged[key] = row
        return sorted(merged.values(), key=lambda item: (item.q, item.r))
