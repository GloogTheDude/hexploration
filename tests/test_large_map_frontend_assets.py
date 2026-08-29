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
