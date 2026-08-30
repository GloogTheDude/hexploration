from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_world_editor_defers_initial_fit_until_canvas_has_real_size():
    js = (ROOT / "static/js/world.js").read_text(encoding="utf-8")
    html = (ROOT / "static/world.html").read_text(encoding="utf-8")

    assert "rect.width<80||rect.height<80" in js
    assert "initialFitPending=true" in js
    assert "requestAnimationFrame(()=>fitView())" in js
    assert "if(initialFitPending)fitView();else draw()" in js
    assert "/js/world.js?v=444" in html
