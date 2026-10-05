from pathlib import Path


def test_dm_expedition_planner_uses_map_version_hub_and_no_transport_picker():
    html = Path("static/dm.html").read_text(encoding="utf-8")
    js = Path("static/js/dm.js").read_text(encoding="utf-8")
    assert 'id="plan-map"' in html
    assert 'id="plan-map-version"' in html
    assert 'id="plan-hub-summary"' in html
    assert 'id="plan-transport"' not in html
    assert 'id="plan-q"' not in html
    assert 'id="plan-r"' not in html
    assert 'gameMinuteFromDateInputs(\'plan-time\')' in js
    assert 'transport_key:' not in js[js.index("async function createExpeditionPlan"):js.index("function renderExpeditions")]


def test_world_editor_poi_form_can_mark_hub():
    html = Path("static/world.html").read_text(encoding="utf-8")
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    assert 'id="world-poi-hub"' in html
    assert 'is_hub:ui.poiHub.checked' in js


def test_shared_game_calendar_is_used_in_main_frontends():
    helper = Path("static/js/game_time.js").read_text(encoding="utf-8")
    assert "GAME_MONTHS_PER_YEAR = 12" in helper
    assert "GAME_DAYS_PER_MONTH = 30" in helper
    for filename in ["app.js", "dm.js", "dashboard.js", "player.js", "timeline.js"]:
        text = Path("static/js", filename).read_text(encoding="utf-8")
        assert "game_time.js" in text
