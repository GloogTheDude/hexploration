from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Expedition, ExpeditionCharacter, ExpeditionStatus
from dto.expedition_dto import ExpeditionCreate
from repositories.campaign_repository import CampaignRepository
from repositories.expedition_repository import ExpeditionRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


class ExpeditionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ExpeditionRepository(db)
        self.campaigns = CampaignRepository(db)

    def create(self, campaign_id: int, data: ExpeditionCreate) -> Expedition:
        if self.campaigns.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")

        expedition = Expedition(
            campaign_id=campaign_id,
            name=data.name.strip(),
            status=ExpeditionStatus.PLANNING,
            start_game_minute=data.start_game_minute,
            current_game_minute=data.start_game_minute,
            return_game_minute=None,
            current_map_version_id=None,
            current_q=None,
            current_r=None,
        )

        self.repo.add(expedition)
        self.db.commit()
        self.db.refresh(expedition)
        return expedition

    def get(self, expedition_id: int) -> Expedition:
        expedition = self.repo.get(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        return expedition

    def list_for_campaign(self, campaign_id: int) -> list[Expedition]:
        if self.campaigns.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")
        return self.repo.list_for_campaign(campaign_id)

    def add_character(
        self,
        expedition_id: int,
        character_id: int,
    ) -> ExpeditionCharacter:
        expedition = self.get(expedition_id)

        if expedition.status not in {
            ExpeditionStatus.PLANNING,
            ExpeditionStatus.ACTIVE,
        }:
            raise ConflictError(
                "Characters can only join a planning or active expedition"
            )

        character = self.repo.get_character(character_id)
        if character is None:
            raise NotFoundError("Character not found")

        if character.campaign_id != expedition.campaign_id:
            raise ForbiddenOperationError(
                "Character and expedition must belong to the same campaign"
            )

        if self.repo.get_participant(expedition_id, character_id) is not None:
            raise ConflictError("Character is already part of this expedition")

        current_assignment = self.repo.active_expedition_for_character(character_id)
        if current_assignment is not None:
            raise ConflictError(
                "Character is already part of another open expedition"
            )

        participant = ExpeditionCharacter(
            expedition_id=expedition_id,
            character_id=character_id,
            joined_game_minute=expedition.current_game_minute,
            left_game_minute=None,
        )

        self.repo.add_participant(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def list_characters(self, expedition_id: int) -> list[ExpeditionCharacter]:
        self.get(expedition_id)
        return self.repo.list_participants(expedition_id)

    def start(self, expedition_id: int) -> Expedition:
        expedition = self.repo.get_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        if expedition.status != ExpeditionStatus.PLANNING:
            raise ConflictError("Only a planning expedition can be started")

        if not self.repo.list_participants(expedition_id):
            raise ConflictError("An expedition needs at least one character")

        expedition.status = ExpeditionStatus.ACTIVE
        self.db.commit()
        self.db.refresh(expedition)
        return expedition

    def return_to_hub(self, expedition_id: int) -> Expedition:
        expedition = self.repo.get_for_update(expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")

        if expedition.status != ExpeditionStatus.ACTIVE:
            raise ConflictError("Only an active expedition can return")

        expedition.status = ExpeditionStatus.RETURNED
        expedition.return_game_minute = expedition.current_game_minute

        for participant in self.repo.list_participants(expedition_id):
            if participant.left_game_minute is None:
                participant.left_game_minute = expedition.current_game_minute

            character = self.repo.get_character(participant.character_id)
            if character is not None:
                character.current_game_minute = max(
                    character.current_game_minute,
                    expedition.current_game_minute,
                )

        self.db.commit()
        self.db.refresh(expedition)
        return expedition
