from __future__ import annotations

from sqlalchemy import func, select
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
    MapEdge,
    MapFeature,
    MapHex,
    MapVersion,
    PointOfInterest,
    WorldEvent,
    WorldMap,
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
from services.movement_modifiers import get_transport_modifier
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
            id=character.id, owner_user_id=character.owner_user_id, name=character.name,
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

    def snapshot_editor_map(self, campaign_id: int, user_id: int, data):
        from services.map_persistence_service import MapPersistenceService

        self._require_dm(campaign_id, user_id)
        return MapPersistenceService(self.db).snapshot_current_editor_map(
            campaign_id=campaign_id,
            name=data.name,
            description=data.description,
            version_name=data.version_name,
            effective_from_game_minute=data.effective_from_game_minute,
        )

    def load_map_version_into_editor(self, campaign_id: int, user_id: int, map_version_id: int):
        from services.map_persistence_service import MapPersistenceService
        self._require_dm(campaign_id, user_id)
        world_map, version = self._require_map_version(campaign_id, map_version_id)
        loaded_map, loaded_version, count = MapPersistenceService(self.db).load_version_into_editor(version.id)
        return loaded_map, loaded_version, count

    def snapshot_new_map_version(self, campaign_id: int, user_id: int, map_id: int, data):
        from services.map_persistence_service import MapPersistenceService
        self._require_dm(campaign_id, user_id)
        world_map = self.db.get(WorldMap, map_id)
        if world_map is None:
            raise NotFoundError("Map not found")
        if world_map.campaign_id != campaign_id:
            raise ForbiddenOperationError("Map does not belong to this campaign")
        return MapPersistenceService(self.db).snapshot_new_version_from_editor(
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
        target_hex = self.db.scalar(
            select(MapHex).where(
                MapHex.map_version_id == data.map_version_id,
                MapHex.q == data.q,
                MapHex.r == data.r,
            )
        )
        if target_hex is None:
            raise NotFoundError("Starting hex not found in this map version")

        transport = get_transport_modifier(data.transport_key)
        expedition = Expedition(
            campaign_id=campaign_id,
            name=name,
            status=(ExpeditionStatus.ACTIVE if data.start_now else ExpeditionStatus.PLANNING),
            start_game_minute=data.start_game_minute,
            current_game_minute=data.start_game_minute,
            return_game_minute=None,
            current_map_version_id=data.map_version_id,
            current_q=data.q,
            current_r=data.r,
            weather_key=None,
            transport_key=(transport.key if transport is not None else None),
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
                            hex_count=hex_counts.get(version.id, 0),
                            poi_count=poi_counts.get(version.id, 0),
                            edge_count=edge_counts.get(version.id, 0),
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
        edges = list(self.db.scalars(select(MapEdge).where(MapEdge.map_version_id == version.id).order_by(MapEdge.id)))
        return DMMapWorkbenchResponse(
            campaign_id=campaign_id,
            map_id=world_map.id,
            map_name=world_map.name,
            map_version_id=version.id,
            version=version.version,
            version_name=version.name,
            effective_from_game_minute=version.effective_from_game_minute,
            hex_size=version.hex_size,
            hexes=[DMMapHexWorkbench(id=h.id, q=h.q, r=h.r, terrain_key=h.terrain_key, elevation=h.elevation, visibility_score=h.visibility_score, travel_cost=h.travel_cost, extra_data=h.extra_data or {}) for h in hexes],
            pois=[DMPOIWorkbench(id=poi.id, feature_id=poi.feature_id, hex_id=h.id, q=h.q, r=h.r, name=poi.name, kind=poi.kind, dm_description=poi.dm_description, is_landmark=poi.is_landmark) for poi, h in pois],
            edges=[DMEdgeWorkbench(id=e.id, from_q=e.from_q, from_r=e.from_r, to_q=e.to_q, to_r=e.to_r, feature_type=e.feature_type, feature_id=e.feature_id, name=e.name, extra_data=e.extra_data or {}) for e in edges],
        )

    def create_poi(self, campaign_id: int, user_id: int, map_version_id: int, data):
        self._require_dm(campaign_id, user_id)
        self._require_map_version(campaign_id, map_version_id)
        map_hex = self.db.scalar(select(MapHex).where(MapHex.map_version_id == map_version_id, MapHex.q == data.q, MapHex.r == data.r))
        if map_hex is None:
            raise NotFoundError("Map hex not found")
        world_map, _ = self._require_map_version(campaign_id, map_version_id)
        identity = MapFeatureService(self.db).allocate(
            campaign_id=campaign_id, map_id=world_map.id, feature_type="POI"
        )
        poi = PointOfInterest(
            feature_id=identity.feature_id,
            hex_id=map_hex.id,
            name=data.name.strip(),
            kind=data.kind.strip().upper() if data.kind and data.kind.strip() else None,
            dm_description=data.dm_description,
            is_landmark=data.is_landmark,
        )
        self.db.add(poi)
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
        if "is_landmark" in changes and changes["is_landmark"] is not None:
            poi.is_landmark = changes["is_landmark"]
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
