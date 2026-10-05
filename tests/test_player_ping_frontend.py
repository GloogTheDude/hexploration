from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static" / "player.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "js" / "player.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "css" / "player.css").read_text(encoding="utf-8")


def test_ping_color_picker_is_in_persistent_map_toolbar():
    assert 'id="ping-color-control"' in HTML
    assert 'id="ping-color" type="color"' in HTML
    assert 'body.shared-display .ping-color-control' in CSS


def test_single_click_ping_has_immediate_feedback_and_server_persistence():
    assert 'if (state.expedition_status === "ACTIVE" && activePingUserId) pingHex(selected);' in JS
    assert 'Immediate local feedback: a single click visibly pings before the round trip.' in JS
    assert 'method: "PUT"' in JS
    assert '/ping?user_id=${activePingUserId}' in JS


def test_ping_controls_are_hidden_only_when_ping_is_unavailable():
    assert 'const pingUnavailable = state.expedition_status !== "ACTIVE" || !activePingUserId;' in JS
    assert 'pingColorControl?.classList.toggle("hidden", pingUnavailable);' in JS


def test_shared_display_can_choose_ping_player_and_toolbar_is_overlay():
    html = (ROOT / "static/player.html").read_text()
    css = (ROOT / "static/css/player.css").read_text()
    assert 'id="ping-user"' in html
    assert 'id="ping-toolbar"' in html
    assert 'loadSharedPingUsers' in JS
    assert 'position:absolute' in css or 'position: absolute' in css


def test_dashboard_exposes_ping_color_picker_in_primary_player_ui():
    dashboard_html = (ROOT / "static" / "dashboard.html").read_text()
    dashboard_js = (ROOT / "static" / "js" / "dashboard.js").read_text()
    assert 'id="dashboard-ping-color" type="color"' in dashboard_html
    assert 'Couleur du ping' in dashboard_html
    assert '/ping-color' in dashboard_js
    assert 'saveDashboardPingColor' in dashboard_js
