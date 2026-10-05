from __future__ import annotations

from sqlalchemy import func, select
from types import SimpleNamespace
from sqlalchemy.orm import Session, selectinload

from db.models import (
    Campaign,
    CampaignMembership,
    CampaignRole,
    Character,
    CharacterSheetDataVersion,
    CharacterStatus,
    Expedition,
    ExpeditionCharacter,
    ExpeditionStatus,
    MapArea,
    MapEdge,
    MapFeature,
    MapHex,
    MapVersion,
    PointOfInterest,
    WorldEvent,
    WorldMap,
    Movement,
    CharacterMapHexObservation,
    CharacterKnowledgeObservation,
    User,
)
from dto.dm_dashboard_dto import (
    DMCampaignSummary,
    DMCampaignUpdate,
    DMMemberSummary,
    DMCharacterSummary,
    DMDashboardResponse,
    DMExpeditionParticipantSummary,
    DMExpeditionSummary,
    DMMapSummary,
    DMMapVersionSummary,
    DMWorldEventSummary,
    DMExpeditionPlanCreate,
    DMExpeditionPlanResponse,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from repositories.expedition_repository import ExpeditionRepository
from services.visibility_service import VisibilityService
from services.map_feature_service import MapFeatureService


class DMDashboardService:
    RECENT_EVENT_LIMIT = 20

    def __init__(self, db: Session) -> None:
        self.db = db

    def _require_dm(self, campaign_id: int, user_id: int) -> tuple[Campaign, CampaignMembership]:
        campaign = self.db.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError("Campaign not found")

        membership = self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == campaign_id,
                CampaignMembership.user_id == user_id,
            )
        )
        if membership is None or membership.role != CampaignRole.DM:
            raise ForbiddenOperationError("DM membership required for this campaign")
        return campaign, membership

    def _character_summary(self, character: Character) -> DMCharacterSummary:
        owner = self.db.get(User, character.owner_user_id)
        membership = self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == character.campaign_id,
                CampaignMembership.user_id == character.owner_user_id,
            )
        )
        sheet = self.db.scalar(
            select(CharacterSheetDataVersion)
            .where(
                CharacterSheetDataVersion.character_id == character.id,
                CharacterSheetDataVersion.is_current.is_(True),
            )
            .order_by(CharacterSheetDataVersion.version.desc())
        )
        data = dict(sheet.data) if sheet else None
        return DMCharacterSummary(
            id=character.id,
            owner_user_id=character.owner_user_id,
            owner_username=(owner.username if owner is not None else f"User #{character.owner_user_id}"),
            owner_role=(membership.role if membership is not None else None),
            name=character.name,
            race=character.race, character_class=character.character_class, level=character.level,
            status=character.status, current_game_minute=character.current_game_minute,
            current_hp=data.get("current_hp") if data else None,
            max_hp=data.get("max_hp") if data else None,
            armor_class=data.get("armor_class") if data else None,
            passive_perception=data.get("passive_perception") if data else None,
            sheet_version=sheet.version if sheet else None, sheet_data=data,
        )

    def list_dm_campaigns(self, user_id: int) -> list[DMCampaignSummary]:
        rows = self.db.execute(
            select(Campaign, CampaignMembership)
            .join(CampaignMembership, CampaignMembership.campaign_id == Campaign.id)
            .where(
                CampaignMembership.user_id == user_id,
                CampaignMembership.role == CampaignRole.DM,
            )
            .order_by(Campaign.name, Campaign.id)
        ).all()
        return [
            DMCampaignSummary(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                epoch_name=campaign.epoch_name,
                role=membership.role,
            )
            for campaign, membership in rows
        ]


    def update_campaign(self, campaign_id: int, user_id: int, data: DMCampaignUpdate) -> DMCampaignSummary:
        campaign, membership = self._require_dm(campaign_id, user_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("At least one campaign field must be provided")

        if "name" in changes:
            campaign.name = changes["name"].strip()
        if "epoch_name" in changes:
            campaign.epoch_name = changes["epoch_name"].strip()
        if "description" in changes:
            description = changes["description"]
            campaign.description = description.strip() if isinstance(description, str) and description.strip() else None

        self.db.commit()
        self.db.refresh(campaign)
        return DMCampaignSummary(
            id=campaign.id,
            name=campaign.name,
            description=campaign.description,
            epoch_name=campaign.epoch_name,
            role=membership.role,
        )

    def delete_campaign(self, campaign_id: int, user_id: int) -> None:
        campaign, _membership = self._require_dm(campaign_id, user_id)
        self.db.delete(campaign)
        self.db.commit()


    def add_member(self, campaign_id: int, user_id: int, member_user_id: int, role: CampaignRole) -> DMMemberSummary:
        self._require_dm(campaign_id, user_id)
        member = self.db.get(User, member_user_id)
        if member is None:
            raise NotFoundError("User not found")
        existing = self.db.scalar(
            select(CampaignMembership).where(
                CampaignMembership.campaign_id == campaign_id,
                CampaignMembership.user_id == member_user_id,
            )
        )
        if existing is not None:
            raise ConflictError("User is already a member of this campaign")
        membership = CampaignMembership(
            campaign_id=campaign_id,
            user_id=member_user_id,
            role=role,
        )
        self.db.add(membership)
        self.db.commit()
        return DMMemberSummary(
            user_id=member.id, username=member.username, email=member.email, role=membership.role
        )

    def create_character(self, campaign_id: int, user_id: int, data):
        from dto.character_dto import CharacterCreate
        from services.character_service import CharacterService

        self._require_dm(campaign_id, user_id)
        payload = CharacterCreate(
            owner_user_id=data.owner_user_id,
            name=data.name,
            race=data.race,
            character_class=data.character_class,
            level=data.level,
            description=data.description,
            current_game_minute=data.current_game_minute,
        )
        return CharacterService(self.db).create(campaign_id, payload)

    def create_persistent_map(self, campaign_id: int, user_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        return MapPersistenceService(self.db).create_map(
            campaign_id=campaign_id,
            name=data.name,
            description=data.description,
            version_name=data.version_name,
            effective_from_game_minute=data.effective_from_game_minute,
            width=data.width,
            height=data.height,
            hex_size=data.hex_size,
        )

    def paint_persistent_map(self, campaign_id: int, user_id: int, map_id: int, map_version_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        world_map, _ = self._require_map_version(campaign_id, map_version_id)
        if world_map.id != map_id:
            raise NotFoundError("Map version not found")
        return MapPersistenceService(self.db).paint_hexes(
            campaign_id=campaign_id,
            map_id=map_id,
            map_version_id=map_version_id,
            centers=[(center.q, center.r) for center in data.centers],
            terrain_key=data.terrain_key.strip().upper(),
            radius=data.radius,
        )

    def paint_persistent_map_exact(self, campaign_id: int, user_id: int, map_id: int, map_version_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        world_map, _ = self._require_map_version(campaign_id, map_version_id)
        if world_map.id != map_id:
            raise NotFoundError("Map version not found")
        service = MapPersistenceService(self.db)
        rows = []
        for item in data:
            rows = service.paint_hexes(
                campaign_id=campaign_id,
                map_id=map_id,
                map_version_id=map_version_id,
                centers=[(item.q, item.r)],
                terrain_key=item.terrain_key.strip().upper(),
                radius=1,
            )
        return rows

    def update_persistent_map_metadata(self, campaign_id: int, user_id: int, map_id: int, map_version_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        if world_map.id != map_id:
            raise NotFoundError("Map version not found")
        return MapPersistenceService(self.db).update_version_metadata(
            map_id=map_id,
            map_version_id=map_version_id,
            map_name=data.map_name,
            version_name=data.version_name,
            effective_from_game_minute=data.effective_from_game_minute,
        )

    def clone_persistent_map_version(self, campaign_id: int, user_id: int, map_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        world_map, _ = self._require_map_version(campaign_id, data.parent_version_id)
        if world_map.id != map_id:
            raise NotFoundError("Map version not found")
        return MapPersistenceService(self.db).clone_map_version(
            map_id=map_id,
            parent_version_id=data.parent_version_id,
            version_name=data.version_name,
            effective_from_game_minute=data.effective_from_game_minute,
        )


    def create_expedition_plan(
        self,
        campaign_id: int,
        user_id: int,
        data: DMExpeditionPlanCreate,
    ) -> DMExpeditionPlanResponse:
        """Create a ready-to-use expedition from the DM control center.

        Validation is deliberately performed before any flush/commit so a bad
        character, map position, or temporal assignment cannot leave a
        half-created expedition behind. Weather is not stored here: it is world
        truth and will be resolved from WorldEvent at the expedition clock.
        """
        self._require_dm(campaign_id, user_id)

        name = data.name.strip()
        if not name:
            raise ValueError("Expedition name cannot be empty")
        if data.start_game_minute < 0:
            raise ValueError("start_game_minute must be positive")

        character_ids = list(dict.fromkeys(data.character_ids))
        if not character_ids:
            raise ConflictError("An expedition needs at least one character")

        characters = list(
            self.db.scalars(
                select(Character).where(Character.id.in_(character_ids))
            )
        )
        by_id = {character.id: character for character in characters}
        missing = [character_id for character_id in character_ids if character_id not in by_id]
        if missing:
            raise NotFoundError(f"Character not found: {missing[0]}")

        expedition_repo = ExpeditionRepository(self.db)
        for character_id in character_ids:
            character = by_id[character_id]
            if character.campaign_id != campaign_id:
                raise ForbiddenOperationError(
                    "All expedition characters must belong to the campaign"
                )
            membership = self.db.scalar(
                select(CampaignMembership).where(
                    CampaignMembership.campaign_id == campaign_id,
                    CampaignMembership.user_id == character.owner_user_id,
                )
            )
            if membership is None or membership.role != CampaignRole.PLAYER:
                raise ForbiddenOperationError(
                    f"Character {character.name} must belong to a registered PLAYER member"
                )
            if character.status != CharacterStatus.ACTIVE:
                raise ConflictError(
                    f"Character {character.name} is not active"
                )
            if character.current_game_minute > data.start_game_minute:
                raise ConflictError(
                    f"Character {character.name} is already at minute "
                    f"{character.current_game_minute}; expedition cannot start "
                    f"at minute {data.start_game_minute}"
                )
            if expedition_repo.active_expedition_for_character(character_id) is not None:
                raise ConflictError(
                    f"Character {character.name} is already part of another open expedition"
                )

        map_version = self.db.get(MapVersion, data.map_version_id)
        if map_version is None:
            raise NotFoundError("Map version not found")
        world_map = self.db.get(WorldMap, map_version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError(
                "Map version and expedition must belong to the same campaign"
            )
        if map_version.effective_from_game_minute > data.start_game_minute:
            raise ConflictError(
                f"Map version v{map_version.version} only becomes effective at minute "
                f"{map_version.effective_from_game_minute}"
            )
        hub_row = self.db.execute(
            select(PointOfInterest, MapHex)
            .join(MapHex, PointOfInterest.hex_id == MapHex.id)
            .where(
                MapHex.map_version_id == data.map_version_id,
                PointOfInterest.is_hub.is_(True),
            )
            .order_by(PointOfInterest.id)
        ).first()
        if hub_row is None:
            raise ConflictError(
                "Cette version de carte n'a aucun POI marqué comme hub de départ"
            )
        hub, target_hex = hub_row

        expedition = Expedition(
            campaign_id=campaign_id,
            name=name,
            status=(ExpeditionStatus.ACTIVE if data.start_now else ExpeditionStatus.PLANNING),
            start_game_minute=data.start_game_minute,
            current_game_minute=data.start_game_minute,
            return_game_minute=None,
            current_map_version_id=data.map_version_id,
            current_q=target_hex.q,
            current_r=target_hex.r,
            weather_key=None,
            transport_key=None,
        )
        self.db.add(expedition)
        self.db.flush()

        for character_id in character_ids:
            self.db.add(
                ExpeditionCharacter(
                    expedition_id=expedition.id,
                    character_id=character_id,
                    joined_game_minute=data.start_game_minute,
                    left_game_minute=None,
                )
            )
            if data.start_now:
                by_id[character_id].current_game_minute = max(
                    by_id[character_id].current_game_minute,
                    data.start_game_minute,
                )

        self.db.flush()
        if data.start_now:
            VisibilityService(self.db).observe_visible_pois(expedition.id, commit=False)

        self.db.commit()
        self.db.refresh(expedition)
        return DMExpeditionPlanResponse(
            expedition_id=expedition.id,
            status=expedition.status,
            start_game_minute=expedition.start_game_minute,
            current_game_minute=expedition.current_game_minute,
            map_version_id=expedition.current_map_version_id,
            q=expedition.current_q,
            r=expedition.current_r,
            transport_key=expedition.transport_key,
            participant_ids=character_ids,
        )

    def _require_campaign_expedition(
        self, campaign_id: int, expedition_id: int
    ) -> Expedition:
        expedition = self.db.get(Expedition, expedition_id)
        if expedition is None:
            raise NotFoundError("Expedition not found")
        if expedition.campaign_id != campaign_id:
            raise ForbiddenOperationError(
                "Expedition does not belong to this campaign"
            )
        return expedition

    def start_expedition(self, campaign_id: int, expedition_id: int, user_id: int) -> Expedition:
        self._require_dm(campaign_id, user_id)
        self._require_campaign_expedition(campaign_id, expedition_id)
        from services.expedition_service import ExpeditionService
        return ExpeditionService(self.db).start(expedition_id)

    def return_expedition(self, campaign_id: int, expedition_id: int, user_id: int) -> Expedition:
        self._require_dm(campaign_id, user_id)
        self._require_campaign_expedition(campaign_id, expedition_id)
        from services.expedition_service import ExpeditionService
        return ExpeditionService(self.db).return_to_hub(expedition_id)

    def reveal_poi_to_expedition(self, campaign_id: int, expedition_id: int, poi_id: int, user_id: int):
        self._require_dm(campaign_id, user_id)
        self._require_campaign_expedition(campaign_id, expedition_id)
        from services.knowledge_service import KnowledgeService
        return KnowledgeService(self.db).set_poi_player_visibility(expedition_id, poi_id, visible=True)

    def hide_poi_from_expedition(self, campaign_id: int, expedition_id: int, poi_id: int, user_id: int):
        self._require_dm(campaign_id, user_id)
        self._require_campaign_expedition(campaign_id, expedition_id)
        from services.knowledge_service import KnowledgeService
        return KnowledgeService(self.db).set_poi_player_visibility(expedition_id, poi_id, visible=False)

    def get(self, campaign_id: int, user_id: int) -> DMDashboardResponse:
        campaign, membership = self._require_dm(campaign_id, user_id)

        members = list(
            self.db.execute(
                select(CampaignMembership, User)
                .join(User, User.id == CampaignMembership.user_id)
                .where(CampaignMembership.campaign_id == campaign_id)
                .order_by(User.username, User.id)
            ).all()
        )

        characters = list(
            self.db.scalars(
                select(Character)
                .where(Character.campaign_id == campaign_id)
                .order_by(Character.name, Character.id)
            )
        )

        expeditions = list(
            self.db.scalars(
                select(Expedition)
                .where(Expedition.campaign_id == campaign_id)
                .options(
                    selectinload(Expedition.participants)
                    .selectinload(ExpeditionCharacter.character)
                )
                .order_by(Expedition.current_game_minute.desc(), Expedition.id.desc())
            )
        )

        maps = list(
            self.db.scalars(
                select(WorldMap)
                .where(WorldMap.campaign_id == campaign_id)
                .options(selectinload(WorldMap.versions))
                .order_by(WorldMap.name, WorldMap.id)
            )
        )

        map_version_ids = [version.id for world_map in maps for version in world_map.versions]
        hub_by_version: dict[int, tuple[int, str, int, int]] = {}
        if map_version_ids:
            for poi, map_hex in self.db.execute(
                select(PointOfInterest, MapHex)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(
                    MapHex.map_version_id.in_(map_version_ids),
                    PointOfInterest.is_hub.is_(True),
                )
                .order_by(PointOfInterest.id)
            ).all():
                hub_by_version.setdefault(
                    map_hex.map_version_id,
                    (poi.id, poi.name, map_hex.q, map_hex.r),
                )
        hex_counts: dict[int, int] = {}
        poi_counts: dict[int, int] = {}
        edge_counts: dict[int, int] = {}
        if map_version_ids:
            hex_counts = dict(
                self.db.execute(
                    select(MapHex.map_version_id, func.count(MapHex.id))
                    .where(MapHex.map_version_id.in_(map_version_ids))
                    .group_by(MapHex.map_version_id)
                ).all()
            )
            poi_counts = dict(
                self.db.execute(
                    select(MapHex.map_version_id, func.count(PointOfInterest.id))
                    .join(PointOfInterest, PointOfInterest.hex_id == MapHex.id)
                    .where(MapHex.map_version_id.in_(map_version_ids))
                    .group_by(MapHex.map_version_id)
                ).all()
            )
            edge_counts = dict(
                self.db.execute(
                    select(MapEdge.map_version_id, func.count(MapEdge.id))
                    .where(MapEdge.map_version_id.in_(map_version_ids))
                    .group_by(MapEdge.map_version_id)
                ).all()
            )

        recent_events = list(
            self.db.scalars(
                select(WorldEvent)
                .where(WorldEvent.campaign_id == campaign_id)
                .order_by(WorldEvent.game_minute.desc(), WorldEvent.id.desc())
                .limit(self.RECENT_EVENT_LIMIT)
            )
        )

        clock_candidates = [0]
        clock_candidates.extend(character.current_game_minute for character in characters)
        clock_candidates.extend(expedition.current_game_minute for expedition in expeditions)
        clock_candidates.extend(event.game_minute for event in recent_events)
        clock_candidates.extend(
            version.effective_from_game_minute
            for world_map in maps
            for version in world_map.versions
        )
        campaign_game_minute = max(clock_candidates)

        return DMDashboardResponse(
            campaign=DMCampaignSummary(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                epoch_name=campaign.epoch_name,
                role=membership.role,
            ),
            campaign_game_minute=campaign_game_minute,
            active_expedition_count=sum(
                1 for expedition in expeditions if expedition.status == ExpeditionStatus.ACTIVE
            ),
            character_count=len(characters),
            map_count=len(maps),
            members=[
                DMMemberSummary(
                    user_id=user.id,
                    username=user.username,
                    email=user.email,
                    role=row.role,
                )
                for row, user in members
            ],
            characters=[
                self._character_summary(character)
                for character in characters
            ],
            expeditions=[
                DMExpeditionSummary(
                    id=expedition.id,
                    name=expedition.name,
                    status=expedition.status,
                    start_game_minute=expedition.start_game_minute,
                    current_game_minute=expedition.current_game_minute,
                    return_game_minute=expedition.return_game_minute,
                    current_map_version_id=expedition.current_map_version_id,
                    current_q=expedition.current_q,
                    current_r=expedition.current_r,
                    weather_key=expedition.weather_key,
                    transport_key=expedition.transport_key,
                    ping_q=expedition.ping_q,
                    ping_r=expedition.ping_r,
                    ping_game_minute=expedition.ping_game_minute,
                    participants=[
                        DMExpeditionParticipantSummary(
                            character_id=participant.character_id,
                            character_name=participant.character.name,
                            joined_game_minute=participant.joined_game_minute,
                            left_game_minute=participant.left_game_minute,
                        )
                        for participant in expedition.participants
                    ],
                )
                for expedition in expeditions
            ],
            maps=[
                DMMapSummary(
                    id=world_map.id,
                    name=world_map.name,
                    description=world_map.description,
                    versions=[
                        DMMapVersionSummary(
                            id=version.id,
                            version=version.version,
                            name=version.name,
                            width=version.width,
                            height=version.height,
                            hex_size=version.hex_size,
                            effective_from_game_minute=version.effective_from_game_minute,
                            hex_count=(version.width * version.height if version.default_terrain_key else hex_counts.get(version.id, 0)),
                            poi_count=poi_counts.get(version.id, 0),
                            edge_count=edge_counts.get(version.id, 0),
                            hub_poi_id=hub_by_version.get(version.id, (None, None, None, None))[0],
                            hub_name=hub_by_version.get(version.id, (None, None, None, None))[1],
                            hub_q=hub_by_version.get(version.id, (None, None, None, None))[2],
                            hub_r=hub_by_version.get(version.id, (None, None, None, None))[3],
                        )
                        for version in sorted(world_map.versions, key=lambda row: row.version, reverse=True)
                    ],
                )
                for world_map in maps
            ],
            recent_events=[
                DMWorldEventSummary(
                    id=event.id,
                    game_minute=event.game_minute,
                    event_type=event.event_type,
                    expedition_id=event.expedition_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    payload=event.payload or {},
                    dm_note=event.dm_note,
                )
                for event in recent_events
            ],
        )

    def delete_map(self, campaign_id: int, user_id: int, map_id: int) -> None:
        self._require_dm(campaign_id, user_id)
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("Map does not belong to this campaign")

        version_ids = list(self.db.scalars(select(MapVersion.id).where(MapVersion.map_id == map_id)))
        if version_ids:
            if self.db.scalar(select(Expedition.id).where(Expedition.current_map_version_id.in_(version_ids)).limit(1)) is not None:
                raise ConflictError("Cannot delete this map: a campaign expedition references one of its versions")
            if self.db.scalar(select(Movement.id).where(Movement.map_version_id.in_(version_ids)).limit(1)) is not None:
                raise ConflictError("Cannot delete this map: movement history references one of its versions")
            if self.db.scalar(select(CharacterMapHexObservation.id).where(CharacterMapHexObservation.map_version_id.in_(version_ids)).limit(1)) is not None:
                raise ConflictError("Cannot delete this map: player map knowledge references one of its versions")

        features = list(self.db.scalars(select(MapFeature).where(MapFeature.map_id == map_id)))
        if features:
            conditions = []
            from sqlalchemy import and_, or_
            for feature in features:
                conditions.append(and_(WorldEvent.target_type == feature.feature_type, WorldEvent.target_id == feature.feature_id))
            if conditions and self.db.scalar(select(CharacterKnowledgeObservation.id).where(or_(*conditions)).limit(1)) is not None:
                raise ConflictError("Cannot delete this map: character knowledge references one of its features")
            # WorldEvents are authored history of these semantic features. For a map that
            # has never entered player history, hard-delete means deleting that authored
            # history too; otherwise stale target_type/target_id rows survive forever.
            if conditions:
                for event in self.db.scalars(select(WorldEvent).where(WorldEvent.campaign_id == campaign_id, or_(*conditions))):
                    self.db.delete(event)

        self.db.delete(world_map)
        self.db.commit()

    def _require_map_version(self, campaign_id: int, map_version_id: int) -> tuple[WorldMap, MapVersion]:
        version = self.db.get(MapVersion, map_version_id)
        if version is None:
            raise NotFoundError("MapVersion not found")
        world_map = self.db.get(WorldMap, version.map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("MapVersion does not belong to this campaign")
        return world_map, version

    def get_map_workbench(self, campaign_id: int, user_id: int, map_version_id: int):
        from dto.dm_dashboard_dto import (
            DMAreaWorkbench,
            DMEdgeWorkbench,
            DMMapHexWorkbench,
            DMMapWorkbenchResponse,
            DMPOIWorkbench,
        )
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        hexes = list(self.db.scalars(select(MapHex).where(MapHex.map_version_id == version.id).order_by(MapHex.q, MapHex.r)))
        pois = list(
            self.db.execute(
                select(PointOfInterest, MapHex)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(MapHex.map_version_id == version.id)
                .order_by(PointOfInterest.name, PointOfInterest.id)
            ).all()
        )
        edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id).order_by(MapEdge.feature_type, MapEdge.feature_id, MapEdge.segment_index, MapEdge.id)))
        areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == version.id).order_by(MapArea.id)))
        return DMMapWorkbenchResponse(
            campaign_id=campaign_id,
            map_id=world_map.id,
            map_name=world_map.name,
            map_version_id=version.id,
            version=version.version,
            version_name=version.name,
            effective_from_game_minute=version.effective_from_game_minute,
            width=version.width,
            height=version.height,
            hex_size=version.hex_size,
            default_terrain_key=version.default_terrain_key,
            hexes=[DMMapHexWorkbench(id=h.id, q=h.q, r=h.r, terrain_key=h.terrain_key, elevation=h.elevation, visibility_score=h.visibility_score, travel_cost=h.travel_cost, extra_data=h.extra_data or {}) for h in hexes],
            pois=[DMPOIWorkbench(id=poi.id, feature_id=poi.feature_id, hex_id=h.id, q=h.q, r=h.r, name=poi.name, kind=poi.kind, dm_description=poi.dm_description, player_description=poi.player_description, requires_discovery=poi.requires_discovery, is_landmark=poi.is_landmark, is_hub=poi.is_hub) for poi, h in pois],
            edges=[DMEdgeWorkbench(id=e.id, from_q=e.from_q, from_r=e.from_r, to_q=e.to_q, to_r=e.to_r, feature_type=e.feature_type, feature_id=e.feature_id, segment_index=e.segment_index, name=e.name, extra_data=e.extra_data or {}) for e in edges],
            areas=[DMAreaWorkbench(id=a.id, feature_type=a.feature_type, feature_id=a.feature_id, name=a.name, cells=list(a.cells or []), extra_data=a.extra_data or {}) for a in areas],
        )


    def world_editor_snapshot(self, campaign_id: int, user_id: int, map_version_id: int):
        """Capture all semantic editor state needed for transactional undo/redo."""
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        poi_rows = list(self.db.execute(
            select(PointOfInterest, MapHex)
            .join(MapHex, PointOfInterest.hex_id == MapHex.id)
            .where(MapHex.map_version_id == version.id)
            .order_by(PointOfInterest.id)
        ).all())
        edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id).order_by(MapEdge.id)))
        areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == version.id).order_by(MapArea.id)))
        features = list(self.db.scalars(select(MapFeature).where(MapFeature.map_id == world_map.id).order_by(MapFeature.id)))
        feature_keys = {(f.feature_type, f.feature_id) for f in features}
        events = list(self.db.scalars(select(WorldEvent).where(WorldEvent.campaign_id == campaign_id).order_by(WorldEvent.id)))
        events = [e for e in events if e.target_type is not None and e.target_id is not None and (e.target_type, e.target_id) in feature_keys]
        return {
            "map_version_id": version.id,
            "features": [{"feature_type": f.feature_type, "feature_id": f.feature_id, "downstream_feature_type": f.downstream_feature_type, "downstream_feature_id": f.downstream_feature_id} for f in features],
            "pois": [{"feature_id": poi.feature_id, "q": h.q, "r": h.r, "name": poi.name, "kind": poi.kind, "dm_description": poi.dm_description, "player_description": poi.player_description, "requires_discovery": poi.requires_discovery, "is_landmark": poi.is_landmark, "is_hub": poi.is_hub} for poi, h in poi_rows],
            "edges": [{"from_q": e.from_q, "from_r": e.from_r, "to_q": e.to_q, "to_r": e.to_r, "feature_type": e.feature_type, "feature_id": e.feature_id, "segment_index": e.segment_index, "name": e.name, "extra_data": dict(e.extra_data or {})} for e in edges],
            "areas": [{"feature_type": a.feature_type, "feature_id": a.feature_id, "name": a.name, "cells": list(a.cells or []), "extra_data": dict(a.extra_data or {})} for a in areas],
            "events": [{"expedition_id": e.expedition_id, "game_minute": e.game_minute, "event_type": e.event_type, "target_type": e.target_type, "target_id": e.target_id, "payload": dict(e.payload or {}), "dm_note": e.dm_note} for e in events],
        }

    def restore_world_editor_snapshot(self, campaign_id: int, user_id: int, map_version_id: int, data) -> None:
        """Atomically restore semantic world-editor state for undo/redo.

        Stable feature IDs are preserved. Concrete DB row IDs may change; the
        frontend reloads the workbench immediately after each restore.
        """
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        if data.map_version_id != version.id:
            raise ValueError("Snapshot belongs to another map version")

        current_pois = list(self.db.scalars(
            select(PointOfInterest).join(MapHex, PointOfInterest.hex_id == MapHex.id).where(MapHex.map_version_id == version.id)
        ))
        current_edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id)))
        current_areas = list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == version.id)))
        map_features = list(self.db.scalars(select(MapFeature).where(MapFeature.map_id == world_map.id)))
        map_keys = {(f.feature_type, f.feature_id) for f in map_features}
        current_events = list(self.db.scalars(select(WorldEvent).where(WorldEvent.campaign_id == campaign_id)))
        for row in current_events:
            if row.target_type is not None and row.target_id is not None and (row.target_type, row.target_id) in map_keys:
                self.db.delete(row)
        for row in current_pois + current_edges + current_areas:
            self.db.delete(row)
        self.db.flush()

        feature_service = MapFeatureService(self.db)
        wanted = {(str(item["feature_type"]).upper(), int(item["feature_id"])): item for item in data.features}
        for feature in map_features:
            item = wanted.get((feature.feature_type, feature.feature_id))
            if item is not None:
                feature.downstream_feature_type = item.get("downstream_feature_type")
                feature.downstream_feature_id = item.get("downstream_feature_id")
            else:
                feature.downstream_feature_type = None
                feature.downstream_feature_id = None
        for (_, _), item in wanted.items():
            identity = feature_service.ensure(campaign_id=campaign_id, map_id=world_map.id, feature_type=item["feature_type"], feature_id=int(item["feature_id"]))
            identity.downstream_feature_type = item.get("downstream_feature_type")
            identity.downstream_feature_id = item.get("downstream_feature_id")

        for item in data.pois:
            feature_service.ensure(campaign_id=campaign_id, map_id=world_map.id, feature_type="POI", feature_id=int(item["feature_id"]))
            h = self._ensure_map_hex(version, int(item["q"]), int(item["r"]))
            self.db.add(PointOfInterest(feature_id=int(item["feature_id"]), hex_id=h.id, name=item["name"], kind=item.get("kind"), dm_description=item.get("dm_description"), player_description=item.get("player_description"), requires_discovery=bool(item.get("requires_discovery", False)), is_landmark=bool(item.get("is_landmark", False)), is_hub=bool(item.get("is_hub", False))))
        for item in data.edges:
            feature_service.ensure(campaign_id=campaign_id, map_id=world_map.id, feature_type=item["feature_type"], feature_id=int(item["feature_id"]))
            self._ensure_map_hex(version, int(item["from_q"]), int(item["from_r"]))
            self._ensure_map_hex(version, int(item["to_q"]), int(item["to_r"]))
            self.db.add(MapEdge(map_version_id=version.id, from_q=int(item["from_q"]), from_r=int(item["from_r"]), to_q=int(item["to_q"]), to_r=int(item["to_r"]), feature_type=str(item["feature_type"]).upper(), feature_id=int(item["feature_id"]), segment_index=int(item.get("segment_index", 0)), name=item.get("name"), extra_data=dict(item.get("extra_data") or {})))
        for item in data.areas:
            feature_service.ensure(campaign_id=campaign_id, map_id=world_map.id, feature_type=item["feature_type"], feature_id=int(item["feature_id"]))
            cells = [{"q": int(c["q"]), "r": int(c["r"])} for c in item.get("cells", [])]
            for c in cells:
                self._ensure_map_hex(version, c["q"], c["r"])
            self.db.add(MapArea(map_version_id=version.id, feature_type=str(item["feature_type"]).upper(), feature_id=int(item["feature_id"]), name=item.get("name"), cells=cells, extra_data=dict(item.get("extra_data") or {})))
        for item in data.events:
            self.db.add(WorldEvent(campaign_id=campaign_id, expedition_id=item.get("expedition_id"), game_minute=int(item["game_minute"]), event_type=item["event_type"], target_type=item.get("target_type"), target_id=item.get("target_id"), payload=dict(item.get("payload") or {}), dm_note=item.get("dm_note")))
        self.db.commit()

    @staticmethod
    def _edge_touches(edge: MapEdge, q: int, r: int) -> bool:
        data = edge.extra_data or {}
        pf = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
        pt = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
        return (int(pf["q"]), int(pf["r"])) == (q, r) or (int(pt["q"]), int(pt["r"])) == (q, r)

    def clear_hex_features(self, campaign_id: int, user_id: int, map_version_id: int, q: int, r: int) -> None:
        """Remove semantic content anchored on/touching one hex, never terrain."""
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        if not self._coord_in_version(version, q, r):
            raise NotFoundError("Map hex not found")

        # POIs are genuinely anchored on the selected cell.
        pois = list(self.db.scalars(select(PointOfInterest).join(MapHex, PointOfInterest.hex_id == MapHex.id).where(MapHex.map_version_id == version.id, MapHex.q == q, MapHex.r == r)))
        for poi in pois:
            self._assert_feature_can_be_hard_deleted(campaign_id, "POI", poi.feature_id)
            feature_id = poi.feature_id
            self.db.delete(poi)
            self.db.flush()
            self._cleanup_feature_identity_if_unused(campaign_id, "POI", feature_id)

        # Area deletion removes only this cell. A one-cell area is a whole-feature delete.
        for area in list(self.db.scalars(select(MapArea).where(MapArea.map_version_id == version.id))):
            cells = list(area.cells or [])
            if not any(int(c.get("q")) == q and int(c.get("r")) == r for c in cells):
                continue
            remaining = [c for c in cells if not (int(c.get("q")) == q and int(c.get("r")) == r)]
            if remaining:
                area.cells = remaining
            else:
                self._assert_feature_can_be_hard_deleted(campaign_id, area.feature_type, area.feature_id)
                ft, fid = area.feature_type, area.feature_id
                self.db.delete(area)
                self.db.flush()
                self._cleanup_feature_identity_if_unused(campaign_id, ft, fid)

        # Remove linear segments touching the cell. If this disconnects a ROAD/RIVER,
        # split the surviving components into distinct semantic identities.
        all_edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id)))
        affected = {(e.feature_type, e.feature_id) for e in all_edges if self._edge_touches(e, q, r)}
        for feature_type, feature_id in affected:
            rows = [e for e in all_edges if e.feature_type == feature_type and e.feature_id == feature_id]
            touching = [e for e in rows if self._edge_touches(e, q, r)]
            remaining = [e for e in rows if e not in touching]
            if not remaining:
                self._assert_feature_can_be_hard_deleted(campaign_id, feature_type, feature_id)
                for edge in touching:
                    self.db.delete(edge)
                self.db.flush()
                self._cleanup_feature_identity_if_unused(campaign_id, feature_type, feature_id)
                continue
            for edge in touching:
                self.db.delete(edge)
            self.db.flush()
            if feature_type not in {"ROAD", "RIVER"}:
                continue
            # Undirected connectivity is enough to identify surviving pieces.
            node_to_edges: dict[tuple[int, int], list[MapEdge]] = {}
            def endpoints(edge):
                data = edge.extra_data or {}
                pf = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
                pt = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
                return (int(pf["q"]), int(pf["r"])), (int(pt["q"]), int(pt["r"]))
            for edge in remaining:
                a, b = endpoints(edge)
                node_to_edges.setdefault(a, []).append(edge); node_to_edges.setdefault(b, []).append(edge)
            unseen = set(e.id for e in remaining); by_id = {e.id: e for e in remaining}; components=[]
            while unseen:
                first = next(iter(unseen)); stack=[first]; ids=set()
                while stack:
                    eid=stack.pop()
                    if eid in ids: continue
                    ids.add(eid); unseen.discard(eid)
                    a,b=endpoints(by_id[eid])
                    for node in (a,b):
                        for neighbor in node_to_edges.get(node,[]):
                            if neighbor.id not in ids: stack.append(neighbor.id)
                components.append([by_id[eid] for eid in ids])
            if len(components) <= 1:
                continue
            if feature_type == "RIVER":
                primary = max(components, key=lambda comp: max(e.segment_index for e in comp))
            else:
                primary = max(components, key=len)
            identity_service = MapFeatureService(self.db)
            for comp in components:
                if comp is primary:
                    new_id = feature_id
                else:
                    new_id = identity_service.allocate(campaign_id=campaign_id, map_id=world_map.id, feature_type=feature_type).feature_id
                for idx, edge in enumerate(sorted(comp, key=lambda e: (e.segment_index, e.id))):
                    edge.feature_id = new_id
                    edge.segment_index = idx
                if feature_type == "RIVER" and comp is not primary:
                    ident = identity_service.ensure(campaign_id=campaign_id, map_id=world_map.id, feature_type="RIVER", feature_id=new_id)
                    ident.downstream_feature_type = None
                    ident.downstream_feature_id = None
        self.db.commit()

    @staticmethod
    def _axial_round(q: float, r: float) -> tuple[int, int]:
        x, z, y = q, r, -q-r
        rx, ry, rz = round(x), round(y), round(z)
        xd, yd, zd = abs(rx-x), abs(ry-y), abs(rz-z)
        if xd > yd and xd > zd:
            rx = -ry-rz
        elif yd > zd:
            ry = -rx-rz
        else:
            rz = -rx-ry
        return int(rx), int(rz)

    @classmethod
    def _hex_line(cls, a, b) -> list[tuple[int, int]]:
        distance = (abs(a.q-b.q) + abs(a.q+a.r-b.q-b.r) + abs(a.r-b.r)) // 2
        if distance == 0:
            return [(a.q, a.r)]
        return [cls._axial_round(a.q + (b.q-a.q)*(i/distance), a.r + (b.r-a.r)*(i/distance)) for i in range(distance+1)]

    def _ensure_map_hex(self, version: MapVersion, q: int, r: int) -> MapHex:
        existing = self.db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == q, MapHex.r == r))
        if existing is not None:
            return existing
        if not version.default_terrain_key:
            raise NotFoundError("Map hex not found")
        from models.hexmap import Hexmap
        from models.constants import BASE_TERRAINS
        col, row = Hexmap.axial_to_offset(q, r, version.width, version.height)
        if not (0 <= col < version.width and 0 <= row < version.height):
            raise NotFoundError("Map hex not found")
        terrain = BASE_TERRAINS[version.default_terrain_key]
        result = MapHex(map_version_id=version.id, q=q, r=r, terrain_key=version.default_terrain_key, elevation=terrain.elevation, visibility_score=terrain.visibility_score, travel_cost=terrain.travel_cost, extra_data={})
        self.db.add(result)
        self.db.flush()
        return result

    def create_poi(self, campaign_id: int, user_id: int, map_version_id: int, data):
        self._require_dm(campaign_id, user_id)
        self._require_map_version(campaign_id, map_version_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        map_hex = self._ensure_map_hex(version, data.q, data.r)
        if getattr(data, "feature_id", None) is not None:
            identity = MapFeatureService(self.db).ensure(
                campaign_id=campaign_id, map_id=world_map.id, feature_type="POI", feature_id=data.feature_id
            )
        else:
            identity = MapFeatureService(self.db).allocate(
                campaign_id=campaign_id, map_id=world_map.id, feature_type="POI"
            )
        poi = PointOfInterest(
            feature_id=identity.feature_id,
            hex_id=map_hex.id,
            name=data.name.strip(),
            kind=data.kind.strip().upper() if data.kind and data.kind.strip() else None,
            dm_description=data.dm_description,
            player_description=data.player_description,
            requires_discovery=data.requires_discovery,
            is_landmark=data.is_landmark,
            is_hub=data.is_hub,
        )
        self.db.add(poi)
        self.db.flush()
        if poi.is_hub:
            for other in self.db.scalars(
                select(PointOfInterest)
                .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                .where(
                    MapHex.map_version_id == map_version_id,
                    PointOfInterest.id != poi.id,
                    PointOfInterest.is_hub.is_(True),
                )
            ):
                other.is_hub = False
        # Every newly-authored POI gets an explicit temporal birth.  The stable
        # feature_id is the WorldEvent target, so moving/editing the concrete
        # POI later does not break its history.
        self.db.add(WorldEvent(
            campaign_id=campaign_id,
            expedition_id=None,
            game_minute=data.creation_game_minute,
            event_type="POI_CREATED",
            target_type="POI",
            target_id=poi.feature_id,
            payload={"visible_at_distance": bool(poi.is_landmark)},
            dm_note=None,
        ))
        self.db.commit()
        self.db.refresh(poi)
        return poi

    def _require_campaign_poi(self, campaign_id: int, poi_id: int) -> PointOfInterest:
        row = self.db.execute(
            select(PointOfInterest, WorldMap)
            .join(MapHex, PointOfInterest.hex_id == MapHex.id)
            .join(MapVersion, MapHex.map_version_id == MapVersion.id)
            .join(WorldMap, MapVersion.map_id == WorldMap.id)
            .where(PointOfInterest.id == poi_id)
        ).first()
        if row is None:
            raise NotFoundError("POI not found")
        poi, world_map = row
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("POI does not belong to this campaign")
        return poi

    def update_poi(self, campaign_id: int, user_id: int, poi_id: int, data):
        self._require_dm(campaign_id, user_id)
        poi = self._require_campaign_poi(campaign_id, poi_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            poi.name = changes["name"].strip()
        if "kind" in changes:
            raw = changes["kind"]
            poi.kind = raw.strip().upper() if raw and raw.strip() else None
        if "dm_description" in changes:
            poi.dm_description = changes["dm_description"]
        if "player_description" in changes:
            poi.player_description = changes["player_description"]
        if "requires_discovery" in changes:
            poi.requires_discovery = bool(changes["requires_discovery"])
        if "is_landmark" in changes and changes["is_landmark"] is not None:
            poi.is_landmark = changes["is_landmark"]
        if "is_hub" in changes and changes["is_hub"] is not None:
            poi.is_hub = changes["is_hub"]
            if poi.is_hub:
                map_version_id = self.db.scalar(select(MapHex.map_version_id).where(MapHex.id == poi.hex_id))
                for other in self.db.scalars(
                    select(PointOfInterest)
                    .join(MapHex, PointOfInterest.hex_id == MapHex.id)
                    .where(
                        MapHex.map_version_id == map_version_id,
                        PointOfInterest.id != poi.id,
                        PointOfInterest.is_hub.is_(True),
                    )
                ):
                    other.is_hub = False
        self.db.commit()
        self.db.refresh(poi)
        return poi

    def create_feature_edge(self, campaign_id: int, user_id: int, map_version_id: int, data):
        from dto.map_edge_dto import MapEdgeCreate
        from services.map_edge_service import MapEdgeService
        self._require_dm(campaign_id, user_id)
        self._require_map_version(campaign_id, map_version_id)
        feature_type = data.feature_type.strip().upper()
        if not feature_type:
            raise ValueError("feature_type cannot be empty")
        world_map, _ = self._require_map_version(campaign_id, map_version_id)
        identity = MapFeatureService(self.db).allocate(
            campaign_id=campaign_id, map_id=world_map.id, feature_type=feature_type
        )
        return MapEdgeService(self.db).create(
            map_version_id,
            MapEdgeCreate(
                from_q=data.from_q,
                from_r=data.from_r,
                to_q=data.to_q,
                to_r=data.to_r,
                feature_type=feature_type,
                feature_id=identity.feature_id,
                name=data.name,
                extra_data=data.extra_data,
            ),
        )

    def _assert_feature_can_be_hard_deleted(self, campaign_id: int, feature_type: str, feature_id: int) -> None:
        has_event = self.db.scalar(select(WorldEvent.id).where(
            WorldEvent.campaign_id == campaign_id,
            WorldEvent.target_type == feature_type,
            WorldEvent.target_id == feature_id,
        ).limit(1))
        if has_event is not None:
            raise ConflictError("Cannot delete this feature: its timeline already contains world events")
        has_knowledge = self.db.scalar(select(CharacterKnowledgeObservation.id).join(
            Character, CharacterKnowledgeObservation.character_id == Character.id
        ).where(
            Character.campaign_id == campaign_id,
            CharacterKnowledgeObservation.target_type == feature_type,
            CharacterKnowledgeObservation.target_id == feature_id,
        ).limit(1))
        if has_knowledge is not None:
            raise ConflictError("Cannot delete this feature: player knowledge already references it")

    def _cleanup_feature_identity_if_unused(self, campaign_id: int, feature_type: str, feature_id: int) -> None:
        identity = self.db.scalar(select(MapFeature).where(
            MapFeature.campaign_id == campaign_id,
            MapFeature.feature_type == feature_type,
            MapFeature.feature_id == feature_id,
        ))
        if identity is None:
            return
        if feature_type == "POI":
            still_used = self.db.scalar(select(PointOfInterest.id).where(PointOfInterest.feature_id == feature_id).limit(1))
        elif feature_type in {"LAKE", "INLAND_SEA", "WETLAND", "REGION"}:
            still_used = self.db.scalar(select(MapArea.id).where(MapArea.feature_type == feature_type, MapArea.feature_id == feature_id).limit(1))
        else:
            still_used = self.db.scalar(select(MapEdge.id).where(MapEdge.feature_type == feature_type, MapEdge.feature_id == feature_id).limit(1))
        if still_used is None:
            self.db.delete(identity)

    def delete_poi(self, campaign_id: int, user_id: int, poi_id: int) -> None:
        self._require_dm(campaign_id, user_id)
        poi = self._require_campaign_poi(campaign_id, poi_id)
        feature_id = poi.feature_id

        # POI_CREATED is lifecycle metadata created automatically with the POI;
        # it must not make a pristine POI impossible to delete.  Any *other*
        # world event still protects the feature from hard deletion.
        blocking_event = self.db.scalar(select(WorldEvent.id).where(
            WorldEvent.campaign_id == campaign_id,
            WorldEvent.target_type == "POI",
            WorldEvent.target_id == feature_id,
            WorldEvent.event_type != "POI_CREATED",
        ).limit(1))
        if blocking_event is not None:
            raise ConflictError("Cannot delete this feature: its timeline already contains world events")
        has_knowledge = self.db.scalar(select(CharacterKnowledgeObservation.id).join(
            Character, CharacterKnowledgeObservation.character_id == Character.id
        ).where(
            Character.campaign_id == campaign_id,
            CharacterKnowledgeObservation.target_type == "POI",
            CharacterKnowledgeObservation.target_id == feature_id,
        ).limit(1))
        if has_knowledge is not None:
            raise ConflictError("Cannot delete this feature: player knowledge already references it")

        for event in self.db.scalars(select(WorldEvent).where(
            WorldEvent.campaign_id == campaign_id,
            WorldEvent.target_type == "POI",
            WorldEvent.target_id == feature_id,
            WorldEvent.event_type == "POI_CREATED",
        )):
            self.db.delete(event)
        self.db.delete(poi)
        self.db.flush()
        self._cleanup_feature_identity_if_unused(campaign_id, "POI", feature_id)
        self.db.commit()

    def update_linear_feature(self, campaign_id: int, user_id: int, edge_id: int, data):
        self._require_dm(campaign_id, user_id)
        edge = self._require_campaign_edge(campaign_id, edge_id)
        name = data.name.strip() if data.name and data.name.strip() else None
        rows = list(self.db.scalars(select(MapEdge).where(
            MapEdge.map_version_id == edge.map_version_id,
            MapEdge.feature_type == edge.feature_type,
            MapEdge.feature_id == edge.feature_id,
        )))
        for row in rows:
            row.name = name
        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        return rows

    def update_area_feature(self, campaign_id: int, user_id: int, area_id: int, data):
        self._require_dm(campaign_id, user_id)
        area = self._require_campaign_area(campaign_id, area_id)
        area.name = data.name.strip() if data.name and data.name.strip() else None
        self.db.commit()
        self.db.refresh(area)
        return {
            "id": area.id, "feature_type": area.feature_type, "feature_id": area.feature_id,
            "name": area.name, "cells": list(area.cells or []), "extra_data": dict(area.extra_data or {}),
        }

    def delete_linear_feature(self, campaign_id: int, user_id: int, edge_id: int) -> None:
        self._require_dm(campaign_id, user_id)
        edge = self._require_campaign_edge(campaign_id, edge_id)
        self._assert_feature_can_be_hard_deleted(campaign_id, edge.feature_type, edge.feature_id)
        if edge.feature_type == "RIVER":
            tributary = self.db.scalar(select(MapFeature.id).where(
                MapFeature.campaign_id == campaign_id,
                MapFeature.downstream_feature_type == "RIVER",
                MapFeature.downstream_feature_id == edge.feature_id,
            ).limit(1))
            if tributary is not None:
                raise ConflictError("Cannot delete this river: tributaries flow into it")
        rows = list(self.db.scalars(select(MapEdge).where(
            MapEdge.map_version_id == edge.map_version_id,
            MapEdge.feature_type == edge.feature_type,
            MapEdge.feature_id == edge.feature_id,
        )))
        feature_type, feature_id = edge.feature_type, edge.feature_id
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        self._cleanup_feature_identity_if_unused(campaign_id, feature_type, feature_id)
        self.db.commit()

    def _require_campaign_area(self, campaign_id: int, area_id: int) -> MapArea:
        row = self.db.execute(
            select(MapArea, WorldMap)
            .join(MapVersion, MapArea.map_version_id == MapVersion.id)
            .join(WorldMap, MapVersion.map_id == WorldMap.id)
            .where(MapArea.id == area_id)
        ).first()
        if row is None:
            raise NotFoundError("Map area not found")
        area, world_map = row
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("Map area does not belong to this campaign")
        return area

    def delete_area_feature(self, campaign_id: int, user_id: int, area_id: int) -> None:
        self._require_dm(campaign_id, user_id)
        area = self._require_campaign_area(campaign_id, area_id)
        self._assert_feature_can_be_hard_deleted(campaign_id, area.feature_type, area.feature_id)
        feature_type, feature_id = area.feature_type, area.feature_id
        self.db.delete(area)
        self.db.flush()
        self._cleanup_feature_identity_if_unused(campaign_id, feature_type, feature_id)
        self.db.commit()

    def _coord_in_version(self, version: MapVersion, q: int, r: int) -> bool:
        from models.hexmap import Hexmap
        col, row = Hexmap.axial_to_offset(q, r, version.width, version.height)
        return 0 <= col < version.width and 0 <= row < version.height

    def _terrain_key_at(self, version: MapVersion, q: int, r: int) -> str | None:
        if not self._coord_in_version(version, q, r):
            return None
        row = self.db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.q == q, MapHex.r == r))
        return row.terrain_key if row is not None else version.default_terrain_key

    def _is_water_coord(self, version: MapVersion, q: int, r: int) -> bool:
        if self._terrain_key_at(version, q, r) == "SEA":
            return True
        water_areas = list(self.db.scalars(select(MapArea).where(
            MapArea.map_version_id == version.id,
            MapArea.feature_type.in_(["LAKE", "INLAND_SEA"]),
        )))
        return any(any(cell.get("q") == q and cell.get("r") == r for cell in (area.cells or [])) for area in water_areas)

    def _river_nodes(self, version: MapVersion) -> dict[tuple[int, int], set[int]]:
        nodes: dict[tuple[int, int], set[int]] = {}
        rows = list(self.db.scalars(select(MapEdge).where(
            MapEdge.map_version_id == version.id,
            MapEdge.feature_type == "RIVER",
        )))
        for edge in rows:
            pf = (edge.extra_data or {}).get("path_from") or {"q": edge.from_q, "r": edge.from_r}
            pt = (edge.extra_data or {}).get("path_to") or {"q": edge.to_q, "r": edge.to_r}
            for coord in ((int(pf["q"]), int(pf["r"])), (int(pt["q"]), int(pt["r"]))):
                nodes.setdefault(coord, set()).add(edge.feature_id)
        return nodes

    def _water_outlet_at(self, version: MapVersion, q: int, r: int) -> dict | None:
        if self._terrain_key_at(version, q, r) == "SEA":
            return {"type": "SEA"}
        water_areas = list(self.db.scalars(select(MapArea).where(
            MapArea.map_version_id == version.id,
            MapArea.feature_type.in_(["LAKE", "INLAND_SEA"]),
        )))
        for area in water_areas:
            if any(cell.get("q") == q and cell.get("r") == r for cell in (area.cells or [])):
                return {"type": area.feature_type, "feature_id": area.feature_id}
        return None

    def _finish_river_path(
        self, version: MapVersion, path: list[tuple[int, int]]
    ) -> tuple[list[tuple[int, int]], int | None, dict | None]:
        """Resolve only explicit river endpoints and explicit confluences.

        Water is never guessed anymore. A river reaches SEA/LAKE/INLAND_SEA
        only when the authored path actually contains the corresponding water
        hex. Existing rivers are still treated as semantic graph nodes: the
        new river stops at the first encountered river and links downstream.
        """
        if not path:
            return path, None, None

        river_nodes = self._river_nodes(version)

        # Stop at the first explicitly crossed river. The authored start node
        # is skipped so a river may originate from an existing confluence.
        for index, coord in enumerate(path[1:], start=1):
            downstream_ids = sorted(river_nodes.get(coord, ()))
            if downstream_ids:
                downstream_id = downstream_ids[0]
                return path[: index + 1], downstream_id, {
                    "type": "RIVER", "feature_id": downstream_id,
                    "q": coord[0], "r": coord[1],
                }

        q, r = path[-1]
        water = self._water_outlet_at(version, q, r)
        if water is not None:
            return path, None, {**water, "q": q, "r": r}

        # No implicit coastal search: the DM must select the actual water hex.
        return path, None, None

    def create_linear_feature(self, campaign_id: int, user_id: int, map_version_id: int, data):
        from dto.map_edge_dto import MapEdgeCreate
        from services.map_edge_service import MapEdgeService
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        feature_type = data.feature_type.strip().upper()
        if feature_type not in {"ROAD", "RIVER", "PASSAGE", "TRAVERSAL"}:
            raise ValueError("Unsupported linear feature type")
        if len(data.waypoints) < 2:
            raise ValueError("At least two waypoints are required")
        path: list[tuple[int, int]] = []
        for start, end in zip(data.waypoints, data.waypoints[1:]):
            segment = self._hex_line(start, end)
            if path and segment and segment[0] == path[-1]:
                segment = segment[1:]
            path.extend(segment)
        downstream_river_id: int | None = None
        river_outlet: dict | None = None
        river_source: dict | None = None
        if feature_type == "RIVER":
            path, downstream_river_id, river_outlet = self._finish_river_path(version, path)
            if path:
                source_water = self._water_outlet_at(version, *path[0])
                if source_water is not None:
                    river_source = {**source_water, "q": path[0][0], "r": path[0][1]}
        if len(path) < 2:
            raise ValueError("Linear feature path is empty")
        for q, r in path:
            self._ensure_map_hex(version, q, r)
        identity = MapFeatureService(self.db).allocate(campaign_id=campaign_id, map_id=world_map.id, feature_type=feature_type)
        if feature_type == "RIVER" and downstream_river_id is not None:
            identity.downstream_feature_type = "RIVER"
            identity.downstream_feature_id = downstream_river_id
        service = MapEdgeService(self.db)
        created = []
        try:
            for index, ((q1, r1), (q2, r2)) in enumerate(zip(path, path[1:])):
                segment_data = dict(data.extra_data)
                segment_data.update({
                    "path_from": {"q": q1, "r": r1},
                    "path_to": {"q": q2, "r": r2},
                    "path_directional": feature_type == "RIVER",
                })
                if feature_type == "RIVER" and index == 0 and river_source is not None:
                    segment_data["source"] = river_source
                if feature_type == "RIVER" and index == len(path) - 2 and river_outlet is not None:
                    segment_data["outlet"] = river_outlet
                    if downstream_river_id is not None:
                        segment_data["downstream_river_feature_id"] = downstream_river_id
                created.append(service.create(map_version_id, MapEdgeCreate(
                    from_q=q1, from_r=r1, to_q=q2, to_r=r2,
                    feature_type=feature_type, feature_id=identity.feature_id,
                    segment_index=index, name=data.name, extra_data=segment_data,
                ), commit=False))
            self.db.commit()
            for edge in created:
                self.db.refresh(edge)
        except Exception:
            self.db.rollback()
            raise
        return created

    def _ordered_linear_chain(self, edges: list[MapEdge], feature_type: str) -> list[tuple[int, int]]:
        """Return one continuous path for mergeable ROAD/RIVER edge sets.

        ROAD is treated as an undirected chain (or loop). RIVER keeps the
        stored path_from -> path_to direction and must form one directed chain.
        Branching networks are intentionally rejected: merging changes semantic
        identity, it must not silently collapse junctions.
        """
        if not edges:
            raise ValueError("No linear feature edges to merge")

        def directed(edge: MapEdge) -> tuple[tuple[int, int], tuple[int, int]]:
            data = edge.extra_data or {}
            pf = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
            pt = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
            return (int(pf["q"]), int(pf["r"])), (int(pt["q"]), int(pt["r"]))

        # De-duplicate exact geometry that may exist under two accidental
        # feature identities before rebuilding the single merged feature.
        unique: dict[frozenset[tuple[int, int]], tuple[tuple[int, int], tuple[int, int]]] = {}
        for edge in edges:
            a, b = directed(edge)
            key = frozenset((a, b))
            if key in unique:
                if feature_type == "RIVER" and unique[key] != (a, b):
                    raise ConflictError("Selected rivers use the same corridor in opposite directions")
                continue
            unique[key] = (a, b)

        if feature_type == "RIVER":
            outgoing: dict[tuple[int, int], tuple[int, int]] = {}
            indegree: dict[tuple[int, int], int] = {}
            nodes: set[tuple[int, int]] = set()
            for a, b in unique.values():
                if a in outgoing and outgoing[a] != b:
                    raise ConflictError("Selected rivers form a branch and cannot be merged into one river")
                outgoing[a] = b
                indegree[b] = indegree.get(b, 0) + 1
                indegree.setdefault(a, indegree.get(a, 0))
                if indegree[b] > 1:
                    raise ConflictError("Selected rivers form a confluence and cannot be merged into one river")
                nodes.update((a, b))
            starts = [n for n in nodes if indegree.get(n, 0) == 0 and n in outgoing]
            ends = [n for n in nodes if n not in outgoing and indegree.get(n, 0) == 1]
            if len(starts) != 1 or len(ends) != 1:
                raise ConflictError("Selected rivers must form one continuous upstream-to-downstream chain")
            path = [starts[0]]
            seen = {starts[0]}
            while path[-1] in outgoing:
                nxt = outgoing[path[-1]]
                if nxt in seen:
                    raise ConflictError("A river merge cannot create a cycle")
                path.append(nxt)
                seen.add(nxt)
            if len(path) - 1 != len(unique):
                raise ConflictError("Selected rivers are not all connected")
            return path

        adjacency: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for a, b in unique.values():
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)
        if any(len(neighbors) > 2 for neighbors in adjacency.values()):
            raise ConflictError("Selected roads form a branch; merge only one continuous route at a time")
        # Connectivity check.
        root = next(iter(adjacency))
        seen = {root}
        stack = [root]
        while stack:
            cur = stack.pop()
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        if len(seen) != len(adjacency):
            raise ConflictError("Selected roads are not connected")
        endpoints = [node for node, neighbors in adjacency.items() if len(neighbors) == 1]
        if len(endpoints) not in {0, 2}:
            raise ConflictError("Selected roads do not form one continuous route")
        # Prefer the first selected feature's authored start when it is a valid
        # endpoint. This makes the retained feature identity feel stable.
        first_a, _ = directed(edges[0])
        start = first_a if first_a in endpoints or not endpoints else endpoints[0]
        if endpoints and start not in endpoints:
            start = endpoints[0]
        path = [start]
        prev = None
        while True:
            choices = [n for n in adjacency[path[-1]] if n != prev]
            if not choices:
                break
            nxt = choices[0]
            if len(path) > 1 and nxt == path[0]:
                path.append(nxt)
                break
            prev, nxt_prev = path[-1], nxt
            path.append(nxt_prev)
            if len(path) > len(unique) + 1:
                raise ConflictError("Invalid route cycle")
        if len(path) - 1 != len(unique):
            raise ConflictError("Selected roads do not form one continuous route")
        return path

    def merge_linear_features(self, campaign_id: int, user_id: int, edge_ids: list[int]) -> list[MapEdge]:
        """Merge several accidental ROAD/RIVER feature identities into one.

        The first selected feature keeps its stable feature_id. Absorbed
        identities are only allowed when they have no timeline/player knowledge
        and no geometry in another MapVersion, preventing history corruption.
        """
        self._require_dm(campaign_id, user_id)
        if len(edge_ids) < 2:
            raise ValueError("Select at least two linear features to merge")

        representatives: list[MapEdge] = []
        seen_features: set[tuple[str, int]] = set()
        for edge_id in edge_ids:
            edge = self._require_campaign_edge(campaign_id, edge_id)
            key = (edge.feature_type, edge.feature_id)
            if key not in seen_features:
                seen_features.add(key)
                representatives.append(edge)
        if len(representatives) < 2:
            raise ValueError("Select at least two distinct linear features to merge")

        feature_type = representatives[0].feature_type
        map_version_id = representatives[0].map_version_id
        if feature_type not in {"ROAD", "RIVER"}:
            raise ValueError("Only ROAD and RIVER features can be merged")
        if any(e.feature_type != feature_type for e in representatives):
            raise ValueError("Merge only features of the same type")
        if any(e.map_version_id != map_version_id for e in representatives):
            raise ValueError("All merged features must belong to the same map version")

        feature_ids = [e.feature_id for e in representatives]
        selected_rows = list(self.db.scalars(select(MapEdge).where(
            MapEdge.map_version_id == map_version_id,
            MapEdge.feature_type == feature_type,
            MapEdge.feature_id.in_(feature_ids),
        ).order_by(MapEdge.feature_id, MapEdge.segment_index, MapEdge.id)))
        primary_id = representatives[0].feature_id
        primary_name = representatives[0].name

        # ROAD is a connected graph, not necessarily one polyline. Branches and
        # cycles are valid road networks; only disconnected selections are rejected.
        if feature_type == "ROAD":
            def road_nodes(edge):
                d=edge.extra_data or {}
                pf=d.get("path_from") or {"q":edge.from_q,"r":edge.from_r}
                pt=d.get("path_to") or {"q":edge.to_q,"r":edge.to_r}
                return (int(pf["q"]),int(pf["r"])),(int(pt["q"]),int(pt["r"]))
            adjacency={}
            unique={}
            for edge in selected_rows:
                a,b=road_nodes(edge); key=frozenset((a,b))
                unique.setdefault(key,edge)
                adjacency.setdefault(a,set()).add(b); adjacency.setdefault(b,set()).add(a)
            root=next(iter(adjacency),None); seen=set()
            if root is not None:
                stack=[root]
                while stack:
                    cur=stack.pop()
                    if cur in seen: continue
                    seen.add(cur); stack.extend(adjacency.get(cur,())-seen)
            if len(seen)!=len(adjacency):
                raise ConflictError("Selected roads are not connected")
            for absorbed_id in feature_ids[1:]:
                self._assert_feature_can_be_hard_deleted(campaign_id,"ROAD",absorbed_id)
                other_version=self.db.scalar(select(MapEdge.id).where(MapEdge.feature_type=="ROAD",MapEdge.feature_id==absorbed_id,MapEdge.map_version_id!=map_version_id).limit(1))
                if other_version is not None: raise ConflictError("Cannot merge a feature that already exists in another map version")
            keep=set(id(edge) for edge in unique.values())
            duplicates=[edge for edge in selected_rows if id(edge) not in keep]
            for edge in duplicates:
                self.db.delete(edge)
            # Flush duplicate corridors first so reassignment cannot collide with
            # the unique (version, coordinates, feature identity) constraint.
            self.db.flush()
            kept=[edge for edge in selected_rows if id(edge) in keep]
            for edge in kept:
                edge.feature_id=primary_id
                if primary_name: edge.name=primary_name
            for index,edge in enumerate(kept): edge.segment_index=index
            self.db.flush()
            for absorbed_id in feature_ids[1:]: self._cleanup_feature_identity_if_unused(campaign_id,"ROAD",absorbed_id)
            self.db.commit()
            return list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id==map_version_id,MapEdge.feature_type=="ROAD",MapEdge.feature_id==primary_id).order_by(MapEdge.segment_index,MapEdge.id)))

        river_plan = None
        if feature_type == "RIVER":
            def river_nodes(edge: MapEdge):
                data = edge.extra_data or {}
                pf = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
                pt = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
                return (int(pf["q"]), int(pf["r"])), (int(pt["q"]), int(pt["r"]))

            unique_rows: dict[frozenset[tuple[int, int]], MapEdge] = {}
            adjacency: dict[tuple[int, int], set[tuple[int, int]]] = {}
            for edge in selected_rows:
                a, b = river_nodes(edge)
                key = frozenset((a, b))
                # Prefer geometry from the retained semantic identity when two
                # accidental river features overlap on the same corridor.
                previous = unique_rows.get(key)
                if previous is None or (previous.feature_id != primary_id and edge.feature_id == primary_id):
                    unique_rows[key] = edge
                adjacency.setdefault(a, set()).add(b)
                adjacency.setdefault(b, set()).add(a)

            root = next(iter(adjacency), None)
            seen_nodes: set[tuple[int, int]] = set()
            if root is not None:
                stack = [root]
                while stack:
                    cur = stack.pop()
                    if cur in seen_nodes:
                        continue
                    seen_nodes.add(cur)
                    stack.extend(adjacency.get(cur, set()) - seen_nodes)
            if len(seen_nodes) != len(adjacency):
                raise ConflictError("Selected rivers are not connected")
            # A merged river may contain any number of confluences, but it may
            # not contain a hydrological loop. For a connected undirected graph,
            # tree geometry has exactly |V|-1 unique corridors.
            if unique_rows and len(unique_rows) != len(adjacency) - 1:
                raise ConflictError("A merged river network cannot contain a cycle")

            # Resolve a single downstream sink. Explicit external outlets win.
            # Internal RIVER outlets are ignored because they disappear into the
            # merged network. If no explicit outlet exists, keep the authored
            # terminal of the primary feature as the downstream sink.
            outlet_candidates: dict[tuple[int, int], dict] = {}
            for edge in selected_rows:
                data = edge.extra_data or {}
                outlet = data.get("outlet")
                if not outlet:
                    continue
                if outlet.get("type") == "RIVER" and outlet.get("feature_id") in feature_ids:
                    continue
                q = outlet.get("q")
                r = outlet.get("r")
                if q is None or r is None:
                    _, terminal = river_nodes(edge)
                    q, r = terminal
                outlet_candidates[(int(q), int(r))] = dict(outlet)
            if len(outlet_candidates) > 1:
                raise ConflictError("Selected rivers have multiple downstream outlets")

            if outlet_candidates:
                sink, sink_outlet = next(iter(outlet_candidates.items()))
            else:
                primary_rows = sorted(
                    (edge for edge in selected_rows if edge.feature_id == primary_id),
                    key=lambda edge: (edge.segment_index, edge.id),
                )
                if not primary_rows:
                    raise ConflictError("Primary river geometry not found")
                _, sink = river_nodes(primary_rows[-1])
                sink_outlet = None

            if sink not in adjacency:
                raise ConflictError("River downstream endpoint is outside the selected network")
            if sink_outlet is not None and len(adjacency[sink]) != 1:
                raise ConflictError("Merged river must have one corridor entering its downstream outlet")

            # Root the tree at the sink. Every corridor is then oriented from
            # its upstream child toward its parent, allowing arbitrary valid
            # confluences while keeping one coherent downstream direction.
            parent: dict[tuple[int, int], tuple[int, int] | None] = {sink: None}
            distance: dict[tuple[int, int], int] = {sink: 0}
            queue = [sink]
            while queue:
                cur = queue.pop(0)
                for nxt in adjacency[cur]:
                    if nxt in parent:
                        continue
                    parent[nxt] = cur
                    distance[nxt] = distance[cur] + 1
                    queue.append(nxt)

            source_by_coord: dict[tuple[int, int], dict] = {}
            for edge in selected_rows:
                data = edge.extra_data or {}
                source = data.get("source")
                if source and source.get("q") is not None and source.get("r") is not None:
                    source_by_coord[(int(source["q"]), int(source["r"]))] = dict(source)

            planned_rows = []
            for key, edge in unique_rows.items():
                a, b = tuple(key)
                if parent.get(a) == b:
                    upstream, downstream = a, b
                elif parent.get(b) == a:
                    upstream, downstream = b, a
                else:
                    raise ConflictError("River network orientation failed")
                planned_rows.append((distance[upstream], upstream, downstream, edge))
            # Stable order for persistence/debugging. In a graph segment_index
            # is no longer a path order; deeper tributaries come first and the
            # downstream corridor comes last.
            planned_rows.sort(key=lambda item: (-item[0], item[1], item[2], item[3].id))
            river_plan = {
                "rows": planned_rows,
                "sink": sink,
                "sink_outlet": sink_outlet,
                "sources": source_by_coord,
                "adjacency": adjacency,
            }

        # Absorbed semantic identities must be safe to erase. Geometry in
        # another version means this is no longer merely an editor cleanup.
        for absorbed_id in feature_ids[1:]:
            self._assert_feature_can_be_hard_deleted(campaign_id, feature_type, absorbed_id)
            other_version = self.db.scalar(select(MapEdge.id).where(
                MapEdge.feature_type == feature_type,
                MapEdge.feature_id == absorbed_id,
                MapEdge.map_version_id != map_version_id,
            ).limit(1))
            if other_version is not None:
                raise ConflictError("Cannot merge a feature that already exists in another map version")

        identities = {
            row.feature_id: row for row in self.db.scalars(select(MapFeature).where(
                MapFeature.campaign_id == campaign_id,
                MapFeature.feature_type == feature_type,
                MapFeature.feature_id.in_(feature_ids),
            ))
        }
        primary_identity = identities.get(primary_id)
        if primary_identity is None:
            raise NotFoundError("Primary map feature identity not found")

        if feature_type == "RIVER":
            assert river_plan is not None
            sink_outlet = river_plan["sink_outlet"]
            downstream_type = sink_outlet.get("type") if sink_outlet else None
            downstream_id = sink_outlet.get("feature_id") if sink_outlet and sink_outlet.get("type") == "RIVER" else None
            primary_identity.downstream_feature_type = downstream_type if downstream_type == "RIVER" else None
            primary_identity.downstream_feature_id = downstream_id

            # Tributaries outside the selection that used to join an absorbed
            # semantic identity now join the retained river feature.
            for tributary in self.db.scalars(select(MapFeature).where(
                MapFeature.campaign_id == campaign_id,
                MapFeature.downstream_feature_type == "RIVER",
                MapFeature.downstream_feature_id.in_(feature_ids[1:]),
            )):
                if tributary.feature_id not in feature_ids:
                    tributary.downstream_feature_id = primary_id

            keep_ids = {id(item[3]) for item in river_plan["rows"]}
            duplicates = [edge for edge in selected_rows if id(edge) not in keep_ids]
            for edge in duplicates:
                self.db.delete(edge)
            self.db.flush()

            try:
                for index, (_, upstream, downstream, edge) in enumerate(river_plan["rows"]):
                    data = dict(edge.extra_data or {})
                    data.pop("source", None)
                    data.pop("outlet", None)
                    data.pop("downstream_river_feature_id", None)
                    data["path_from"] = {"q": upstream[0], "r": upstream[1]}
                    data["path_to"] = {"q": downstream[0], "r": downstream[1]}
                    data["path_directional"] = True
                    if len(river_plan["adjacency"][upstream]) == 1 and upstream in river_plan["sources"]:
                        data["source"] = river_plan["sources"][upstream]
                    if downstream == river_plan["sink"] and river_plan["sink_outlet"] is not None:
                        data["outlet"] = river_plan["sink_outlet"]
                        if downstream_type == "RIVER" and downstream_id is not None:
                            data["downstream_river_feature_id"] = downstream_id
                    edge.feature_id = primary_id
                    edge.segment_index = index
                    edge.name = primary_name or edge.name
                    edge.extra_data = data
                self.db.flush()
                for absorbed_id in feature_ids[1:]:
                    self._cleanup_feature_identity_if_unused(campaign_id, "RIVER", absorbed_id)
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            return list(self.db.scalars(select(MapEdge).where(
                MapEdge.map_version_id == map_version_id,
                MapEdge.feature_type == "RIVER",
                MapEdge.feature_id == primary_id,
            ).order_by(MapEdge.segment_index, MapEdge.id)))

        # Legacy/simple-chain rebuilding remains available for any future linear
        # type routed through this branch. ROAD is handled earlier as a graph.
        path = self._ordered_linear_chain(selected_rows, feature_type)
        source_by_segment: dict[frozenset[tuple[int, int]], MapEdge] = {}
        for edge in selected_rows:
            data = edge.extra_data or {}
            pf = data.get("path_from") or {"q": edge.from_q, "r": edge.from_r}
            pt = data.get("path_to") or {"q": edge.to_q, "r": edge.to_r}
            a = (int(pf["q"]), int(pf["r"]))
            b = (int(pt["q"]), int(pt["r"]))
            source_by_segment.setdefault(frozenset((a, b)), edge)

        for edge in selected_rows:
            self.db.delete(edge)
        self.db.flush()

        from dto.map_edge_dto import MapEdgeCreate
        from services.map_edge_service import MapEdgeService
        edge_service = MapEdgeService(self.db)
        created: list[MapEdge] = []
        try:
            for index, (a, b) in enumerate(zip(path, path[1:])):
                source = source_by_segment.get(frozenset((a, b)))
                extra = dict(source.extra_data or {}) if source else {}
                extra["path_from"] = {"q": a[0], "r": a[1]}
                extra["path_to"] = {"q": b[0], "r": b[1]}
                extra["path_directional"] = feature_type == "RIVER"
                created.append(edge_service.create(map_version_id, MapEdgeCreate(
                    from_q=a[0], from_r=a[1], to_q=b[0], to_r=b[1],
                    feature_type=feature_type, feature_id=primary_id,
                    segment_index=index, name=primary_name or (source.name if source else None),
                    extra_data=extra,
                ), commit=False))
            self.db.flush()
            for absorbed_id in feature_ids[1:]:
                self._cleanup_feature_identity_if_unused(campaign_id, feature_type, absorbed_id)
            self.db.commit()
            for edge in created:
                self.db.refresh(edge)
        except Exception:
            self.db.rollback()
            raise
        return created

    def create_area_feature(self, campaign_id: int, user_id: int, map_version_id: int, data):
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        feature_type = data.feature_type.strip().upper()
        if feature_type not in {"LAKE", "INLAND_SEA", "WETLAND", "REGION"}:
            raise ValueError("Unsupported area feature type")
        unique = []
        seen = set()
        for cell in data.cells:
            key = (cell.q, cell.r)
            if key in seen:
                continue
            seen.add(key)
            self._ensure_map_hex(version, cell.q, cell.r)
            unique.append({"q": cell.q, "r": cell.r})
        if not unique:
            raise ValueError("Area must contain at least one hex")
        identity = MapFeatureService(self.db).allocate(campaign_id=campaign_id, map_id=world_map.id, feature_type=feature_type)
        area = MapArea(map_version_id=map_version_id, feature_type=feature_type, feature_id=identity.feature_id, name=data.name, cells=unique, extra_data=dict(data.extra_data))
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return {"id": area.id, "map_version_id": area.map_version_id, "feature_type": area.feature_type, "feature_id": area.feature_id, "name": area.name, "cells": area.cells, "extra_data": area.extra_data}

    def _require_campaign_edge(self, campaign_id: int, edge_id: int) -> MapEdge:
        row = self.db.execute(
            select(MapEdge, WorldMap)
            .join(MapVersion, MapEdge.map_version_id == MapVersion.id)
            .join(WorldMap, MapVersion.map_id == WorldMap.id)
            .where(MapEdge.id == edge_id)
        ).first()
        if row is None:
            raise NotFoundError("Map edge not found")
        edge, world_map = row
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("Map edge does not belong to this campaign")
        return edge

    def create_poi_world_event(self, campaign_id: int, user_id: int, poi_id: int, data):
        from dto.world_event_dto import WorldEventCreate
        from services.world_event_service import WorldEventService
        self._require_dm(campaign_id, user_id)
        poi = self._require_campaign_poi(campaign_id, poi_id)
        return WorldEventService(self.db).create(
            campaign_id,
            WorldEventCreate(
                game_minute=data.game_minute,
                event_type=data.event_type,
                expedition_id=data.expedition_id,
                target_type="POI",
                target_id=poi.feature_id,
                payload=data.payload,
                dm_note=data.dm_note,
            ),
        )

    def create_edge_world_event(self, campaign_id: int, user_id: int, edge_id: int, data):
        from dto.world_event_dto import WorldEventCreate
        from services.world_event_service import WorldEventService
        self._require_dm(campaign_id, user_id)
        edge = self._require_campaign_edge(campaign_id, edge_id)
        return WorldEventService(self.db).create(
            campaign_id,
            WorldEventCreate(
                game_minute=data.game_minute,
                event_type=data.event_type,
                target_type=edge.feature_type,
                target_id=edge.feature_id,
                payload=data.payload,
                dm_note=data.dm_note,
            ),
        )
