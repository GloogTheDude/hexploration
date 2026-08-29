from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    CampaignMembership,
    CampaignRole,
    Character,
    CharacterStatus,
    Expedition,
    ExpeditionCharacter,
    ExpeditionStatus,
    MapEdge,
    MapHex,
    MapVersion,
    PointOfInterest,
    User,
    WorldEvent,
    WorldMap,
)
from services.dm_dashboard_service import DMDashboardService
from services.errors import ForbiddenOperationError


def make_user(db: Session, suffix: str) -> User:
    user = User(username=f"user_{suffix}", email=f"{suffix}@example.com", password_hash="x")
    db.add(user)
    db.flush()
    return user


def test_dm_campaign_list_contains_only_dm_memberships(db: Session):
    dm = make_user(db, "dm")
    dm_campaign = Campaign(name="DM campaign", description=None, epoch_name="Day 1")
    player_campaign = Campaign(name="Player campaign", description=None, epoch_name="Day 1")
    db.add_all([dm_campaign, player_campaign]); db.flush()
    db.add_all([
        CampaignMembership(campaign_id=dm_campaign.id, user_id=dm.id, role=CampaignRole.DM),
        CampaignMembership(campaign_id=player_campaign.id, user_id=dm.id, role=CampaignRole.PLAYER),
    ])
    db.commit()

    result = DMDashboardService(db).list_dm_campaigns(dm.id)

    assert [row.id for row in result] == [dm_campaign.id]
    assert result[0].role == CampaignRole.DM


def test_dm_dashboard_rejects_player_membership(db: Session, campaign):
    player = make_user(db, "player")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER))
    db.commit()

    try:
        DMDashboardService(db).get(campaign.id, player.id)
    except ForbiddenOperationError as exc:
        assert "DM membership required" in str(exc)
    else:
        raise AssertionError("Expected DM-only dashboard to reject PLAYER membership")


def test_dm_dashboard_aggregates_campaign_control_state(db: Session, campaign):
    dm = make_user(db, "owner")
    player = make_user(db, "hero")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.flush()

    character = Character(
        campaign_id=campaign.id, owner_user_id=player.id, name="Scout", race="Human",
        character_class="Ranger", level=3, description=None,
        status=CharacterStatus.ACTIVE, current_game_minute=110,
    )
    world_map = WorldMap(campaign_id=campaign.id, name="North", description="Frozen road")
    db.add_all([character, world_map]); db.flush()
    version = MapVersion(map_id=world_map.id, version=1, name="Spring", width=2, height=1, hex_size=32, effective_from_game_minute=50)
    db.add(version); db.flush()
    h0 = MapHex(map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0, visibility_score=3, travel_cost=1.0, extra_data={})
    h1 = MapHex(map_version_id=version.id, q=1, r=0, terrain_key="FOREST", elevation=1, visibility_score=2, travel_cost=1.5, extra_data={})
    db.add_all([h0, h1]); db.flush()
    db.add(PointOfInterest(feature_id=1, hex_id=h1.id, name="Tower", kind="RUIN", dm_description="secret", is_landmark=True))
    db.add(MapEdge(map_version_id=version.id, from_q=0, from_r=0, to_q=1, to_r=0, feature_type="BRIDGE", feature_id=17, name="Bridge", extra_data={}))
    expedition = Expedition(
        campaign_id=campaign.id, name="Northbound", status=ExpeditionStatus.ACTIVE,
        start_game_minute=100, current_game_minute=140, return_game_minute=None,
        current_map_version_id=version.id, current_q=1, current_r=0,
        weather_key="RAIN", transport_key="FOOT",
    )
    db.add(expedition); db.flush()
    db.add(ExpeditionCharacter(expedition_id=expedition.id, character_id=character.id, joined_game_minute=100, left_game_minute=None))
    db.add(WorldEvent(campaign_id=campaign.id, expedition_id=None, game_minute=160, event_type="WEATHER_CHANGED", target_type=None, target_id=None, payload={"weather_key":"STORM"}, dm_note="incoming"))
    db.commit()

    result = DMDashboardService(db).get(campaign.id, dm.id)

    assert result.campaign.id == campaign.id
    assert result.active_expedition_count == 1
    assert result.character_count == 1
    assert result.map_count == 1
    assert result.campaign_game_minute == 160
    assert result.expeditions[0].participants[0].character_name == "Scout"
    assert result.maps[0].versions[0].hex_count == 2
    assert result.maps[0].versions[0].poi_count == 1
    assert result.maps[0].versions[0].edge_count == 1
    assert result.recent_events[0].event_type == "WEATHER_CHANGED"


