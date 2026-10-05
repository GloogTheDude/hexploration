from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User
from dto.user_dto import UserCreate, UserPingColorUpdate, UserResponse
from services.errors import ConflictError, NotFoundError
from services.user_service import UserService
from services.auth_dependencies import get_current_user
from services.authorization import require_same_user


router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        return UserResponse.model_validate(UserService(db).create(data))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    try:
        require_same_user(user_id, current_user)
        return UserResponse.model_validate(UserService(db).get(user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{user_id}/ping-color", response_model=UserResponse)
def update_ping_color(user_id: int, data: UserPingColorUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserResponse:
    try:
        require_same_user(user_id, current_user)
        return UserResponse.model_validate(UserService(db).update_ping_color(current_user.id, data.ping_color))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
