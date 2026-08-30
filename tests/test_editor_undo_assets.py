from pathlib import Path


def test_map_editor_has_stroke_undo_redo_and_exact_server_sync():
    app = Path("static/js/app.js").read_text()
    tools = Path("static/js/tools.js").read_text()
    routes = Path("routes/map_routes.py").read_text()
    assert "beginPaintStroke" in app
    assert "endPaintStroke" in app
    assert "undoPaint" in app and "redoPaint" in app
    assert "event.shiftKey ? await redoPaint() : await undoPaint()" in app
    assert "activeStrokeBefore" in tools
    assert "paintHexesExactApi" in tools
    assert '/api/hex/paintExact' in routes


def test_dm_workbench_has_poi_undo_linear_waypoints_and_area_tools():
    js = Path("static/js/dm.js").read_text()
    html = Path("static/dm.html").read_text()
    assert "undoPoi" in js and "redoPoi" in js
    assert "linear-features" in js
    assert "waypoints:selected.map" in js
    assert "RIVER" in html
    assert 'id="area-form"' in html
    assert "area-features" in js
    assert "edgeGroups" in js
