import pytest
from pydantic import ValidationError

from db.models import ExpeditionStatus
from dto.expedition_dto import ExpeditionCreate
from services.errors import NotFoundError
from services.expedition_service import ExpeditionService


def test_expedition_creation_persists_planning_state_and_campaign(db, campaign):
    expedition = ExpeditionService(db).create(
        campaign.id,
        ExpeditionCreate(name="  First Expedition  ", start_game_minute=45),
    )

    assert expedition.campaign_id == campaign.id
    assert expedition.name == "First Expedition"
    assert expedition.status is ExpeditionStatus.PLANNING
    assert expedition.start_game_minute == 45
    assert expedition.current_game_minute == 45
    assert expedition.current_map_version_id is None
    assert expedition.current_q is None
    assert expedition.current_r is None


def test_expedition_creation_rejects_unknown_campaign(db):
    with pytest.raises(NotFoundError, match="Campaign not found"):
        ExpeditionService(db).create(
            999999,
            ExpeditionCreate(name="Orphan Expedition"),
        )


def test_expedition_creation_rejects_whitespace_only_name():
    with pytest.raises(ValidationError):
        ExpeditionCreate(name="   ")
