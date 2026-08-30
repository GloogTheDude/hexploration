from pathlib import Path


def test_world_editor_offsets_only_shared_road_segments_and_skips_ghost_junctions():
    source = Path("static/js/world.js").read_text(encoding="utf-8")
    assert "function sharedCorridorKeys" in source
    assert "sharedKeys.has(corridorKey(edge))" in source
    assert "sharedNodes.has(k)" in source
    assert "offsetting the whole semantic road creates ghost dots" in source
    assert "sharedCorridor(group,allGroups)" not in source


def test_export_skips_junction_fill_on_shared_road_river_nodes():
    source = Path("services/map_export_service.py").read_text(encoding="utf-8")
    assert "shared_nodes: set[tuple[int, int]] = set()" in source
    assert "shared_nodes.update((a, b))" in source
    assert "degree < 2 or h in shared_nodes" in source


def test_world_editor_cache_bust_for_shared_corridor_fix():
    html = Path("static/world.html").read_text(encoding="utf-8")
    assert '/js/world.js?v=444' in html
