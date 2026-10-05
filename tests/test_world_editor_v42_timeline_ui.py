from pathlib import Path


def test_world_editor_uses_readable_campaign_calendar_and_dynamic_poi_payload():
    html = Path("static/world.html").read_text(encoding="utf-8")
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    assert 'id="world-time-year"' in html
    assert 'id="world-time-month"' in html
    assert 'id="world-time-day"' in html
    assert 'id="world-poi-event-year"' in html
    assert 'POI_VISIBILITY_CHANGED' in html
    assert 'id="world-poi-event-visibility"' in html
    assert 'Avancé · Payload JSON' in html
    assert 'GAME_MINUTES_PER_YEAR=518400' in js
    assert 'visible_at_distance' in js
    assert 'loadPoiTemporalStates' in js
    assert 'formatGameDate' in js


def test_world_editor_v42_cache_bust():
    html = Path("static/world.html").read_text(encoding="utf-8")
    assert '/js/world.js?v=460' in html
    assert '/css/world.css?v=444' in html
