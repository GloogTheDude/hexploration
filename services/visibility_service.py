from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import CharacterKnowledgeObservation, CharacterMapHexObservation, ExpeditionStatus, MapHex, MapVersion, PointOfInterest
from repositories.knowledge_repository import KnowledgeRepository
from repositories.visibility_repository import VisibilityRepository
from services.errors import ConflictError, NotFoundError
from services.poi_service import POIService
from services.map_knowledge_service import MapKnowledgeService
from services.map_hex_service import get_or_materialize_hex, materialize_radius
from services.world_event_service import WorldEventService


WEATHER_VISIBILITY_PENALTY: dict[str, int] = {
    "CLEAR": 0,
    "RAIN": 1,
    "HEAVY_RAIN": 2,
    "STORM": 3,
    "SNOW": 2,
    "BLIZZARD": 4,
    "FOG": 4,
}

LANDMARK_RANGE_BONUS = 2
MAX_ELEVATION_BONUS = 2
NORMAL_TERRAIN_VISIBILITY = 3
LOS_EPSILON = 1e-9


def axial_hex_distance(q1: int, r1: int, q2: int, r2: int) -> int:
    return (
        abs(q1 - q2)
        + abs(q1 + r1 - q2 - r2)
        + abs(r1 - r2)
    ) // 2


def _cube_round(x: float, y: float, z: float) -> tuple[int, int, int]:
    rx, ry, rz = round(x), round(y), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - y), abs(rz - z)

    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(ry), int(rz)


def axial_hex_line(q1: int, r1: int, q2: int, r2: int) -> list[tuple[int, int]]:
    """Return a deterministic axial line including origin and destination.

    Axial coordinates are converted to cube coordinates and interpolated using
    the standard cube-rounding method. A tiny nudge removes exact edge/corner
    ambiguity in a deterministic way, which is preferable to unstable LOS
    results that depend on floating-point ties.
    """

    distance = axial_hex_distance(q1, r1, q2, r2)
    if distance == 0:
        return [(q1, r1)]

    ax, az = float(q1) + 1e-6, float(r1) - 2e-6
    ay = -ax - az
    bx, bz = float(q2) + 1e-6, float(r2) - 2e-6
    by = -bx - bz

    line: list[tuple[int, int]] = []
    for step in range(distance + 1):
        t = step / distance
        x = ax + (bx - ax) * t
        y = ay + (by - ay) * t
        z = az + (bz - az) * t
        rx, _, rz = _cube_round(x, y, z)
        coord = (rx, rz)
        if not line or line[-1] != coord:
            line.append(coord)
    return line


@dataclass(frozen=True)
class LOSResult:
    clear: bool
    path: list[tuple[int, int]]
    blocker_q: int | None = None
    blocker_r: int | None = None
    blocker_reason: str | None = None
    blocker_elevation: float | None = None
    sightline_elevation: float | None = None


@dataclass(frozen=True)
class VisiblePOI:
    poi: PointOfInterest
    hex: MapHex
    distance: int
    max_visible_distance: int
    weather_key: str | None
    weather_penalty: int
    landmark_bonus: int
    elevation_bonus: int
    terrain_concealment_penalty: int
    state: str
    exists: bool
    world_event_id: int | None
    los_path: list[tuple[int, int]]
    visible_at_distance: bool


@dataclass(frozen=True)
class OccludedPOI:
    poi: PointOfInterest
    hex: MapHex
    distance: int
    max_visible_distance: int
    blocker_q: int
    blocker_r: int
    blocker_reason: str
    blocker_elevation: float | None
    sightline_elevation: float | None
    los_path: list[tuple[int, int]]


@dataclass(frozen=True)
class VisibleHex:
    hex: MapHex
    distance: int
    max_visible_distance: int
    weather_penalty: int
    elevation_bonus: int
    terrain_concealment_penalty: int
    los_path: list[tuple[int, int]]


@dataclass(frozen=True)
class OccludedHex:
    hex: MapHex
    distance: int
    max_visible_distance: int
    blocker_q: int
    blocker_r: int
    blocker_reason: str
    blocker_elevation: float | None
    sightline_elevation: float | None
    los_path: list[tuple[int, int]]


@dataclass(frozen=True)
class VisibilityScan:
    expedition_id: int
    game_minute: int
    map_version_id: int
    origin_q: int
    origin_r: int
    origin_visibility_score: int
    weather_key: str | None
    visible_hexes: list[VisibleHex]
    occluded_hexes: list[OccludedHex]
    visible_pois: list[VisiblePOI]
    occluded_pois: list[OccludedPOI]


