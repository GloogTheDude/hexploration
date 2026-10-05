from pathlib import Path


def test_world_editor_v443_layout_contract():
    css = Path("static/css/world.css").read_text(encoding="utf-8")
    html = Path("static/world.html").read_text(encoding="utf-8")
    assert "v44.3 — final World Editor chrome cleanup" in css
    assert "overflow-x:clip!important" in css
    assert "grid-template-columns:repeat(5,minmax(0,1fr))!important" in css
    assert "v44.4 — move world calendar into the inspector" in css
    assert "/css/world.css?v=445" in html
    assert "/js/world.js?v=461" in html
