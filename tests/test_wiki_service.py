from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db.models import Campaign, ExpeditionStatus
from dto.poi_dto import POICreate
from dto.wiki_dto import ExpeditionReportCreate
from dto.world_event_dto import WorldEventCreate
from services.errors import ConflictError, NotFoundError
from services.knowledge_service import KnowledgeService
from services.poi_service import POIService
from services.wiki_service import WikiService
from services.world_event_service import WorldEventService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _returned_expedition_with_known_poi(
    db: Session,
    campaign: Campaign,
    *,
    discover_minute: int = 100,
    return_minute: int = 300,
):
    _, version, source, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=discover_minute,
    )
    poi = POIService(db).create(
        POICreate(
            hex_id=source.id,
            name="Old Watchtower",
            kind="RUIN",
            is_landmark=True,
        )
    )
    KnowledgeService(db).discover_poi(expedition.id, poi.id)

    expedition.current_game_minute = return_minute
    expedition.return_game_minute = return_minute
    expedition.status = ExpeditionStatus.RETURNED
    if character is not None:
        character.current_game_minute = return_minute
    db.commit()
    return expedition, character, poi


def test_report_requires_returned_expedition(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=100)

    with pytest.raises(ConflictError, match="returned expedition"):
        WikiService(db).publish_expedition_report(
            expedition.id,
            ExpeditionReportCreate(title="Too soon", content="Not back yet"),
        )


def test_report_publishes_known_poi_at_return_minute(
    db: Session,
    campaign: Campaign,
):
    expedition, _, poi = _returned_expedition_with_known_poi(db, campaign)

    report, pages = WikiService(db).publish_expedition_report(
        expedition.id,
        ExpeditionReportCreate(title="First expedition", content="We returned."),
    )

    assert report.published_game_minute == 300
    assert len(pages) == 1
    page, revision = pages[0]
    assert page.slug == f"poi-{poi.id}"
    assert revision.effective_from_game_minute == 300
    assert revision.source_report_id == report.id
    assert "Old Watchtower" in revision.content

    with pytest.raises(NotFoundError, match="not available"):
        WikiService(db).get_page_state(page.id, as_of_game_minute=299)

    _, visible = WikiService(db).get_page_state(page.id, as_of_game_minute=300)
    assert visible.id == revision.id


def test_late_world_change_is_not_published_without_reobservation(
    db: Session,
    campaign: Campaign,
):
    expedition, _, poi = _returned_expedition_with_known_poi(db, campaign)
    WorldEventService(db).create(
        campaign.id,
        WorldEventCreate(
            game_minute=200,
            event_type="POI_DESTROYED",
            target_type="POI",
            target_id=poi.id,
            payload={},
        ),
    )

    _, pages = WikiService(db).publish_expedition_report(
        expedition.id,
        ExpeditionReportCreate(title="Old intel", content="Our observations."),
    )
    _, revision = pages[0]

    # The expedition only observed the POI at minute 100, before destruction.
    assert "État observé: ACTIVE" in revision.content
    assert "Existe: oui" in revision.content


def test_second_return_creates_temporal_wiki_revision(
    db: Session,
    campaign: Campaign,
):
    first_expedition, _, poi = _returned_expedition_with_known_poi(
        db,
        campaign,
        discover_minute=100,
        return_minute=300,
    )
    service = WikiService(db)
    _, first_pages = service.publish_expedition_report(
        first_expedition.id,
        ExpeditionReportCreate(title="Report one", content="Tower intact."),
    )
    page = first_pages[0][0]

    # A second expedition uses the same map version and observes the destruction.
    first_map_version = first_expedition.current_map_version_id
    from db.models import MapVersion
    version = db.get(MapVersion, first_map_version)
    assert version is not None

    WorldEventService(db).create(
        campaign.id,
        WorldEventCreate(
            game_minute=400,
            event_type="POI_DESTROYED",
            target_type="POI",
            target_id=poi.id,
            payload={},
        ),
    )
    second, second_character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=450,
    )
    KnowledgeService(db).discover_poi(second.id, poi.id)
    second.current_game_minute = 500
    second.return_game_minute = 500
    second.status = ExpeditionStatus.RETURNED
    if second_character is not None:
        second_character.current_game_minute = 500
    db.commit()

    _, second_pages = service.publish_expedition_report(
        second.id,
        ExpeditionReportCreate(title="Report two", content="Tower destroyed."),
    )
    assert second_pages[0][0].id == page.id
    assert second_pages[0][1].revision == 2

    _, old_revision = service.get_page_state(page.id, as_of_game_minute=450)
    _, new_revision = service.get_page_state(page.id, as_of_game_minute=500)
    assert old_revision.revision == 1
    assert "ACTIVE" in old_revision.content
    assert new_revision.revision == 2
    assert "DESTROYED" in new_revision.content


def test_report_is_unique_per_expedition(db: Session, campaign: Campaign):
    expedition, _, _ = _returned_expedition_with_known_poi(db, campaign)
    service = WikiService(db)
    data = ExpeditionReportCreate(title="Report", content="Done")
    service.publish_expedition_report(expedition.id, data)

    with pytest.raises(ConflictError, match="already has"):
        service.publish_expedition_report(expedition.id, data)
