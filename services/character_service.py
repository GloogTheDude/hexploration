from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Character, CharacterStatus
from dto.character_dto import CharacterCreate
from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository
from repositories.user_repository import UserRepository
from services.errors import ForbiddenOperationError, NotFoundError


class CharacterService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CharacterRepository(db)
        self.campaigns = CampaignRepository(db)
        self.users = UserRepository(db)

    def create(self, campaign_id: int, data: CharacterCreate) -> Character:
        if self.campaigns.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")

        if self.users.get(data.owner_user_id) is None:
            raise NotFoundError("Owner user not found")

        membership = self.campaigns.get_membership(
            campaign_id=campaign_id,
            user_id=data.owner_user_id,
        )
        if membership is None:
            raise ForbiddenOperationError(
                "Character owner must be a member of the campaign"
            )

        character = Character(
            campaign_id=campaign_id,
            owner_user_id=data.owner_user_id,
            name=data.name.strip(),
            race=data.race,
            character_class=data.character_class,
            level=data.level,
            description=data.description,
            status=CharacterStatus.ACTIVE,
            current_game_minute=data.current_game_minute,
        )

        self.repo.add(character)
        self.db.commit()
        self.db.refresh(character)
        return character

    def get(self, character_id: int) -> Character:
        character = self.repo.get(character_id)
        if character is None:
            raise NotFoundError("Character not found")
        return character

    def list_for_campaign(self, campaign_id: int) -> list[Character]:
        if self.campaigns.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")
        return self.repo.list_for_campaign(campaign_id)

    def list_for_user(self, user_id: int) -> list[Character]:
        if self.users.get(user_id) is None:
            raise NotFoundError("User not found")
        return self.repo.list_for_user(user_id)
