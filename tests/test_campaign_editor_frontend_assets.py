from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "static" / "index.html"
JS = ROOT / "static" / "js" / "app.js"


def test_editor_can_persist_current_map_into_dm_campaign_context():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="campaign-save-panel"' in html
    assert 'id="persist-map-btn"' in html
    assert 'editorCampaignId' in js
    assert '/dm-maps/from-editor?user_id=${editorUserId}' in js
    assert 'Retour dashboard MJ' in js


def test_editor_can_load_existing_version_and_persist_next_version():
    js = JS.read_text(encoding="utf-8")
    assert 'editorParentVersionId' in js
    assert '/dm-map-versions/${editorParentVersionId}/load-editor?user_id=${editorUserId}' in js
    assert '/dm-maps/${editorMapId}/versions/from-editor?user_id=${editorUserId}' in js
    assert 'Créer la nouvelle version' in js
