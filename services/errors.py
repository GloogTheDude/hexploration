class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ForbiddenOperationError(DomainError):
    pass


class MovementBlockedError(ConflictError):
    def __init__(
        self,
        *,
        reason: str,
        target_type: str,
        target_id: int,
        edge_id: int,
        game_minute: int,
        world_event_id: int | None,
    ) -> None:
        self.detail = {
            "code": "MOVEMENT_BLOCKED",
            "reason": reason,
            "target_type": target_type,
            "target_id": target_id,
            "edge_id": edge_id,
            "game_minute": game_minute,
            "world_event_id": world_event_id,
        }
        super().__init__(
            f"Movement blocked by {reason} on {target_type} #{target_id}"
        )
