from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import ExpeditionStatus, Movement
from dto.movement_dto import ExpeditionPositionSet
from repositories.movement_repository import MovementRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.movement_cost_service import MovementCostService


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

        cost = self.costs.calculate(
            campaign_id=expedition.campaign_id,
            destination=destination,
            base_duration_minutes=base_duration_minutes,
            weather_key=expedition.weather_key,
            transport_key=expedition.transport_key,
        )

        departure = expedition.current_game_minute
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

        self.db.commit()
        self.db.refresh(movement)
        return movement

    def history(self, expedition_id: int) -> list[Movement]:
        expedition = self.repo.get_expedition_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        return self.repo.list_movements(expedition_id)
