from pathlib import Path


def test_brush_hot_path_is_incremental_and_sync_is_deferred():
    tools = Path("static/js/tools.js").read_text()
    renderer = Path("static/js/renderer.js").read_text()
    app = Path("static/js/app.js").read_text()

    assert "drawPaintPreview" in tools
    assert "requestMapDraw(canvas, state.map)" not in tools
    assert "state.isPainting" in tools
    assert "MAX_PENDING_CENTERS" in tools
    assert "export function drawPaintPreview" in renderer
    assert "flushPendingPaint().catch" in app
    assert "?v=303" in app
