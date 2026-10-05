from pathlib import Path


def test_editor_allows_large_maps_and_batches_painting():
    html = Path("static/index.html").read_text(encoding="utf-8")
    tools = Path("static/js/tools.js").read_text(encoding="utf-8")
    renderer = Path("static/js/renderer.js").read_text(encoding="utf-8")

    assert 'max="10000"' in html
    assert "10 000×10 000" in html
    assert "pendingCenters" in tools
    assert "flushPendingPaint" in tools
    assert "requestAnimationFrame" in renderer
    assert "drawRectangularVisible" in renderer
    assert "map.sparse" in renderer


def test_terrain_paint_uses_delta_responses_without_full_workbench_reload():
    tools = Path("static/js/tools.js").read_text(encoding="utf-8")
    api = Path("static/js/api.js").read_text(encoding="utf-8")
    routes = Path("routes/dm_dashboard_routes.py").read_text(encoding="utf-8")
    assert "applyPaintDelta" in tools
    assert "applyPersistentWorkbench(data)" not in tools
    assert "fetchPersistentMap" in tools
    assert "DMMapHexPaintDelta" in routes
    assert 'editorPath("exact")' in api


def test_workbench_coordinate_lookups_are_indexed():
    world = Path("static/js/world.js").read_text(encoding="utf-8")
    dm = Path("static/js/dm.js").read_text(encoding="utf-8")
    assert "rebuildHexIndex" in world
    assert "hexByCoord.get" in world
    assert "state.mapWorkbench?.hexes?.find(h=>h.q===q&&h.r===r)" not in dm
    assert "workbenchHexByCoord" in dm


def test_interactive_renderers_share_viewport_culling_helper():
    viewport = Path("static/js/viewport.js").read_text(encoding="utf-8")
    renderer = Path("static/js/renderer.js").read_text(encoding="utf-8")
    world = Path("static/js/world.js").read_text(encoding="utf-8")
    assert "computeVisibleHexBounds" in viewport
    assert 'from "./viewport.js?v=1"' in renderer
    assert "./viewport.js?v=1" in world
    assert "rowBounds" in renderer
    assert "rowBounds" in world
    assert "map.hexes?.[`${q},${r}`]" in renderer


def test_editor_defaults_to_one_to_one_and_space_pan():
    app = Path("static/js/app.js").read_text(encoding="utf-8")
    state = Path("static/js/state.js").read_text(encoding="utf-8")
    css = Path("static/css/style.css").read_text(encoding="utf-8")
    html = Path("static/index.html").read_text(encoding="utf-8")

    assert "function resetViewOneToOne()" in app
    assert "scale: canvasPixelRatio()" in app
    assert 'event.code !== "Space"' in app
    assert "state.spacePanning && event.button === 0" in app
    assert "isTypingTarget" in app
    assert "spacePanning: false" in state
    assert "canvas.space-pan" in css
    assert "Espace + glisser" in html
