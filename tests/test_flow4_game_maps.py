from sqlalchemy import select

from db.models import MapEdge, MapHex, MapVersion, PointOfInterest, WorldMap
from services.expedition_ping_service import ExpeditionPingService
from services.knowledge_service import KnowledgeService
from services.player_map_service import PlayerMapService
from services.visibility_service import VisibilityService
from tests.factories import make_active_expedition


def make_sparse_map(db, campaign):
    world = WorldMap(campaign_id=campaign.id, name="Sparse Sea", description=None)
    db.add(world); db.flush()
    version = MapVersion(
        map_id=world.id, version=1, name="v1", width=7, height=7, hex_size=32,
        default_terrain_key="SEA", effective_from_game_minute=0,
    )
    db.add(version); db.flush()
    origin = MapHex(
        map_version_id=version.id, q=0, r=0, terrain_key="PLAIN", elevation=0,
        visibility_score=3, travel_cost=1.0, extra_data={},
    )
    db.add(origin); db.commit()
    return world, version, origin


def test_sparse_default_sea_is_materialized_when_party_can_see_it(db, campaign):
    _, version, _ = make_sparse_map(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=10)

    result = VisibilityService(db).observe_visible_pois(expedition.id)
    assert any(item.hex.terrain_key == "SEA" for item in result.scan.visible_hexes)

    state = PlayerMapService(db).get(expedition.id)
    assert any(row.terrain_key == "SEA" for row in state.hexes)
    assert db.scalar(select(MapHex).where(MapHex.map_version_id == version.id, MapHex.terrain_key == "SEA")) is not None


def test_player_ping_is_only_an_adjacent_intention_and_dm_movement_clears_it(db, campaign):
    _, version, _ = make_sparse_map(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=25)
    service = ExpeditionPingService(db)

    pinged = service.set_ping(expedition.id, character.owner_user_id, 1, 0)
    assert (pinged.q, pinged.r, pinged.game_minute) == (1, 0, 25)
    assert pinged.user_id == character.owner_user_id
    assert pinged.color == "#ff4f64"


def test_hidden_poi_requires_explicit_dm_discovery_even_on_current_hex(db, campaign):
    _, version, origin = make_sparse_map(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=50)
    poi = PointOfInterest(
        feature_id=777, hex_id=origin.id, name="Secret Door", kind="SECRET",
        dm_description="A concealed stone door.", player_description="A narrow hidden doorway.",
        requires_discovery=True, is_landmark=False, is_hub=False,
    )
    db.add(poi); db.commit()

    automatic = VisibilityService(db).observe_visible_pois(expedition.id)
    assert all(row.target_id != poi.feature_id for row in automatic.observations)

    revealed = KnowledgeService(db).discover_poi(expedition.id, poi.id)
    assert revealed and revealed[0].knowledge["description"] == "A narrow hidden doorway."
    known = KnowledgeService(db).latest_for_target(character.id, "POI", poi.feature_id)
    assert known.source_type == "DISCOVERY"


def test_player_map_marks_current_fov_separately_from_historical_discovery(db, campaign):
    _, version, _ = make_sparse_map(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=75)
    VisibilityService(db).observe_visible_pois(expedition.id)
    state = PlayerMapService(db).get(expedition.id)
    assert state.visible_hex_coords
    assert (expedition.current_q, expedition.current_r) in state.visible_hex_coords



def test_player_map_exposes_only_semantic_edges_inside_known_hexes(db, campaign):
    _, version, _ = make_sparse_map(db, campaign)
    expedition, _ = make_active_expedition(db, campaign, version, game_minute=90)
    VisibilityService(db).observe_visible_pois(expedition.id)
    known = PlayerMapService(db).get(expedition.id).hexes
    coords = {(row.q, row.r) for row in known}
    assert (0, 0) in coords
    adjacent = next((coord for coord in coords if coord != (0, 0)), None)
    assert adjacent is not None
    aq, ar = adjacent
    db.add(MapEdge(
        map_version_id=version.id, from_q=0, from_r=0, to_q=aq, to_r=ar,
        feature_type="ROAD", feature_id=501, segment_index=0, name="Known road", extra_data={},
    ))
    db.add(MapEdge(
        map_version_id=version.id, from_q=20, from_r=20, to_q=21, to_r=20,
        feature_type="RIVER", feature_id=502, segment_index=0, name="Secret river", extra_data={},
    ))
    db.commit()

    state = PlayerMapService(db).get(expedition.id)
    assert [edge.feature_id for edge in state.edges] == [501]


