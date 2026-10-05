from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.models import User

from db.session import get_db
from dto.character_dto import CharacterCreate, CharacterResponse
from services.character_service import CharacterService
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.auth_dependencies import get_current_user
from services.authorization import require_campaign_dm, require_campaign_member, require_character_access, require_same_user


router = APIRouter(tags=["characters"])


@router.post(
    "/api/campaigns/{campaign_id}/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_character(
    campaign_id: int,
    data: CharacterCreate,
    _membership = Depends(require_campaign_dm),
    db: Session = Depends(get_db),
) -> CharacterResponse:
    try:
        character = CharacterService(db).create(campaign_id, data)
        return CharacterResponse.model_validate(character)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get(
    "/api/campaigns/{campaign_id}/characters",
    response_model=list[CharacterResponse],
)
def list_campaign_characters(
    campaign_id: int,
    _membership = Depends(require_campaign_member),
    db: Session = Depends(get_db),
) -> list[CharacterResponse]:
    try:
        characters = CharacterService(db).list_for_campaign(campaign_id)
        return [CharacterResponse.model_validate(c) for c in characters]
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/api/users/{user_id}/characters",
    response_model=list[CharacterResponse],
)
def list_user_characters(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CharacterResponse]:
    try:
        require_same_user(user_id, current_user)
        characters = CharacterService(db).list_for_user(current_user.id)
        return [CharacterResponse.model_validate(c) for c in characters]
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/api/characters/{character_id}",
    response_model=CharacterResponse,
)
def get_character(
    character_id: int,
    _character = Depends(require_character_access),
    db: Session = Depends(get_db),
) -> CharacterResponse:
    try:
        return CharacterResponse.model_validate(
            CharacterService(db).get(character_id)
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/api/campaigns/{campaign_id}/player-characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_player_character(campaign_id: int, data: CharacterCreate, current_user: User = Depends(get_current_user), _membership = Depends(require_campaign_member), db: Session = Depends(get_db)) -> CharacterResponse:
    try:
        trusted_data = data.model_copy(update={"owner_user_id": current_user.id})
        return CharacterResponse.model_validate(CharacterService(db).create_for_player(campaign_id, current_user.id, trusted_data))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/api/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player_character(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> None:
    try:
        CharacterService(db).delete_for_player(character_id, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/api/characters/{character_id}/retire", response_model=CharacterResponse)
def retire_player_character(character_id: int, current_user: User = Depends(get_current_user), _character = Depends(require_character_access), db: Session = Depends(get_db)) -> CharacterResponse:
    try:
        return CharacterResponse.model_validate(CharacterService(db).retire_for_player(character_id, current_user.id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
