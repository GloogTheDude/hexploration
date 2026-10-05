from sqlalchemy.orm import Session

from db.models import (
    CampaignMembership,
    CampaignRole,
    Character,
    CharacterStatus,
    ExpeditionCharacter,
    ExpeditionStatus,
    PointOfInterest,
    User,
)
from dto.dm_dashboard_dto import DMExpeditionPlanCreate
from services.dm_dashboard_service import DMDashboardService
from services.errors import ConflictError, ForbiddenOperationError
from tests.factories import make_map_with_two_hexes


def make_user(db: Session, suffix: str) -> User:
    user = User(
        username=f"planner_{suffix}",
        email=f"planner_{suffix}@example.com",
        password_hash="x",
    )
    db.add(user)
    db.flush()
    return user


def make_character(db: Session, campaign, owner: User, *, name: str, minute: int = 0) -> Character:
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=owner.id,
        name=name,
        race="Human",
        character_class="Ranger",
        level=1,
        description=None,
        status=CharacterStatus.ACTIVE,
        current_game_minute=minute,
    )
    db.add(character)
    db.flush()
    return character


def test_dm_planner_creates_ready_active_expedition_atomically(db: Session, campaign):
    dm = make_user(db, "dm")
    owner = make_user(db, "owner")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    _, version, _, destination = make_map_with_two_hexes(db, campaign)
    alice = make_character(db, campaign, owner, name="Alice", minute=80)
    bob = make_character(db, campaign, owner, name="Bob", minute=75)
    db.add(PointOfInterest(feature_id=1, hex_id=destination.id, name="North Gate", kind="TOWN", dm_description=None, is_landmark=True, is_hub=True))
    db.commit()

    result = DMDashboardService(db).create_expedition_plan(
        campaign.id,
        dm.id,
        DMExpeditionPlanCreate(
            name="  Northern Watch  ",
            start_game_minute=90,
            character_ids=[alice.id, bob.id],
            map_version_id=version.id,
            start_now=True,
        ),
    )

    assert result.status == ExpeditionStatus.ACTIVE
    assert result.transport_key is None
    assert result.participant_ids == [alice.id, bob.id]
    expedition = db.get(__import__('db.models', fromlist=['Expedition']).Expedition, result.expedition_id)
    assert expedition.name == "Northern Watch"
    assert (expedition.current_q, expedition.current_r) == (1, 0)
    assert alice.current_game_minute == 90
    assert bob.current_game_minute == 90
    participants = db.query(ExpeditionCharacter).filter_by(expedition_id=result.expedition_id).all()
    assert len(participants) == 2


def test_dm_planner_refuses_temporal_backtracking_without_partial_expedition(db: Session, campaign):
    dm = make_user(db, "dm_backtrack")
    owner = make_user(db, "owner_backtrack")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    traveler = make_character(db, campaign, owner, name="Future Scout", minute=120)
    db.commit()

    before = len(DMDashboardService(db).get(campaign.id, dm.id).expeditions)
    try:
        DMDashboardService(db).create_expedition_plan(
            campaign.id,
            dm.id,
            DMExpeditionPlanCreate(
                name="Impossible",
                start_game_minute=100,
                character_ids=[traveler.id],
                map_version_id=version.id,
                q=source.q,
                r=source.r,
                transport_key="FOOT",
                start_now=False,
            ),
        )
    except ConflictError as exc:
        assert "already at minute 120" in str(exc)
    else:
        raise AssertionError("Expected temporal backtracking to be rejected")

    after = len(DMDashboardService(db).get(campaign.id, dm.id).expeditions)
    assert after == before


def test_dm_planner_rejects_non_dm(db: Session, campaign):
    player = make_user(db, "player")
    owner = make_user(db, "owner_player")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER))
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    character = make_character(db, campaign, owner, name="Scout")
    db.commit()

    try:
        DMDashboardService(db).create_expedition_plan(
            campaign.id,
            player.id,
            DMExpeditionPlanCreate(
                name="Nope",
                start_game_minute=0,
                character_ids=[character.id],
                map_version_id=version.id,
                q=source.q,
                r=source.r,
                transport_key="FOOT",
                start_now=False,
            ),
        )
    except ForbiddenOperationError:
        pass
    else:
        raise AssertionError("Expected DM membership enforcement")


def test_dm_planner_cannot_use_future_map_version(db: Session, campaign):
    dm = make_user(db, "dm_future_map")
    owner = make_user(db, "owner_future_map")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    version.effective_from_game_minute = 200
    character = make_character(db, campaign, owner, name="Early Scout", minute=50)
    db.commit()

    try:
        DMDashboardService(db).create_expedition_plan(
            campaign.id,
            dm.id,
            DMExpeditionPlanCreate(
                name="Too early",
                start_game_minute=100,
                character_ids=[character.id],
                map_version_id=version.id,
                q=source.q,
                r=source.r,
                transport_key="FOOT",
                start_now=False,
            ),
        )
    except ConflictError as exc:
        assert "only becomes effective at minute 200" in str(exc)
    else:
        raise AssertionError("Expected future map version to be rejected")


def test_dm_planner_rejects_character_whose_owner_is_not_registered_player(db: Session, campaign):
    dm = make_user(db, "dm_unregistered")
    outsider = make_user(db, "outsider")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    character = make_character(db, campaign, outsider, name="Outsider Scout")
    db.commit()

    try:
        DMDashboardService(db).create_expedition_plan(
            campaign.id,
            dm.id,
            DMExpeditionPlanCreate(
                name="Invalid party",
                start_game_minute=0,
                character_ids=[character.id],
                map_version_id=version.id,
                q=source.q,
                r=source.r,
                transport_key="FOOT",
                start_now=False,
            ),
        )
    except ForbiddenOperationError as exc:
        assert "registered PLAYER member" in str(exc)
    else:
        raise AssertionError("Expected unregistered character owner to be rejected")


def test_dm_planner_requires_a_hub_on_selected_map_version(db: Session, campaign):
    dm = make_user(db, "dm_no_hub")
    owner = make_user(db, "owner_no_hub")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=owner.id, role=CampaignRole.PLAYER))
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    traveler = make_character(db, campaign, owner, name="Traveler", minute=0)
    db.commit()

    try:
        DMDashboardService(db).create_expedition_plan(
            campaign.id,
            dm.id,
            DMExpeditionPlanCreate(
                name="No hub",
                start_game_minute=0,
                character_ids=[traveler.id],
                map_version_id=version.id,
                start_now=True,
            ),
        )
    except ConflictError as exc:
        assert "hub" in str(exc).lower()
    else:
        raise AssertionError("Expected expedition creation to require a hub")
