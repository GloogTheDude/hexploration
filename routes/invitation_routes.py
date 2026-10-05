from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.models import User
from db.session import get_db
from dto.invitation_dto import CampaignInvitationCreate, CampaignInvitationResponse
from services.invitation_service import CampaignInvitationService
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.auth_dependencies import get_current_user
from services.authorization import require_campaign_dm, require_same_user

router=APIRouter(tags=["campaign-invitations"])

def out(i):
    return CampaignInvitationResponse(id=i.id,campaign_id=i.campaign_id,campaign_name=i.campaign.name,invited_user_id=i.invited_user_id,invited_username=i.invited_user.username,invited_by_user_id=i.invited_by_user_id,invited_by_username=i.invited_by_user.username,status=i.status,created_at=i.created_at,responded_at=i.responded_at)

def fail(exc):
    code=404 if isinstance(exc,NotFoundError) else 403 if isinstance(exc,ForbiddenOperationError) else 409
    raise HTTPException(code,detail=str(exc)) from exc

@router.post("/api/campaigns/{campaign_id}/invitations",response_model=CampaignInvitationResponse,status_code=status.HTTP_201_CREATED)
def invite(campaign_id:int,data:CampaignInvitationCreate,current_user:User=Depends(get_current_user),_membership=Depends(require_campaign_dm),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).invite(campaign_id,current_user.id,data.invited_user_id))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)


@router.get("/api/campaigns/{campaign_id}/invitations",response_model=list[CampaignInvitationResponse])
def campaign_invitations(campaign_id:int,current_user:User=Depends(get_current_user),_membership=Depends(require_campaign_dm),db:Session=Depends(get_db)):
    try:return [out(i) for i in CampaignInvitationService(db).list_for_campaign(campaign_id,current_user.id)]
    except (NotFoundError,ForbiddenOperationError) as e: fail(e)

@router.get("/api/users/{user_id}/campaign-invitations",response_model=list[CampaignInvitationResponse])
def invitations(user_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    try:
        require_same_user(user_id,current_user)
        return [out(i) for i in CampaignInvitationService(db).list_for_user(current_user.id)]
    except NotFoundError as e: fail(e)

@router.post("/api/campaign-invitations/{invitation_id}/accept",response_model=CampaignInvitationResponse)
def accept(invitation_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).respond(invitation_id,current_user.id,True))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)

@router.post("/api/campaign-invitations/{invitation_id}/refuse",response_model=CampaignInvitationResponse)
def refuse(invitation_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).respond(invitation_id,current_user.id,False))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)
