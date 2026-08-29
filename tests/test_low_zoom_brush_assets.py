from pathlib import Path


def test_low_zoom_brush_is_frame_budgeted_and_uses_segment_preview():
    app = Path("static/js/app.js").read_text()
    tools = Path("static/js/tools.js").read_text()
    renderer = Path("static/js/renderer.js").read_text()
    assert "pendingPaintEvent" in app
    assert "requestAnimationFrame" in app
    assert "processPaintMove" in app
    assert "cssZoom < 0.60" in tools
    assert "brushOffsetCache" in tools
    assert "drawBrushSegmentPreview" in tools
    assert "export function drawBrushSegmentPreview" in renderer
