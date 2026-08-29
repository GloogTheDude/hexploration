from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db.models import Campaign
from dto.map_edge_dto import MapEdgeCreate
from services.errors import ConflictError
from services.map_edge_service import MapEdgeService
from tests.factories import make_map_with_two_hexes


def _edge_payload(from_q: int, from_r: int, to_q: int, to_r: int) -> MapEdgeCreate:
    return MapEdgeCreate(
        from_q=from_q,
        from_r=from_r,
        to_q=to_q,
        to_r=to_r,
        feature_type="bridge",
        feature_id=17,
        name="North Bridge",
        extra_data={"river": "Test River"},
    )


def test_edge_coordinates_are_canonicalized(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    service = MapEdgeService(db)

    edge = service.create(version.id, _edge_payload(1, 0, 0, 0))

    assert (edge.from_q, edge.from_r, edge.to_q, edge.to_r) == (0, 0, 1, 0)
    assert edge.feature_type == "BRIDGE"
    assert edge.feature_id == 17


def test_reversed_duplicate_edge_is_rejected(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    service = MapEdgeService(db)

    service.create(version.id, _edge_payload(0, 0, 1, 0))

    with pytest.raises(ConflictError, match="edge already exists"):
        service.create(version.id, _edge_payload(1, 0, 0, 0))


def test_edge_requires_adjacent_hexes(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    service = MapEdgeService(db)

    with pytest.raises(ValueError, match="adjacent"):
        service.create(version.id, _edge_payload(0, 0, 2, 0))