def test_dm_can_add_campaign_member_and_dashboard_lists_identity(db: Session, campaign):
    dm = make_user(db, "member_admin")
    player = make_user(db, "new_member")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.commit()

    created = DMDashboardService(db).add_member(campaign.id, dm.id, player.id, CampaignRole.PLAYER)
    dashboard = DMDashboardService(db).get(campaign.id, dm.id)

    assert created.user_id == player.id
    assert created.username == player.username
    assert created.role == CampaignRole.PLAYER
    assert {row.user_id for row in dashboard.members} == {dm.id, player.id}


def test_dm_can_create_character_for_campaign_member(db: Session, campaign):
    from dto.dm_dashboard_dto import DMCharacterCreate

    dm = make_user(db, "character_admin")
    player = make_user(db, "character_owner")
    db.add_all([
        CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM),
        CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER),
    ])
    db.commit()

    character = DMDashboardService(db).create_character(
        campaign.id,
        dm.id,
        DMCharacterCreate(
            owner_user_id=player.id,
            name="Mira",
            race="Human",
            character_class="Ranger",
            level=2,
            current_game_minute=30,
        ),
    )

    assert character.campaign_id == campaign.id
    assert character.owner_user_id == player.id
    assert character.name == "Mira"
    assert character.current_game_minute == 30


def test_dm_can_persist_current_editor_as_campaign_map(db: Session, campaign):
    from dto.dm_dashboard_dto import DMEditorMapCreate
    from models.hexmap import Hexmap
    import routes.map_routes as map_routes

    dm = make_user(db, "map_admin")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.commit()

    previous = map_routes.hexmap
    map_routes.hexmap = Hexmap(2, 2, 24)
    try:
        world_map, version, count = DMDashboardService(db).snapshot_editor_map(
            campaign.id,
            dm.id,
            DMEditorMapCreate(name="First region", version_name="Opening state", effective_from_game_minute=0),
        )
    finally:
        map_routes.hexmap = previous

    assert world_map.campaign_id == campaign.id
    assert version.map_id == world_map.id
    assert version.version == 1
    assert version.width == 2
    assert version.height == 2
    assert count == 4


def test_dm_can_update_campaign_settings(db: Session, campaign):
    from dto.dm_dashboard_dto import DMCampaignUpdate

    dm = make_user(db, "campaign_editor")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM))
    db.commit()

    result = DMDashboardService(db).update_campaign(
        campaign.id,
        dm.id,
        DMCampaignUpdate(name="  Nouvelle Marche  ", epoch_name="An 12", description="  Nouveau pitch  "),
    )

    assert result.name == "Nouvelle Marche"
    assert result.epoch_name == "An 12"
    assert result.description == "Nouveau pitch"
    db.refresh(campaign)
    assert campaign.name == "Nouvelle Marche"


def test_player_cannot_update_or_delete_campaign(db: Session, campaign):
    from dto.dm_dashboard_dto import DMCampaignUpdate

    player = make_user(db, "campaign_intruder")
    db.add(CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER))
    db.commit()

    service = DMDashboardService(db)
    for operation in (
        lambda: service.update_campaign(campaign.id, player.id, DMCampaignUpdate(name="Nope")),
        lambda: service.delete_campaign(campaign.id, player.id),
    ):
        try:
            operation()
        except ForbiddenOperationError:
            pass
        else:
            raise AssertionError("Expected PLAYER campaign mutation to be forbidden")


def test_dm_can_delete_campaign_and_cascade_its_data(db: Session, campaign):
    dm = make_user(db, "campaign_delete")
    player = make_user(db, "campaign_delete_player")
    db.add_all([
        CampaignMembership(campaign_id=campaign.id, user_id=dm.id, role=CampaignRole.DM),
        CampaignMembership(campaign_id=campaign.id, user_id=player.id, role=CampaignRole.PLAYER),
    ])
    db.flush()
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=player.id,
        name="Temporary Hero",
        race="Human",
        character_class="Fighter",
        level=1,
        status=CharacterStatus.ACTIVE,
        current_game_minute=0,
    )
    world_map = WorldMap(campaign_id=campaign.id, name="Temporary Map", description=None)
    db.add_all([character, world_map])
    db.commit()
    campaign_id = campaign.id
    character_id = character.id
    map_id = world_map.id

    DMDashboardService(db).delete_campaign(campaign_id, dm.id)

    assert db.get(Campaign, campaign_id) is None
    assert db.get(Character, character_id) is None
    assert db.get(WorldMap, map_id) is None
