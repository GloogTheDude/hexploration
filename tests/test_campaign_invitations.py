from db.models import Campaign, CampaignMembership, CampaignRole, Character, User
from dto.character_dto import CharacterCreate
from services.campaign_service import CampaignService
from services.invitation_service import CampaignInvitationService
from services.character_service import CharacterService
from services.errors import ConflictError, ForbiddenOperationError

def seed(db):
    dm=User(username="dm_inv",email="dm_inv@test",password_hash="x"); player=User(username="player_inv",email="player_inv@test",password_hash="x"); campaign=Campaign(name="Invite campaign",description=None,epoch_name="Day 1")
    db.add_all([dm,player,campaign]); db.flush(); db.add(CampaignMembership(campaign_id=campaign.id,user_id=dm.id,role=CampaignRole.DM)); db.commit(); return dm,player,campaign

def test_invitation_does_not_create_membership_before_accept(db):
    dm,p,c=seed(db); inv=CampaignInvitationService(db).invite(c.id,dm.id,p.id)
    assert inv.status=="PENDING"; assert CampaignService(db).repo.get_membership(c.id,p.id) is None

def test_accept_invitation_creates_player_membership(db):
    dm,p,c=seed(db); inv=CampaignInvitationService(db).invite(c.id,dm.id,p.id); CampaignInvitationService(db).respond(inv.id,p.id,True)
    m=CampaignService(db).repo.get_membership(c.id,p.id); assert m is not None and m.role==CampaignRole.PLAYER

def test_refused_invitation_does_not_create_membership(db):
    dm,p,c=seed(db); inv=CampaignInvitationService(db).invite(c.id,dm.id,p.id); CampaignInvitationService(db).respond(inv.id,p.id,False)
    assert CampaignService(db).repo.get_membership(c.id,p.id) is None

def test_player_cannot_create_character_before_accepting(db):
    dm,p,c=seed(db); data=CharacterCreate(owner_user_id=p.id,name="Hero")
    try: CharacterService(db).create_for_player(c.id,p.id,data); assert False
    except ForbiddenOperationError: pass

def test_player_can_create_own_character_after_accepting(db):
    dm,p,c=seed(db); inv=CampaignInvitationService(db).invite(c.id,dm.id,p.id); CampaignInvitationService(db).respond(inv.id,p.id,True)
    char=CharacterService(db).create_for_player(c.id,p.id,CharacterCreate(owner_user_id=p.id,name="Hero")); assert char.owner_user_id==p.id

def test_player_cannot_create_character_for_someone_else(db):
    dm,p,c=seed(db); inv=CampaignInvitationService(db).invite(c.id,dm.id,p.id); CampaignInvitationService(db).respond(inv.id,p.id,True)
    try: CharacterService(db).create_for_player(c.id,p.id,CharacterCreate(owner_user_id=dm.id,name="Spoof")); assert False
    except ForbiddenOperationError: pass

def test_dm_can_list_invitation_statuses_and_reinvite_after_refusal(db):
    dm,p,c=seed(db)
    service=CampaignInvitationService(db)
    inv=service.invite(c.id,dm.id,p.id)
    assert [x.status for x in service.list_for_campaign(c.id,dm.id)] == ["PENDING"]
    service.respond(inv.id,p.id,False)
    assert service.list_for_campaign(c.id,dm.id)[0].status == "REFUSED"
    reinvite=service.invite(c.id,dm.id,p.id)
    assert reinvite.id == inv.id
    assert reinvite.status == "PENDING"
