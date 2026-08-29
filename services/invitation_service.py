from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from db.models import Campaign, CampaignInvitation, CampaignMembership, CampaignRole, User
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError

class CampaignInvitationService:
    def __init__(self, db: Session): self.db = db

    def _require_dm(self, campaign_id: int, user_id: int):
        campaign = self.db.get(Campaign, campaign_id)
        if campaign is None: raise NotFoundError("Campaign not found")
        membership = self.db.scalar(select(CampaignMembership).where(CampaignMembership.campaign_id==campaign_id, CampaignMembership.user_id==user_id))
        if membership is None or membership.role != CampaignRole.DM:
            raise ForbiddenOperationError("DM membership required for this campaign")
        return campaign

    def invite(self, campaign_id: int, dm_user_id: int, invited_user_id: int):
        self._require_dm(campaign_id, dm_user_id)
        if self.db.get(User, invited_user_id) is None: raise NotFoundError("User not found")
        if self.db.scalar(select(CampaignMembership).where(CampaignMembership.campaign_id==campaign_id, CampaignMembership.user_id==invited_user_id)):
            raise ConflictError("User is already a member of this campaign")
        existing = self.db.scalar(select(CampaignInvitation).where(CampaignInvitation.campaign_id==campaign_id, CampaignInvitation.invited_user_id==invited_user_id))
        if existing:
            if existing.status == "PENDING": raise ConflictError("A pending invitation already exists for this user")
            existing.status="PENDING"; existing.invited_by_user_id=dm_user_id; existing.created_at=datetime.now(UTC); existing.responded_at=None
            invitation=existing
        else:
            invitation=CampaignInvitation(campaign_id=campaign_id, invited_user_id=invited_user_id, invited_by_user_id=dm_user_id, status="PENDING")
            self.db.add(invitation)
        self.db.commit(); self.db.refresh(invitation); return invitation

    def list_for_campaign(self, campaign_id: int, dm_user_id: int):
        self._require_dm(campaign_id, dm_user_id)
        return list(self.db.scalars(select(CampaignInvitation).where(CampaignInvitation.campaign_id==campaign_id).order_by(CampaignInvitation.created_at.desc())))

    def list_for_user(self, user_id: int):
        if self.db.get(User,user_id) is None: raise NotFoundError("User not found")
        return list(self.db.scalars(select(CampaignInvitation).where(CampaignInvitation.invited_user_id==user_id, CampaignInvitation.status=="PENDING").order_by(CampaignInvitation.created_at.desc())))

    def respond(self, invitation_id: int, user_id: int, accept: bool):
        invitation=self.db.get(CampaignInvitation, invitation_id)
        if invitation is None: raise NotFoundError("Invitation not found")
        if invitation.invited_user_id != user_id: raise ForbiddenOperationError("This invitation belongs to another user")
        if invitation.status != "PENDING": raise ConflictError("Invitation has already been answered")
        if accept:
            membership=self.db.scalar(select(CampaignMembership).where(CampaignMembership.campaign_id==invitation.campaign_id, CampaignMembership.user_id==user_id))
            if membership is None: self.db.add(CampaignMembership(campaign_id=invitation.campaign_id,user_id=user_id,role=CampaignRole.PLAYER))
            invitation.status="ACCEPTED"
        else: invitation.status="REFUSED"
        invitation.responded_at=datetime.now(UTC); self.db.commit(); self.db.refresh(invitation); return invitation
