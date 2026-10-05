from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_JS = (ROOT / "static/js/auth.js").read_text(encoding="utf-8")


def test_auth_bootstrap_uses_server_session_and_gates_application_startup():
    assert 'fetch("/auth/me"' in AUTH_JS
    assert "export const authReady" in AUTH_JS
    assert "await authReady" in (ROOT / "static/js/app.js").read_text(encoding="utf-8")
    assert "authReady.then(load)" in (ROOT / "static/js/dashboard.js").read_text(encoding="utf-8")


def test_login_and_logout_use_existing_contract():
    assert 'fetch("/auth/login"' in AUTH_JS
    assert 'username_or_email' in AUTH_JS
    assert 'fetch("/auth/logout"' in AUTH_JS
    assert 'autocomplete="current-password"' in AUTH_JS


def test_frontend_never_handles_session_token_or_persists_identity():
    forbidden = ("localStorage", "sessionStorage", "document.cookie", "session_token", "raw_token")
    assert not any(marker in AUTH_JS for marker in forbidden)
    assert "getCurrentUser" in (ROOT / "static/js/dashboard.js").read_text(encoding="utf-8")
    assert "getCurrentUser" in (ROOT / "static/js/dm.js").read_text(encoding="utf-8")


def test_only_401_expires_authentication():
    assert "response.status === 401" in AUTH_JS
    assert "response.status === 403" not in AUTH_JS
    assert "response.status === 404" not in AUTH_JS


def test_authenticated_pages_include_shared_login_styles():
    for filename in ("index.html", "dashboard.html", "dm.html", "dm_expedition.html", "player.html", "world.html", "timeline.html"):
        html = (ROOT / "static" / filename).read_text(encoding="utf-8")
        assert "/css/auth.css" in html


def test_caller_identity_is_not_taken_from_dashboard_or_dm_user_selector():
    dashboard = (ROOT / "static/js/dashboard.js").read_text(encoding="utf-8")
    dm = (ROOT / "static/js/dm.js").read_text(encoding="utf-8")
    assert "getCurrentUser()" in dashboard
    assert "getCurrentUser()" in dm
    assert "Number(ui.userId.value)" not in dashboard
    assert "Number(ui.userId.value)" not in dm
