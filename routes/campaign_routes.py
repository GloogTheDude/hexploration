from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User
from dto.campaign_dto import (
    CampaignCreate,
    CampaignResponse,
    MembershipCreate,
    MembershipResponse,
)
from services.campaign_service import CampaignService
from services.errors import ConflictError, NotFoundError
from services.auth_dependencies import get_current_user
from services.authorization import require_campaign_dm, require_campaign_member, require_same_user


router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignResponse:
    try:
        trusted_data = data.model_copy(update={"creator_user_id": current_user.id})
        return CampaignResponse.model_validate(CampaignService(db).create(trusted_data))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    _membership = Depends(require_campaign_member),
    db: Session = Depends(get_db),
) -> CampaignResponse:
    try:
        return CampaignResponse.model_validate(CampaignService(db).get(campaign_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/by-user/{user_id}", response_model=list[CampaignResponse])
def list_user_campaigns(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CampaignResponse]:
    try:
        require_same_user(user_id, current_user)
        campaigns = CampaignService(db).list_for_user(current_user.id)
        return [CampaignResponse.model_validate(c) for c in campaigns]
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{campaign_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_campaign_member(
    campaign_id: int,
    data: MembershipCreate,
    _membership = Depends(require_campaign_dm),
    db: Session = Depends(get_db),
) -> MembershipResponse:
    try:
        membership = CampaignService(db).add_member(campaign_id, data)
        return MembershipResponse.model_validate(membership)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
