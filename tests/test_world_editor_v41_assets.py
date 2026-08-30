from pathlib import Path


def test_v41_world_editor_has_task_oriented_controls():
    html = Path("static/world.html").read_text(encoding="utf-8")
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    assert 'id="world-save"' in html
    assert 'id="world-time"' in html
    assert 'id="world-linear-edit-form"' in html
    assert 'id="world-area-edit-form"' in html
    assert 'id="world-poi-event-list"' in html
    assert 'id="world-edge-event-list"' in html
    assert 'data-tool="bridge"' not in html
    assert '<option>BRIDGE</option>' not in html
    assert "loadTargetTimeline" in js
    assert "data-event-edit" in js
    assert "data-event-delete" in js
    assert "e.key.toLowerCase()==='s'" in js


def test_v41_cache_bust():
    html = Path("static/world.html").read_text(encoding="utf-8")
    assert '/js/world.js?v=444' in html
    assert '/css/world.css?v=444' in html
