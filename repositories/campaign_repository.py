from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db.models import Campaign, CampaignMembership


class CampaignRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, campaign_id: int) -> Campaign | None:
        return self.db.scalar(
            select(Campaign)
            .where(Campaign.id == campaign_id)
            .options(selectinload(Campaign.memberships))
        )

    def add(self, campaign: Campaign) -> Campaign:
        self.db.add(campaign)
        self.db.flush()
        return campaign

    def get_membership(
        self,
        campaign_id: int,
        user_id: int,
    ) -> CampaignMembership | None:
        return self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == campaign_id,
                CampaignMembership.user_id == user_id,
            )
        )

    def add_membership(
        self,
        membership: CampaignMembership,
    ) -> CampaignMembership:
        self.db.add(membership)
        self.db.flush()
        return membership

    def list_for_user(self, user_id: int) -> list[Campaign]:
        stmt = (
            select(Campaign)
            .join(CampaignMembership)
            .where(CampaignMembership.user_id == user_id)
            .order_by(Campaign.name)
        )
        return list(self.db.scalars(stmt))
