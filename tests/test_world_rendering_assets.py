from pathlib import Path


def test_world_editor_has_continuous_water_and_smooth_river_rendering():
    source = Path("static/js/world.js").read_text()
    assert "size*1.005" in source
    assert "const a1=-i*Math.PI/3" in source
    assert "strokeRiverNetwork(ctx,groups,center)" in source
    assert "function riverNetwork(groups)" in source


def test_world_editor_cache_bust_for_rendering_fix():
    html = Path("static/world.html").read_text()
    assert "/js/world.js?v=461" in html



def test_world_editor_renders_rivers_as_deduplicated_network():
    source = Path("static/js/world.js").read_text()
    assert "function riverNetwork(groups)" in source
    assert "if(!segments.has(key))" in source
    assert "strokeRiverNetwork(ctx,groups,center)" in source
    assert "if(count<3)continue" in source


def test_world_editor_clips_river_outlets_to_shoreline_and_supports_merge():
    source = Path("static/js/world.js").read_text()
    html = Path("static/world.html").read_text()
    assert "function isWaterHex" in source
    assert "clipStart" in source and "clipEnd" in source
    assert "shorelinePoint" in source
    assert 'id="world-edge-merge"' in html
    assert "/dm-linear-features/merge?user_id=" in source
    assert "selectedEdgeIds" in source


def test_world_editor_renders_branched_river_features_from_concrete_edges():
    source = Path("static/js/world.js").read_text()
    network = source[source.index("function riverNetwork(groups)"):source.index("function edgePoints(edge,center)")]
    assert "for(const edge of group)" in network
    assert "orderedPath(group)" not in network
    assert "Selection is also rendered from concrete corridors" in network
