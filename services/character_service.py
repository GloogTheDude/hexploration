from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Character, CharacterStatus, ExpeditionCharacter
from dto.character_dto import CharacterCreate
from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository
from repositories.user_repository import UserRepository
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


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


    def create_for_player(self, campaign_id: int, user_id: int, data: CharacterCreate) -> Character:
        if data.owner_user_id != user_id:
            raise ForbiddenOperationError("A player can only create their own character")
        membership = self.campaigns.get_membership(campaign_id=campaign_id, user_id=user_id)
        if membership is None or membership.role.value != "PLAYER":
            raise ForbiddenOperationError("Accepted PLAYER membership required to create a character")
        return self.create(campaign_id, data)

    def _require_owned_player_character(self, character_id: int, user_id: int) -> Character:
        character = self.get(character_id)
        if character.owner_user_id != user_id:
            raise ForbiddenOperationError("A player can only manage their own character")
        membership = self.campaigns.get_membership(campaign_id=character.campaign_id, user_id=user_id)
        if membership is None or membership.role.value != "PLAYER":
            raise ForbiddenOperationError("Accepted PLAYER membership required")
        return character

    def delete_for_player(self, character_id: int, user_id: int) -> None:
        character = self._require_owned_player_character(character_id, user_id)
        history = self.db.scalar(select(ExpeditionCharacter.id).where(ExpeditionCharacter.character_id == character_id).limit(1))
        if history is not None:
            raise ConflictError("Character has expedition history and cannot be deleted; retire it instead")
        self.db.delete(character)
        self.db.commit()

    def retire_for_player(self, character_id: int, user_id: int) -> Character:
        character = self._require_owned_player_character(character_id, user_id)
        if character.status == CharacterStatus.DEAD:
            raise ConflictError("A dead character cannot be retired")
        character.status = CharacterStatus.RETIRED
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
