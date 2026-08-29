from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYER_JS = ROOT / "static" / "js" / "player.js"
PLAYER_CSS = ROOT / "static" / "css" / "player.css"


def test_player_canvas_resyncs_backing_bitmap_before_each_draw():
    source = PLAYER_JS.read_text(encoding="utf-8")
    assert "function syncCanvasResolution()" in source
    assert "const {width, height} = syncCanvasResolution();" in source
    assert "canvas.width = targetWidth;" in source
    assert "canvas.height = targetHeight;" in source
    assert "ctx.setTransform(ratio, 0, 0, ratio, 0, 0);" in source


def test_player_canvas_tracks_layout_changes_and_has_dark_fallback():
    js = PLAYER_JS.read_text(encoding="utf-8")
    css = PLAYER_CSS.read_text(encoding="utf-8")
    assert "new ResizeObserver(() => draw())" in js
    assert "requestAnimationFrame(() => resizeCanvas())" in js
    assert "background: #0b0e12" in css
