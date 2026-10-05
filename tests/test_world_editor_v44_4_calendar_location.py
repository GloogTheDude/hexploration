from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_world_calendar_is_in_inspector_not_header():
    html = (ROOT / "static/world.html").read_text(encoding="utf-8")
    header = html.split("</header>", 1)[0]
    inspector = html.split('<aside class="world-inspector">', 1)[1]
    assert 'id="world-time-year"' not in header
    assert 'id="world-time-year"' in inspector
    assert 'class="inspector-world-time"' in html
    assert 'Afficher cette date' in html

def test_v44_4_assets_are_cache_busted():
    html = (ROOT / "static/world.html").read_text(encoding="utf-8")
    assert '/css/world.css?v=444' in html
    assert '/js/world.js?v=460' in html
