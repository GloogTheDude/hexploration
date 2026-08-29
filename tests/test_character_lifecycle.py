from db.models import Campaign, CampaignMembership, CampaignRole, Expedition, ExpeditionCharacter, ExpeditionStatus, User, CharacterStatus
from dto.character_dto import CharacterCreate
from services.character_service import CharacterService
from services.errors import ConflictError, ForbiddenOperationError


def seed(db):
    player=User(username='lifecycle_player',email='life@test',password_hash='x')
    other=User(username='lifecycle_other',email='other@test',password_hash='x')
    campaign=Campaign(name='Lifecycle',description=None,epoch_name='Day 1')
    db.add_all([player,other,campaign]); db.flush()
    db.add(CampaignMembership(campaign_id=campaign.id,user_id=player.id,role=CampaignRole.PLAYER)); db.commit()
    return player,other,campaign


def test_player_can_delete_own_character_without_expedition_history(db):
    player,_,campaign=seed(db)
    service=CharacterService(db)
    char=service.create_for_player(campaign.id,player.id,CharacterCreate(owner_user_id=player.id,name='Disposable'))
    service.delete_for_player(char.id,player.id)
    assert service.repo.get(char.id) is None


def test_character_with_expedition_history_must_be_retired_not_deleted(db):
    player,_,campaign=seed(db)
    service=CharacterService(db)
    char=service.create_for_player(campaign.id,player.id,CharacterCreate(owner_user_id=player.id,name='Veteran'))
    expedition=Expedition(campaign_id=campaign.id,name='Old road',status=ExpeditionStatus.RETURNED,start_game_minute=0,current_game_minute=10,return_game_minute=10,current_map_version_id=None,current_q=None,current_r=None,weather_key=None,transport_key='FOOT')
    db.add(expedition); db.flush(); db.add(ExpeditionCharacter(expedition_id=expedition.id,character_id=char.id,joined_game_minute=0,left_game_minute=10)); db.commit()
    try:
        service.delete_for_player(char.id,player.id)
        assert False
    except ConflictError:
        pass
    retired=service.retire_for_player(char.id,player.id)
    assert retired.status == CharacterStatus.RETIRED


def test_player_cannot_delete_another_users_character(db):
    player,other,campaign=seed(db)
    service=CharacterService(db)
    char=service.create_for_player(campaign.id,player.id,CharacterCreate(owner_user_id=player.id,name='Mine'))
    try:
        service.delete_for_player(char.id,other.id)
        assert False
    except ForbiddenOperationError:
        pass
