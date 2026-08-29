from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Campaign, CampaignMembership, CampaignRole
from dto.campaign_dto import CampaignCreate, MembershipCreate
from repositories.campaign_repository import CampaignRepository
from repositories.user_repository import UserRepository
from services.errors import ConflictError, NotFoundError


class CampaignService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CampaignRepository(db)
        self.users = UserRepository(db)

    def create(self, data: CampaignCreate) -> Campaign:
        creator = self.users.get(data.creator_user_id)
        if creator is None:
            raise NotFoundError("Creator user not found")

        campaign = Campaign(
            name=data.name.strip(),
            description=data.description,
            epoch_name=data.epoch_name.strip(),
        )

        try:
            self.repo.add(campaign)
            self.repo.add_membership(
                CampaignMembership(
                    campaign_id=campaign.id,
                    user_id=creator.id,
                    role=CampaignRole.DM,
                )
            )
            self.db.commit()
            self.db.refresh(campaign)
            return campaign
        except IntegrityError:
            self.db.rollback()
            raise

    def get(self, campaign_id: int) -> Campaign:
        campaign = self.repo.get(campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")
        return campaign

    def list_for_user(self, user_id: int) -> list[Campaign]:
        if self.users.get(user_id) is None:
            raise NotFoundError("User not found")
        return self.repo.list_for_user(user_id)

    def add_member(
        self,
        campaign_id: int,
        data: MembershipCreate,
    ) -> CampaignMembership:
        if self.repo.get(campaign_id) is None:
            raise NotFoundError("Campaign not found")

        if self.users.get(data.user_id) is None:
            raise NotFoundError("User not found")

        if self.repo.get_membership(campaign_id, data.user_id) is not None:
            raise ConflictError("User is already a member of this campaign")

        membership = CampaignMembership(
            campaign_id=campaign_id,
            user_id=data.user_id,
            role=data.role,
        )

        try:
            self.repo.add_membership(membership)
            self.db.commit()
            self.db.refresh(membership)
            return membership
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("User is already a member of this campaign") from exc
