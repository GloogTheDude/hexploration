from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DM_JS = ROOT / 'static' / 'js' / 'dm.js'
ROUTES = ROOT / 'routes' / 'dm_dashboard_routes.py'


def test_dashboard_keeps_world_and_terrain_exports():
    js = DM_JS.read_text(encoding='utf-8')
    assert 'mode=world' in js
    assert 'mode=terrain' in js


def test_export_route_forwards_render_mode_and_quality():
    routes = ROUTES.read_text(encoding='utf-8')
    assert 'mode: str = Query(default="world")' in routes
    assert 'quality: str = Query(default="high")' in routes
    assert '.render(map_version_id, format, mode=mode, quality=quality)' in routes


def test_world_editor_export_has_world_layer_toggle_and_formats():
    html = (ROOT / 'static' / 'world.html').read_text(encoding='utf-8')
    js = (ROOT / 'static' / 'js' / 'world.js').read_text(encoding='utf-8')
    assert 'id="world-export-layer"' in html
    assert 'id="world-export-png"' in html
    assert 'id="world-export-jpeg"' in html
    assert 'id="world-export-pdf"' in html
    assert "ui.exportLayer?.checked?'world':'terrain'" in js
    assert 'quality=high' in js
