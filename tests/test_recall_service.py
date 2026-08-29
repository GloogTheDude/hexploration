from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from db.models import (
    Campaign,
    Character,
    CharacterStatus,
    ExpeditionCharacter,
    ExpeditionStatus,
    User,
    WikiPage,
    WikiRevision,
)
from services.errors import ConflictError, ForbiddenOperationError, NotFoundError
from services.recall_service import DEFAULT_RECALL_LIMIT_PER_CHARACTER, RecallService
from tests.factories import make_active_expedition, make_map_with_two_hexes


def _wiki_page(
    db: Session,
    campaign: Campaign,
    *,
    slug: str,
    title: str,
    minute: int,
    content: str,
) -> WikiPage:
    page = WikiPage(
        campaign_id=campaign.id,
        slug=slug,
        title=title,
        category="POI",
    )
    db.add(page)
    db.flush()
    db.add(
        WikiRevision(
            page_id=page.id,
            revision=1,
            effective_from_game_minute=minute,
            source_report_id=None,
            content=content,
        )
    )
    db.commit()
    return page


def _add_revision(db: Session, page: WikiPage, minute: int, content: str) -> WikiRevision:
    current = (
        db.query(WikiRevision)
        .filter(WikiRevision.page_id == page.id)
        .order_by(WikiRevision.revision.desc())
        .first()
    )
    revision = WikiRevision(
        page_id=page.id,
        revision=(current.revision if current else 0) + 1,
        effective_from_game_minute=minute,
        source_report_id=None,
        content=content,
    )
    db.add(revision)
    db.commit()
    return revision


def _second_character(db: Session, campaign: Campaign, expedition_id: int, minute: int) -> Character:
    user = User(
        username=f"recall_second_{expedition_id}",
        email=f"recall_second_{expedition_id}@example.com",
        password_hash="unused",
    )
    db.add(user)
    db.flush()
    character = Character(
        campaign_id=campaign.id,
        owner_user_id=user.id,
        name="Second Recall Tester",
        race="Human",
        character_class="Wizard",
        level=1,
        description=None,
        status=CharacterStatus.ACTIVE,
        current_game_minute=minute,
    )
    db.add(character)
    db.flush()
    db.add(
        ExpeditionCharacter(
            expedition_id=expedition_id,
            character_id=character.id,
            joined_game_minute=minute,
            left_game_minute=None,
        )
    )
    db.commit()
    return character


def test_recall_uses_wiki_state_at_expedition_departure(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    page = _wiki_page(
        db,
        campaign,
        slug="old-tower",
        title="Old Tower",
        minute=100,
        content="Tower intact",
    )
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None

    _add_revision(db, page, minute=250, content="Tower destroyed")
    expedition.current_game_minute = 300
    character.current_game_minute = 300
    db.commit()

    recalled = RecallService(db).recall_page(expedition.id, character.id, page.id)

    assert recalled.recall.knowledge_cutoff_game_minute == 200
    assert recalled.recall.recalled_at_game_minute == 300
    assert recalled.revision.content == "Tower intact"
    assert recalled.revision.effective_from_game_minute == 100


def test_page_unknown_at_departure_cannot_be_recalled(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None
    page = _wiki_page(
        db,
        campaign,
        slug="new-ruin",
        title="New Ruin",
        minute=250,
        content="Discovered after departure",
    )

    with pytest.raises(NotFoundError, match="not known at expedition departure"):
        RecallService(db).recall_page(expedition.id, character.id, page.id)


def test_recalled_page_stays_pinned_to_departure_knowledge(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    page = _wiki_page(
        db,
        campaign,
        slug="bridge",
        title="Northern Bridge",
        minute=100,
        content="Bridge open",
    )
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None

    service = RecallService(db)
    first = service.recall_page(expedition.id, character.id, page.id)
    _add_revision(db, page, minute=400, content="Bridge destroyed")
    expedition.current_game_minute = 500
    db.commit()

    unlocked = service.list_unlocked(expedition.id)
    assert len(unlocked) == 1
    assert unlocked[0].recall.id == first.recall.id
    assert unlocked[0].revision.content == "Bridge open"


def test_character_has_limited_unique_recalls(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None
    service = RecallService(db)

    pages = [
        _wiki_page(
            db,
            campaign,
            slug=f"page-{index}",
            title=f"Page {index}",
            minute=100,
            content=f"Knowledge {index}",
        )
        for index in range(DEFAULT_RECALL_LIMIT_PER_CHARACTER + 1)
    ]

    for page in pages[:DEFAULT_RECALL_LIMIT_PER_CHARACTER]:
        service.recall_page(expedition.id, character.id, page.id)

    status = service.status(expedition.id, character.id)
    assert status.used == DEFAULT_RECALL_LIMIT_PER_CHARACTER
    assert status.remaining == 0

    with pytest.raises(ConflictError, match="no knowledge recalls remaining"):
        service.recall_page(expedition.id, character.id, pages[-1].id)


def test_recalled_page_is_shared_with_expedition_without_spending_second_slot(
    db: Session,
    campaign: Campaign,
):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    page = _wiki_page(
        db,
        campaign,
        slug="shared-place",
        title="Shared Place",
        minute=100,
        content="Known before departure",
    )
    expedition, first_character = make_active_expedition(
        db,
        campaign,
        version,
        game_minute=200,
    )
    assert first_character is not None
    second_character = _second_character(db, campaign, expedition.id, 200)

    service = RecallService(db)
    first = service.recall_page(expedition.id, first_character.id, page.id)
    shared = service.recall_page(expedition.id, second_character.id, page.id)

    assert shared.recall.id == first.recall.id
    assert service.status(expedition.id, second_character.id).used == 0
    assert len(service.list_unlocked(expedition.id)) == 1


def test_recall_search_only_exposes_pages_known_at_departure(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    old_page = _wiki_page(
        db,
        campaign,
        slug="old-forest",
        title="Old Forest",
        minute=100,
        content="Known",
    )
    _wiki_page(
        db,
        campaign,
        slug="new-forest",
        title="New Forest Shrine",
        minute=250,
        content="Future hub intel",
    )
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None

    results = RecallService(db).search_available(
        expedition.id,
        character.id,
        "forest",
    )

    assert [page.id for page, _ in results] == [old_page.id]


def test_recall_requires_active_expedition_and_active_participant(db: Session, campaign: Campaign):
    _, version, _, _ = make_map_with_two_hexes(db, campaign)
    page = _wiki_page(
        db,
        campaign,
        slug="road",
        title="Old Road",
        minute=100,
        content="Road known",
    )
    expedition, character = make_active_expedition(db, campaign, version, game_minute=200)
    assert character is not None
    service = RecallService(db)

    participant = service.expeditions.get_participant(expedition.id, character.id)
    assert participant is not None
    participant.left_game_minute = 210
    db.commit()
    with pytest.raises(ForbiddenOperationError, match="no longer active"):
        service.recall_page(expedition.id, character.id, page.id)

    participant.left_game_minute = None
    expedition.status = ExpeditionStatus.RETURNED
    expedition.return_game_minute = 220
    db.commit()
    with pytest.raises(ConflictError, match="active expedition"):
        service.recall_page(expedition.id, character.id, page.id)
