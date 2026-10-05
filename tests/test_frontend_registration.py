from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH_JS = (ROOT / "static/js/auth.js").read_text(encoding="utf-8")


def test_registration_is_available_from_the_existing_login_gate():
    assert 'id="auth-show-register"' in AUTH_JS
    assert 'id="auth-register-form"' in AUTH_JS
    assert 'id="auth-show-login"' in AUTH_JS


def test_registration_uses_the_real_public_user_contract():
    assert 'fetch("/api/users"' in AUTH_JS
    assert 'JSON.stringify({username: values.username, email: values.email, password: values.password})' in AUTH_JS
    assert 'fetch("/auth/login"' in AUTH_JS
    assert 'loginWithCredentials(values.username, password)' in AUTH_JS


def test_registration_does_not_send_privileges_or_persist_passwords():
    registration_request = AUTH_JS[AUTH_JS.index('fetch("/api/users"'):AUTH_JS.index('fetch("/api/users"') + 500]
    assert "campaign_role" not in registration_request
    assert "is_dm" not in registration_request
    assert "localStorage" not in AUTH_JS
    assert "sessionStorage" not in AUTH_JS
    assert "document.cookie" not in AUTH_JS


def test_registration_handles_conflict_validation_and_login_fallback():
    assert 'response.status === 409' in AUTH_JS
    assert 'response.status === 422' in AUTH_JS
    assert 'Compte créé. Connecte-toi pour continuer.' in AUTH_JS
    assert 'registerForm.reset()' in AUTH_JS
