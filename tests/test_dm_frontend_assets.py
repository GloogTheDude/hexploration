from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "static" / "dm.html"
JS = ROOT / "static" / "js" / "dm.js"
CSS = ROOT / "static" / "css" / "dm.css"


def test_dm_dashboard_assets_expose_campaign_control_tabs():
    html = HTML.read_text(encoding="utf-8")
    for tab in ["overview", "expeditions", "world", "maps", "characters", "timeline"]:
        assert f'data-tab="{tab}"' in html
    assert 'id="world-minute"' in html
    assert 'id="timeline-frame"' in html
    assert 'id="expedition-planner-form"' in html
    assert 'id="plan-characters"' in html


def test_dm_dashboard_uses_dm_only_backend_and_world_state():
    js = JS.read_text(encoding="utf-8")
    assert "/dm-campaigns" in js
    assert "/dm-dashboard?user_id=" in js
    assert "/world-state?game_minute=" in js
    assert "/api/campaigns/${state.campaignId}/dm-expeditions/${state.expeditionId}/${action}?user_id=${state.userId}" in js
    assert "expeditionAction('start')" in js
    assert "expeditionAction('return')" in js


def test_dm_dashboard_timeline_preserves_campaign_context():
    js = JS.read_text(encoding="utf-8")
    assert "timeline.html?campaign_id=" in js
    assert "&embedded=1" in js


def test_dm_dashboard_has_responsive_layout():
    css = CSS.read_text(encoding="utf-8")
    assert ".shell" in css
    assert ".overview-grid" in css
    assert "@media(max-width:760px)" in css


def test_dm_dashboard_can_create_campaign_without_swagger():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="campaign-create-form"' in html
    assert 'id="toggle-campaign-create"' in html
    assert "creator_user_id: state.userId" in js
    assert "api('/api/campaigns'" in js


def test_dm_dashboard_exposes_visual_map_feature_workbench():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    for marker in ['id="dm-map-canvas"', 'id="poi-form"', 'id="edge-form"', 'id="poi-event-form"', 'id="edge-event-form"']:
        assert marker in html
    assert "/dm-map-workbench?user_id=" in js
    assert "/dm-map-versions/${state.mapWorkbench.map_version_id}/pois" in js
    assert "/dm-map-versions/${state.mapWorkbench.map_version_id}/edges" in js
    assert "/world-events?user_id=" in js


def test_dm_dashboard_bootstraps_members_characters_and_campaign_editor():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="member-form"' in html
    assert 'id="character-form"' not in html
    assert 'Inviter un joueur' in html
    assert 'id="map-editor-open"' in html
    assert "/invitations?user_id=" in js
    assert "/dm-characters?user_id=" not in js
    assert "/?user=${state.userId}&campaign=${d.campaign.id}" in js


def test_dm_map_versions_link_to_version_editor_without_internal_id_hunting():
    js = JS.read_text(encoding="utf-8")
    assert 'Éditer → nouvelle version' in js
    assert '&map=${m.id}&version=${v.id}' in js
    assert 'identité POI #${p.feature_id}' in js


def test_dm_dashboard_shows_sent_invitation_status_and_reinvite_action():
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert 'id="sent-invitations"' in html
    assert 'Invitations envoyées' in html
    assert '/invitations?user_id=${state.userId}' in js
    assert 'invite-${i.status}' in js
    assert 'data-reinvite' in js


def test_dm_dashboard_can_update_and_delete_selected_campaign():
    js = JS.read_text(encoding="utf-8")
    assert 'id="edit-campaign"' in js
    assert 'id="delete-campaign"' in js
    assert '/dm-settings?user_id=${state.userId}' in js
    assert "method: 'PATCH'" in js
    assert "method: 'DELETE'" in js
    assert 'Tape exactement le nom de la campagne' in js
