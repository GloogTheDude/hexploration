from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import ExpeditionStatus, Movement
from dto.movement_dto import ExpeditionPositionSet
from repositories.movement_repository import MovementRepository
from services.errors import (
    ConflictError,
    ForbiddenOperationError,
    MovementBlockedError,
    NotFoundError,
)
from services.movement_cost_service import MovementCostService
from services.world_event_service import WorldEventService
from services.visibility_service import VisibilityService


class InvalidMovementError(Exception):
    pass


def axial_hex_distance(q1: int, r1: int, q2: int, r2: int) -> int:
    return (
        abs(q1 - q2)
        + abs(q1 + r1 - q2 - r2)
        + abs(r1 - r2)
    ) // 2


class ExpeditionMovementService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MovementRepository(db)
        self.costs = MovementCostService()
        self.world_events = WorldEventService(db)
        self.visibility = VisibilityService(db)

    def set_position(
        self,
        expedition_id: int,
        data: ExpeditionPositionSet,
    ):
        expedition = self.repo.get_expedition_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        if expedition.status not in {
            ExpeditionStatus.PLANNING,
            ExpeditionStatus.ACTIVE,
        }:
            raise ConflictError(
                "Position can only be set for a planning or active expedition"
            )

        map_version = self.repo.get_map_version(data.map_version_id)
        if map_version is None:
            raise NotFoundError("Map version not found")

        world_map = self.repo.get_world_map(map_version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")

        if world_map.campaign_id != expedition.campaign_id:
            raise ForbiddenOperationError(
                "Map version and expedition must belong to the same campaign"
            )

        target_hex = self.repo.get_hex(data.map_version_id, data.q, data.r)
        if target_hex is None:
            raise NotFoundError("Hex not found in this map version")

        expedition.current_map_version_id = data.map_version_id
        expedition.current_q = data.q
        expedition.current_r = data.r

        if expedition.status == ExpeditionStatus.ACTIVE:
            self.visibility.observe_visible_pois(expedition.id, commit=False)

        self.db.commit()
        self.db.refresh(expedition)
        return expedition

    def move(
        self,
        *,
        expedition_id: int,
        to_q: int,
        to_r: int,
        base_duration_minutes: int,
    ) -> Movement:
        expedition = self.repo.get_expedition_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can move")

        if (
            expedition.current_map_version_id is None
            or expedition.current_q is None
            or expedition.current_r is None
        ):
            raise ConflictError(
                "Expedition position must be initialized before moving"
            )

        if axial_hex_distance(
            expedition.current_q,
            expedition.current_r,
            to_q,
            to_r,
        ) != 1:
            raise InvalidMovementError(
                "Destination must be an adjacent hex"
            )

        destination = self.repo.get_hex(
            expedition.current_map_version_id,
            to_q,
            to_r,
        )
        if destination is None:
            raise NotFoundError("Destination hex not found")

        source = self.repo.get_hex(
            expedition.current_map_version_id,
            expedition.current_q,
            expedition.current_r,
        )
        if source is None:
            raise ConflictError("Current expedition hex no longer exists")

        departure = expedition.current_game_minute

        # An edge represents a spatial feature between two adjacent hexes.
        # Its traversability is resolved from WorldEvent at the expedition's
        # own departure minute. The same bridge can therefore be destroyed for
        # one expedition and already repaired for another expedition later in
        # the campaign timeline.
        edge = self.repo.get_edge_between(
            expedition.current_map_version_id,
            expedition.current_q,
            expedition.current_r,
            to_q,
            to_r,
        )
        if edge is not None:
            traversal = self.world_events.traversal_state_for_target(
                expedition.campaign_id,
                game_minute=departure,
                target_type=edge.feature_type,
                target_id=edge.feature_id,
            )
            if not traversal.allowed and traversal.event is not None:
                raise MovementBlockedError(
                    reason=traversal.event.event_type,
                    target_type=edge.feature_type,
                    target_id=edge.feature_id,
                    edge_id=edge.id,
                    game_minute=departure,
                    world_event_id=traversal.event.id,
                )

        # Weather is world truth and therefore resolved at the expedition's
        # own in-world clock. An expedition at minute 150 can see RAIN while
        # another expedition at minute 350 sees a later STORM event.
        weather_key = self.world_events.weather_at(
            expedition.campaign_id,
            departure,
        )

        # Transport remains party state rather than world state.
        cost = self.costs.calculate(
            campaign_id=expedition.campaign_id,
            destination=destination,
            base_duration_minutes=base_duration_minutes,
            weather_key=weather_key,
            transport_key=expedition.transport_key,
        )

        arrival = departure + cost.effective_duration_minutes

        movement = Movement(
            expedition_id=expedition.id,
            map_version_id=expedition.current_map_version_id,
            from_q=expedition.current_q,
            from_r=expedition.current_r,
            to_q=to_q,
            to_r=to_r,
            departure_game_minute=departure,
            arrival_game_minute=arrival,
            base_duration_minutes=cost.base_duration_minutes,
            effective_duration_minutes=cost.effective_duration_minutes,
            modifiers=cost.modifiers,
        )

        self.repo.add_movement(movement)

        expedition.current_q = to_q
        expedition.current_r = to_r
        expedition.current_game_minute = arrival

        for participant in self.repo.active_participants(expedition.id):
            character = self.repo.get_character(participant.character_id)
            if character is not None:
                character.current_game_minute = max(
                    character.current_game_minute,
                    arrival,
                )

        # Arrival changes both position and in-world time. Resolve visibility at
        # that exact arrival minute and persist newly learned/changed POI state
        # in the same transaction as the movement.
        self.visibility.observe_visible_pois(expedition.id, commit=False)

        self.db.commit()
        self.db.refresh(movement)
        return movement

    def history(self, expedition_id: int) -> list[Movement]:
        expedition = self.repo.get_expedition_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        return self.repo.list_movements(expedition_id)
