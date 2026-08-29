from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from db.session import get_db
from dto.invitation_dto import CampaignInvitationCreate, CampaignInvitationResponse
from services.invitation_service import CampaignInvitationService
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError

router=APIRouter(tags=["campaign-invitations"])

def out(i):
    return CampaignInvitationResponse(id=i.id,campaign_id=i.campaign_id,campaign_name=i.campaign.name,invited_user_id=i.invited_user_id,invited_username=i.invited_user.username,invited_by_user_id=i.invited_by_user_id,invited_by_username=i.invited_by_user.username,status=i.status,created_at=i.created_at,responded_at=i.responded_at)

def fail(exc):
    code=404 if isinstance(exc,NotFoundError) else 403 if isinstance(exc,ForbiddenOperationError) else 409
    raise HTTPException(code,detail=str(exc)) from exc

@router.post("/api/campaigns/{campaign_id}/invitations",response_model=CampaignInvitationResponse,status_code=status.HTTP_201_CREATED)
def invite(campaign_id:int,data:CampaignInvitationCreate,user_id:int=Query(gt=0),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).invite(campaign_id,user_id,data.invited_user_id))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)


@router.get("/api/campaigns/{campaign_id}/invitations",response_model=list[CampaignInvitationResponse])
def campaign_invitations(campaign_id:int,user_id:int=Query(gt=0),db:Session=Depends(get_db)):
    try:return [out(i) for i in CampaignInvitationService(db).list_for_campaign(campaign_id,user_id)]
    except (NotFoundError,ForbiddenOperationError) as e: fail(e)

@router.get("/api/users/{user_id}/campaign-invitations",response_model=list[CampaignInvitationResponse])
def invitations(user_id:int,db:Session=Depends(get_db)):
    try:return [out(i) for i in CampaignInvitationService(db).list_for_user(user_id)]
    except NotFoundError as e: fail(e)

@router.post("/api/campaign-invitations/{invitation_id}/accept",response_model=CampaignInvitationResponse)
def accept(invitation_id:int,user_id:int=Query(gt=0),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).respond(invitation_id,user_id,True))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)

@router.post("/api/campaign-invitations/{invitation_id}/refuse",response_model=CampaignInvitationResponse)
def refuse(invitation_id:int,user_id:int=Query(gt=0),db:Session=Depends(get_db)):
    try:return out(CampaignInvitationService(db).respond(invitation_id,user_id,False))
    except (NotFoundError,ForbiddenOperationError,ConflictError) as e: fail(e)
