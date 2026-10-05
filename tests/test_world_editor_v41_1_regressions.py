from pathlib import Path


def test_toolbar_handlers_are_installed_at_module_scope():
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    undo = js[js.index("async function undoWorld"):js.index("async function redoWorld")]
    assert "ui.save.addEventListener" not in undo
    assert "ui.worldTimeApply.addEventListener" not in undo
    assert "ui.save.addEventListener('click'" in js
    assert "ui.worldTimeApply.addEventListener('click'" in js


def test_world_event_timeline_has_loading_and_empty_states():
    js = Path("static/js/world.js").read_text(encoding="utf-8")
    assert "Chargement des événements" in js
    assert "Aucun WorldEvent pour cet objet" in js
    assert "Impossible de charger la timeline" in js
    assert ".sort((a,b)=>a.game_minute-b.game_minute||a.id-b.id)" in js


def test_v411_toolbar_and_cache_bust():
    html = Path("static/world.html").read_text(encoding="utf-8")
    css = Path("static/css/world.css").read_text(encoding="utf-8")
    assert 'class="toolbar-group toolbar-version"' in html
    assert 'class="inspector-world-time"' in html
    assert 'class="toolbar-group toolbar-history"' in html
    assert '/js/world.js?v=461' in html
    assert '/css/world.css?v=445' in html
    assert ".toolbar-group" in css
