from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "static/dm_expedition.html").read_text()
DM_JS = (ROOT / "static/js/dm_expedition.js").read_text()
PLAYER_JS = (ROOT / "static/js/player.js").read_text()

def test_dm_ping_controls_are_visible_on_dm_session_map():
    assert 'id="dm-ping-color" type="color"' in HTML
    assert 'id="dm-ping"' in HTML
    assert '◆ Ping MJ' in HTML

def test_dm_ping_is_independent_and_has_distinct_symbol():
    assert "/dm-ping?user_id=${userId}" in DM_JS
    assert "strokeRect" in DM_JS
    assert "state.dm_ping_q" in PLAYER_JS
    assert "state.dm_ping_color" in PLAYER_JS


def test_player_map_payload_excludes_dm_ping_from_player_view():
    dto = (ROOT / "dto/player_map_dto.py").read_text()
    routes = (ROOT / "routes/player_map_routes.py").read_text()
    assert "dm_ping_q: int | None = None" in dto
    assert "dm_ping_created_at: datetime | None = None" in dto
    assert "dm_ping_q=None" in routes
    assert "dm_ping_user_id=None" in routes
    assert "dm_ping_color=None" in routes
