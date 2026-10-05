from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_primary_frontends_render_api_error_details():
    scripts = [
        ROOT / "static/js/app.js",
        ROOT / "static/js/dashboard.js",
        ROOT / "static/js/dm.js",
        ROOT / "static/js/player.js",
        ROOT / "static/js/world.js",
    ]

    for script in scripts:
        source = script.read_text(encoding="utf-8")
        assert "response.ok" in source
        assert "body.detail" in source
        assert "throw new Error" in source


def test_primary_frontends_expose_loading_and_save_feedback():
    app = (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "static/js/dashboard.js").read_text(encoding="utf-8")
    dm = (ROOT / "static/js/dm.js").read_text(encoding="utf-8")
    world = (ROOT / "static/js/world.js").read_text(encoding="utf-8")

    assert "Chargement" in app
    assert "Sauvegarde" in app
    assert "Chargement" in dashboard
    assert "Enregistrement" in dashboard
    assert "Chargement" in dm
    assert "Enregistrement" in dm
    assert "Chargement" in world
    assert "Sauvegardé" in world


def test_main_pages_keep_cross_area_navigation():
    expected_links = {
        "dashboard.html": ("dm.html", "player.html", "timeline.html"),
        "dm.html": ("dashboard.html", "player.html", "timeline.html", "world.html"),
        "player.html": ("dashboard.html", "dm.html", "timeline.html"),
        "world.html": ("dm.html", 'href="/"'),
    }
    for filename, links in expected_links.items():
        html = (ROOT / "static" / filename).read_text(encoding="utf-8")
        for link in links:
            assert link in html