@dataclass(frozen=True)
class VisibilityObservationResult:
    scan: VisibilityScan
    observations: list[CharacterKnowledgeObservation]
    map_observations: list[CharacterMapHexObservation]


class VisibilityService:
    """Resolve what an active expedition can currently see.

    v13 keeps the v12 range model and adds deterministic line-of-sight through
    intermediate map hexes. Terrain with a visibility score below the neutral
    score contributes an opacity height, while high terrain can physically rise
    above the interpolated sight line. Missing intermediate map cells are also
    opaque: the system never grants knowledge through unknown/nonexistent map
    geometry.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = VisibilityRepository(db)
        self.knowledge = KnowledgeRepository(db)
        self.pois = POIService(db)
        self.world = WorldEventService(db)
        self.map_knowledge = MapKnowledgeService(db)

    @staticmethod
    def _weather_penalty(weather_key: str | None) -> int:
        if weather_key is None:
            return 0
        return WEATHER_VISIBILITY_PENALTY.get(weather_key.upper(), 0)

    @staticmethod
    def _terrain_concealment(target_hex: MapHex) -> int:
        return max(0, NORMAL_TERRAIN_VISIBILITY - target_hex.visibility_score)

    @staticmethod
    def _terrain_opacity_height(hex_tile: MapHex) -> int:
        """Convert dense terrain into effective LOS obstacle height.

        Neutral/open terrain (visibility >= 3) adds no height. Forest-like
        terrain with score 2 adds one level; denser terrain can add more.
        """
        return max(0, NORMAL_TERRAIN_VISIBILITY - hex_tile.visibility_score)

    @staticmethod
    def _elevation_bonus(origin: MapHex, target: MapHex) -> int:
        advantage = max(0, origin.elevation - target.elevation)
        return min(MAX_ELEVATION_BONUS, advantage)

    def _max_visible_distance(
        self,
        *,
        origin: MapHex,
        target: MapHex,
        poi: PointOfInterest,
        weather_key: str | None,
        visible_at_distance: bool | None = None,
    ) -> tuple[int, int, int, int, int]:
        weather_penalty = self._weather_penalty(weather_key)
        is_landmark = poi.is_landmark if visible_at_distance is None else visible_at_distance
        landmark_bonus = LANDMARK_RANGE_BONUS if is_landmark else 0
        elevation_bonus = self._elevation_bonus(origin, target)
        concealment = self._terrain_concealment(target)
        max_distance = max(
            0,
            origin.visibility_score
            - weather_penalty
            + landmark_bonus
            + elevation_bonus
            - concealment,
        )
        return (
            max_distance,
            weather_penalty,
            landmark_bonus,
            elevation_bonus,
            concealment,
        )

    def _max_hex_visible_distance(
        self,
        *,
        origin: MapHex,
        target: MapHex,
        weather_key: str | None,
    ) -> tuple[int, int, int, int]:
        weather_penalty = self._weather_penalty(weather_key)
        elevation_bonus = self._elevation_bonus(origin, target)
        concealment = self._terrain_concealment(target)
        max_distance = max(
            0,
            origin.visibility_score
            - weather_penalty
            + elevation_bonus
            - concealment,
        )
        return max_distance, weather_penalty, elevation_bonus, concealment

    def _line_of_sight(
        self,
        *,
        origin: MapHex,
        target: MapHex,
        hexes: dict[tuple[int, int], MapHex],
    ) -> LOSResult:
        path = axial_hex_line(origin.q, origin.r, target.q, target.r)
        distance = len(path) - 1
        if distance <= 1:
            return LOSResult(clear=True, path=path)

        for step, (q, r) in enumerate(path[1:-1], start=1):
            intermediate = hexes.get((q, r))
            if intermediate is None:
                return LOSResult(
                    clear=False,
                    path=path,
                    blocker_q=q,
                    blocker_r=r,
                    blocker_reason="MISSING_HEX",
                )

            t = step / distance
            sightline = origin.elevation + (target.elevation - origin.elevation) * t
            obstacle = intermediate.elevation + self._terrain_opacity_height(intermediate)
            if obstacle > sightline + LOS_EPSILON:
                reason = (
                    "TERRAIN_CONCEALMENT"
                    if self._terrain_opacity_height(intermediate) > 0
                    else "ELEVATION"
                )
                return LOSResult(
                    clear=False,
                    path=path,
                    blocker_q=q,
                    blocker_r=r,
                    blocker_reason=reason,
                    blocker_elevation=float(obstacle),
                    sightline_elevation=float(sightline),
                )

        return LOSResult(clear=True, path=path)

    def scan(self, expedition_id: int) -> VisibilityScan:
        expedition = self.repo.get_expedition(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Visibility can only be resolved for an active expedition")
        if (
            expedition.current_map_version_id is None
            or expedition.current_q is None
            or expedition.current_r is None
        ):
            raise ConflictError("Expedition has no current map position")

        version = self.db.get(MapVersion, expedition.current_map_version_id)
        if version is None:
            raise NotFoundError("Map version not found")
        origin = get_or_materialize_hex(self.db, version, expedition.current_q, expedition.current_r)
        if origin is None:
            raise ConflictError("Current expedition hex no longer exists")
        # Sparse versions intentionally omit default-terrain rows. Materialise only
        # the bounded visibility neighbourhood so implicit SEA/PLAIN cells take
        # part in LOS and can become player observations without densifying maps.
        scan_radius = max(0, origin.visibility_score) + LANDMARK_RANGE_BONUS + MAX_ELEVATION_BONUS
        materialize_radius(self.db, version, origin.q, origin.r, scan_radius)
        all_hexes = {
            (hex_tile.q, hex_tile.r): hex_tile
            for hex_tile in self.repo.list_hexes(expedition.current_map_version_id)
        }

        weather_key = self.world.weather_at(
            expedition.campaign_id,
            expedition.current_game_minute,
        )

        visible_hexes: list[VisibleHex] = []
        occluded_hexes: list[OccludedHex] = []
        for target_hex in all_hexes.values():
            distance = axial_hex_distance(origin.q, origin.r, target_hex.q, target_hex.r)
            max_distance, weather_penalty, elevation_bonus, concealment = (
                self._max_hex_visible_distance(
                    origin=origin,
                    target=target_hex,
                    weather_key=weather_key,
                )
            )

            # The occupied cell is always known/observable. Otherwise range is
            # checked before the more expensive LOS trace.
            if distance != 0 and distance > max_distance:
                continue

            los = self._line_of_sight(origin=origin, target=target_hex, hexes=all_hexes)
            if not los.clear:
                assert los.blocker_q is not None
                assert los.blocker_r is not None
                assert los.blocker_reason is not None
                occluded_hexes.append(
                    OccludedHex(
                        hex=target_hex,
                        distance=distance,
                        max_visible_distance=max_distance,
                        blocker_q=los.blocker_q,
                        blocker_r=los.blocker_r,
                        blocker_reason=los.blocker_reason,
                        blocker_elevation=los.blocker_elevation,
                        sightline_elevation=los.sightline_elevation,
                        los_path=los.path,
                    )
                )
                continue

            visible_hexes.append(
                VisibleHex(
                    hex=target_hex,
                    distance=distance,
                    max_visible_distance=max_distance,
                    weather_penalty=weather_penalty,
                    elevation_bonus=elevation_bonus,
                    terrain_concealment_penalty=concealment,
                    los_path=los.path,
                )
            )

        visible: list[VisiblePOI] = []
        occluded: list[OccludedPOI] = []
        for poi, target_hex in self.repo.list_pois_with_hex(
            expedition.current_map_version_id
        ):
            state = self.pois.state_at(
                poi.id,
                campaign_id=expedition.campaign_id,
                game_minute=expedition.current_game_minute,
            )
            distance = axial_hex_distance(origin.q, origin.r, target_hex.q, target_hex.r)
            (
                max_distance,
                weather_penalty,
                landmark_bonus,
                elevation_bonus,
                concealment,
            ) = self._max_visible_distance(
                origin=origin,
                target=target_hex,
                poi=poi,
                weather_key=weather_key,
                visible_at_distance=state.visible_at_distance,
            )

            if distance != 0 and distance > max_distance:
                continue

            los = self._line_of_sight(origin=origin, target=target_hex, hexes=all_hexes)
            if not los.clear:
                assert los.blocker_q is not None
                assert los.blocker_r is not None
                assert los.blocker_reason is not None
                occluded.append(
                    OccludedPOI(
                        poi=poi,
                        hex=target_hex,
                        distance=distance,
                        max_visible_distance=max_distance,
                        blocker_q=los.blocker_q,
                        blocker_r=los.blocker_r,
                        blocker_reason=los.blocker_reason,
                        blocker_elevation=los.blocker_elevation,
                        sightline_elevation=los.sightline_elevation,
                        los_path=los.path,
                    )
                )
                continue

            visible.append(
                VisiblePOI(
                    poi=poi,
                    hex=target_hex,
                    distance=distance,
                    max_visible_distance=max_distance,
                    weather_key=weather_key,
                    weather_penalty=weather_penalty,
                    landmark_bonus=landmark_bonus,
                    elevation_bonus=elevation_bonus,
                    terrain_concealment_penalty=concealment,
                    state=state.state,
                    exists=state.exists,
                    world_event_id=(
                        state.latest_event.id if state.latest_event is not None else None
                    ),
                    los_path=los.path,
                    visible_at_distance=state.visible_at_distance,
                )
            )

        visible_hexes.sort(key=lambda item: (item.distance, item.hex.q, item.hex.r))
        occluded_hexes.sort(key=lambda item: (item.distance, item.hex.q, item.hex.r))
        visible.sort(key=lambda item: (item.distance, item.poi.id))
        occluded.sort(key=lambda item: (item.distance, item.poi.id))
        return VisibilityScan(
            expedition_id=expedition.id,
            game_minute=expedition.current_game_minute,
            map_version_id=expedition.current_map_version_id,
            origin_q=origin.q,
            origin_r=origin.r,
            origin_visibility_score=origin.visibility_score,
            weather_key=weather_key,
            visible_hexes=visible_hexes,
            occluded_hexes=occluded_hexes,
            visible_pois=visible,
            occluded_pois=occluded,
        )

    @staticmethod
    def _snapshot(item: VisiblePOI, map_version_id: int) -> dict:
        return {
            "name": item.poi.name,
            "kind": item.poi.kind,
            "description": item.poi.player_description,
            "map_version_id": map_version_id,
            "q": item.hex.q,
            "r": item.hex.r,
            "state": item.state,
            "exists": item.exists,
            "world_event_id": item.world_event_id,
        }

    def observe_visible_pois(
        self,
        expedition_id: int,
        *,
        commit: bool = True,
    ) -> VisibilityObservationResult:
        scan = self.scan(expedition_id)
        participants = self.repo.active_participants(expedition_id, scan.game_minute)

        observations: list[CharacterKnowledgeObservation] = []
        for item in scan.visible_pois:
            snapshot = self._snapshot(item, scan.map_version_id)
            for participant in participants:
                latest = self.knowledge.latest_for_target(
                    character_id=participant.character_id,
                    target_type="POI",
                    target_id=item.poi.feature_id,
                )
                # Explicit DM hiding is authoritative until the DM reveals the
                # POI again. Merely being inside the current field of view must
                # never recreate knowledge that was deliberately revoked.
                if latest is not None and latest.knowledge.get("hidden_from_players", False):
                    continue
                # A search-required POI must first be explicitly revealed by the
                # DM. Once discovered, later visible changes can be observed normally.
                if item.poi.requires_discovery and latest is None:
                    continue
                existing_exact = self.knowledge.get_exact(
                    character_id=participant.character_id,
                    expedition_id=expedition_id,
                    target_type="POI",
                    target_id=item.poi.feature_id,
                    observed_game_minute=scan.game_minute,
                )
                if existing_exact is not None:
                    continue

                if (
                    latest is not None
                    and latest.expedition_id == expedition_id
                    and latest.knowledge == snapshot
                ):
                    continue

                observation = CharacterKnowledgeObservation(
                    character_id=participant.character_id,
                    expedition_id=expedition_id,
                    target_type="POI",
                    target_id=item.poi.feature_id,
                    observed_game_minute=scan.game_minute,
                    source_type="AUTO_VISIBILITY",
                    knowledge=dict(snapshot),
                )
                self.knowledge.add(observation)
                observations.append(observation)

        map_observations = self.map_knowledge.record_visible_hexes(
            expedition_id=expedition_id,
            map_version_id=scan.map_version_id,
            game_minute=scan.game_minute,
            origin_q=scan.origin_q,
            origin_r=scan.origin_r,
            visible_hexes=(item.hex for item in scan.visible_hexes),
            commit=False,
        )

        if commit:
            self.db.commit()
            for observation in observations:
                self.db.refresh(observation)
            for observation in map_observations:
                self.db.refresh(observation)

        return VisibilityObservationResult(
            scan=scan,
            observations=observations,
            map_observations=map_observations,
        )
