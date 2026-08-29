from dto.dm_dashboard_dto import DMCharacterSummary
from db.models import CharacterStatus


def test_dm_character_summary_exposes_compact_sheet_stats_and_readonly_data():
    item = DMCharacterSummary(
        id=18, owner_user_id=2, name="tituan", race="Dinosaure",
        character_class="Débile", level=1, status=CharacterStatus.ACTIVE,
        current_game_minute=0, current_hp=8, max_hp=12, armor_class=15,
        passive_perception=13, sheet_version=2, sheet_data={"strength": 14},
    )
    assert (item.current_hp, item.max_hp, item.armor_class, item.passive_perception) == (8, 12, 15, 13)
    assert item.sheet_data == {"strength": 14}