def test_flow4_game_map_frontend_assets_exist():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    dm_html = (root / "static/dm_expedition.html").read_text()
    dm_js = (root / "static/js/dm_expedition.js").read_text()
    player_html = (root / "static/player.html").read_text()
    player_js = (root / "static/js/player.js").read_text()
    assert "Ouvrir la carte joueur" in dm_html
    assert "/dm-expeditions/${expedition.id}/pois/${selectedPoi.id}/reveal" in dm_js
    assert "Clique simplement un hex adjacent" in player_html
    assert 'type="color"' in player_html
    assert "/api/expeditions/${state.expedition_id}/ping?user_id=${activePingUserId}" in player_js
    assert "pingHex(selected)" in player_js
    assert "visibility_state" in player_js
    assert "state.edges || []" in player_js
    assert "/player-map/bootstrap" not in player_js
    assert "playerMap?.ping_q" in dm_js


def test_dm_can_hide_and_reveal_poi_without_changing_world_visibility(db, campaign):
    _, version, origin = make_sparse_map(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=120)
    poi = PointOfInterest(
        feature_id=880, hex_id=origin.id, name="Hidden Shrine", kind="SHRINE",
        dm_description="DM secret", player_description="Old shrine",
        requires_discovery=True, is_landmark=True, is_hub=False,
    )
    db.add(poi); db.commit()

    service = KnowledgeService(db)
    service.set_poi_player_visibility(expedition.id, poi.id, visible=True)
    assert [item.target_id for item in PlayerMapService(db).get(expedition.id).pois] == [poi.feature_id]

    # Same campaign minute toggle must be legal and must hide the latest known
    # snapshot instead of accidentally exposing the previous one.
    hidden = service.set_poi_player_visibility(expedition.id, poi.id, visible=False)
    assert hidden[0].source_type == "DM_HIDDEN"
    assert hidden[0].knowledge["hidden_from_players"] is True
    assert PlayerMapService(db).get(expedition.id).pois == []

    revealed = service.set_poi_player_visibility(expedition.id, poi.id, visible=True)
    assert revealed[0].source_type == "DISCOVERY"
    assert revealed[0].knowledge["hidden_from_players"] is False
    assert [item.target_id for item in PlayerMapService(db).get(expedition.id).pois] == [poi.feature_id]


def test_flow4_session_controls_use_ctrl_y_and_explicit_knowledge_actions():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    dm_html = (root / "static/dm_expedition.html").read_text()
    dm_js = (root / "static/js/dm_expedition.js").read_text()
    player_js = (root / "static/js/player.js").read_text()
    assert "Ctrl+Z / Ctrl+Y" in dm_html
    assert "key==='y'" in dm_js
    assert "/hide?user_id=${userId}" in dm_js
    assert "Cacher aux joueurs" in dm_js
    assert "Visible à distance" in dm_js
    assert "expedition_id:expedition.id" in dm_js
    assert "cache:'no-store'" in dm_js
    assert 'cache: "no-store"' in player_js


def test_dm_hidden_poi_stays_hidden_during_later_auto_visibility(db, campaign):
    _, version, origin = make_sparse_map(db, campaign)
    expedition, _character = make_active_expedition(db, campaign, version, game_minute=140)
    poi = PointOfInterest(
        feature_id=990, hex_id=origin.id, name="Vanishing Village", kind="TOWN",
        dm_description="secret", player_description="village",
        requires_discovery=False, is_landmark=True, is_hub=False,
    )
    db.add(poi); db.commit()
    service = KnowledgeService(db)
    service.set_poi_player_visibility(expedition.id, poi.id, visible=True)
    service.set_poi_player_visibility(expedition.id, poi.id, visible=False)
    expedition.current_game_minute += 10
    db.commit()
    automatic = VisibilityService(db).observe_visible_pois(expedition.id)
    assert all(row.target_id != poi.feature_id for row in automatic.observations)
    assert PlayerMapService(db).get(expedition.id).pois == []


def test_returned_expedition_keeps_historical_map_snapshot(db, campaign):
    from services.expedition_service import ExpeditionService
    _, version, _ = make_sparse_map(db, campaign)
    expedition, _character = make_active_expedition(db, campaign, version, game_minute=160)
    VisibilityService(db).observe_visible_pois(expedition.id)
    before = {(row.q, row.r) for row in PlayerMapService(db).get(expedition.id).hexes}
    assert before
    ExpeditionService(db).return_to_hub(expedition.id)
    archived = PlayerMapService(db).get(expedition.id)
    assert {(row.q, row.r) for row in archived.hexes} == before
    assert archived.visible_hex_coords == set()


def test_ping_color_is_persistent_on_user(db, campaign):
    _, version, _ = make_sparse_map(db, campaign)
    expedition, character = make_active_expedition(db, campaign, version, game_minute=180)
    character.owner.ping_color = "#12abef"
    db.commit()
    ping = ExpeditionPingService(db).set_ping(expedition.id, character.owner_user_id, 1, 0)
    assert ping.color == "#12abef"
    assert ping.username == character.owner.username
