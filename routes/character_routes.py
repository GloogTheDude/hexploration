from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from dto.character_dto import CharacterCreate, CharacterResponse
from services.character_service import CharacterService
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError


router = APIRouter(tags=["characters"])


@router.post(
    "/api/campaigns/{campaign_id}/characters",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_character(
    campaign_id: int,
    data: CharacterCreate,
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
    db: Session = Depends(get_db),
) -> list[CharacterResponse]:
    try:
        characters = CharacterService(db).list_for_user(user_id)
        return [CharacterResponse.model_validate(c) for c in characters]
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/api/characters/{character_id}",
    response_model=CharacterResponse,
)
def get_character(
    character_id: int,
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
def create_player_character(campaign_id: int, data: CharacterCreate, user_id: int, db: Session = Depends(get_db)) -> CharacterResponse:
    try:
        return CharacterResponse.model_validate(CharacterService(db).create_for_player(campaign_id, user_id, data))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/api/characters/{character_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player_character(character_id: int, user_id: int, db: Session = Depends(get_db)) -> None:
    try:
        CharacterService(db).delete_for_player(character_id, user_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/api/characters/{character_id}/retire", response_model=CharacterResponse)
def retire_player_character(character_id: int, user_id: int, db: Session = Depends(get_db)) -> CharacterResponse:
    try:
        return CharacterResponse.model_validate(CharacterService(db).retire_for_player(character_id, user_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ForbiddenOperationError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
