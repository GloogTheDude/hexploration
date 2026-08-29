from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_HTML = ROOT / "static" / "dashboard.html"
DASHBOARD_JS = ROOT / "static" / "js" / "dashboard.js"
DASHBOARD_CSS = ROOT / "static" / "css" / "dashboard.css"


def test_dashboard_exposes_gameplay_tabs_and_context_selectors():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    assert 'data-tab="map"' in html
    assert 'data-tab="wiki"' in html
    assert 'data-tab="recall"' in html
    assert 'id="characters"' in html
    assert 'id="expeditions"' in html
    assert 'id="map-frame"' in html


def test_active_expedition_wiki_uses_recalled_library_not_live_campaign_wiki():
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    active_branch = js.index('if (state.expedition.status === "ACTIVE")')
    returned_branch = js.index('ui.wikiTitle.textContent = "Wiki du hub"', active_branch)
    active_source = js[active_branch:returned_branch]
    assert '/recall`' in active_source
    assert '/wiki`' not in active_source


def test_recall_search_and_creation_use_selected_character():
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    assert 'recall/status?character_id=${state.character.id}' in js
    assert 'recall/search?character_id=${state.character.id}' in js
    assert 'character_id: state.character.id, page_id: entry.page.id' in js


def test_dashboard_url_keeps_campaign_character_and_expedition_context():
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    assert 'qs("campaign", id)' in js
    assert 'qs("character", id)' in js
    assert 'qs("expedition", id)' in js


def test_dashboard_has_responsive_gameplay_workspace_styles():
    css = DASHBOARD_CSS.read_text(encoding="utf-8")
    assert '.dashboard-shell' in css
    assert '.game-panel' in css
    assert '.knowledge-layout' in css
    assert '@media(max-width:760px)' in css


def test_dashboard_embeds_player_map_without_duplicate_topbar():
    dashboard_js = DASHBOARD_JS.read_text(encoding="utf-8")
    player_js = (ROOT / "static" / "js" / "player.js").read_text(encoding="utf-8")
    player_css = (ROOT / "static" / "css" / "player.css").read_text(encoding="utf-8")
    assert "&embedded=1" in dashboard_js
    assert 'get("embedded") === "1"' in player_js
    assert "body.embedded .topbar { display: none; }" in player_css


def test_player_character_creation_uses_modal_and_exposes_lifecycle_actions():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    css = DASHBOARD_CSS.read_text(encoding="utf-8")
    assert 'id="character-modal"' in html
    assert 'id="close-character-modal"' in html
    assert 'data-character-delete' in js
    assert '/retire?user_id=${state.user.id}' in js
    assert 'method:\'DELETE\'' in js
    assert '.modal-backdrop' in css


def test_player_invitations_refresh_without_full_page_reload():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    js = DASHBOARD_JS.read_text(encoding="utf-8")
    assert 'id="refresh-invitations"' in html
    assert 'setInterval' in js
    assert '/campaign-invitations`' in js
