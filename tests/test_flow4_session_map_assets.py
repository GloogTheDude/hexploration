from pathlib import Path


def test_dm_session_map_has_direct_move_controls_and_history():
    html = Path("static/dm_expedition.html").read_text()
    js = Path("static/js/dm_expedition.js").read_text()
    assert 'id="undo-move"' in html
    assert 'id="redo-move"' in html
    assert 'id="show-hidden-pois"' in html
    assert "drawMoveArrows" in js
    assert "/move/undo" in js
    assert "/ping`" in js


def test_player_map_renders_known_areas_and_strong_seen_tint():
    js = Path("static/js/player.js").read_text()
    assert "state.areas" in js
    assert 'rgba(2, 7, 9, .58)' in js
    assert 'visibility_state === "VISIBLE"' in js
