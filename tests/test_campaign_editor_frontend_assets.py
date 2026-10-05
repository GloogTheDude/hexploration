from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "static" / "index.html"
JS = ROOT / "static" / "js" / "app.js"
CSS = ROOT / "static" / "css" / "style.css"


def test_editor_can_persist_current_map_into_dm_campaign_context():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="campaign-save-panel"' in html
    assert 'id="persist-map-btn"' in html
    assert 'editorCampaignId' in js
    assert '/api/campaigns/${editorCampaignId}/dm-maps' in js
    assert 'persisted created' in js or 'peintures sont enregistrées' in js
    assert 'editorDmLink.href' in js


def test_editor_can_load_existing_version_from_editor_screen():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="persisted-version-select"' in html
    assert 'id="load-persisted-btn"' in html
    assert '/api/campaigns/${editorCampaignId}/dm-dashboard' in js
    assert 'fetchPersistentMap' in js


def test_editor_can_choose_update_or_new_version():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'name="save-mode" value="update"' in html
    assert 'name="save-mode" value="new-version"' in html
    assert 'method: "PATCH"' in js
    assert '/versions/${editorVersionId}' in js
    assert '/dm-maps/${editorMapId}/versions' in js
    assert 'editorPath("paint")' in (ROOT / 'static/js/api.js').read_text(encoding='utf-8')


def test_editor_has_pan_zoom_and_fit_navigation():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    for element_id in ("zoom-in-btn", "zoom-out-btn", "fit-map-btn"):
        assert f'id="{element_id}"' in html
    assert 'canvas.addEventListener("wheel"' in js
    assert 'state.isPanning' in js
    assert '.editor-layout' in css
    assert 'background-color: blue' not in css
