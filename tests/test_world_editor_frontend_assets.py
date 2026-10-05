from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "static" / "world.html"
JS = ROOT / "static" / "js" / "world.js"
MAP_HTML = ROOT / "static" / "index.html"
MAP_JS = ROOT / "static" / "js" / "app.js"
RENDERER = ROOT / "static" / "js" / "renderer.js"


def test_world_editor_is_a_dedicated_semantic_feature_page():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert "Éditeur du monde" in html
    assert 'id="world-map-canvas"' in html
    assert 'id="world-poi-form"' in html
    assert 'id="world-edge-form"' in html
    assert 'id="world-area-form"' in html
    assert "/dm-map-workbench?user_id=" in js
    assert "waypoints:selectedHexes.map" in js
    assert "Ctrl+Z" in html or "Ctrl+Z" in js


def test_map_editor_can_toggle_persisted_poi_overlay():
    html = MAP_HTML.read_text(encoding="utf-8")
    app = MAP_JS.read_text(encoding="utf-8")
    renderer = RENDERER.read_text(encoding="utf-8")
    assert 'id="toggle-poi-overlay"' in html
    assert "state.showPoiOverlay" in app
    assert "refreshPoiOverlay" in app
    assert "dm-map-workbench?map_version_id=" in app
    assert "drawPoiOverlay" in renderer
    assert "state.editorPois" in renderer


def test_world_editor_keeps_campaign_navigation_without_user_url_identity():
    html = HTML.read_text(encoding="utf-8")
    world = (ROOT / "static" / "js" / "world.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "world.css").read_text(encoding="utf-8")
    assert 'id="world-dm-link"' in html
    assert "Retour à la campagne et au dashboard MJ" in html
    assert "← Campagne MJ" in html
    assert "ui.dmLink.href=`/dm.html?campaign=${campaignId}`" in world
    assert "dashboard.campaign?.name" in world
    assert "ui.dmLink.href=`/dm.html?user=" not in world
    assert ".world-header-actions #world-dm-link{display:inline-block!important}" in css


def test_world_editor_uses_contextual_tool_and_inspector_layout():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "world.css").read_text(encoding="utf-8")
    assert 'data-tool="select"' in html
    assert 'data-tool="river"' in html
    assert 'id="world-object-browser"' in html
    assert 'id="world-poi-delete"' in html
    assert 'id="world-edge-delete"' in html
    assert 'id="world-area-delete"' in html
    assert "orderedPath(group)" in js
    assert "offsetPolyline" in js
    assert "ctx.fillStyle='#ffd84d'" in js
    assert "visible?'#111820':'#ffffff'" in js
    assert 'poiTemporalStates' in js
    assert "drawArea" in js
    assert ".world-tools" in css
