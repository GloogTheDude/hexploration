from pathlib import Path


def test_v43_calendar_and_created_event_ui():
    html = Path("static/world.html").read_text(encoding="utf-8")
    css = Path("static/css/world.css").read_text(encoding="utf-8")
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    assert 'value="POI_CREATED"' in html
    assert 'POI_CREATED — Apparition / création' in html
    assert '/js/world.js?v=444' in html
    assert '/css/world.css?v=444' in html
    assert '.toolbar-time .compact-date{width:390px!important' in css
    assert "EVENT_LABELS={POI_CREATED:'Création / apparition'" in js
    assert "temporal?.exists===false&&state!=='DESTROYED'" in js
