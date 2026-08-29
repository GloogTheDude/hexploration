from models.hexmap import Hexmap
from models.constants import SEA, FOREST


def test_hexmap_defaults_to_sea_without_dense_allocation():
    hexmap = Hexmap(10, 10, 32)
    assert hexmap.sparse is True
    assert len(hexmap.hexes) == 0
    assert hexmap.get_hex(0, 0).terrain == SEA
    assert len(hexmap.hexes) == 1  # lazy materialisation only


def test_get_hex_returns_correct_hex():
    hexmap = Hexmap(10, 10, 32)
    hex_tile = hexmap.get_hex(3, 2)
    assert hex_tile is not None
    assert hex_tile.q == 3
    assert hex_tile.r == 2


def test_paint_hex_changes_terrain():
    hexmap = Hexmap(10, 10, 32)
    updated_hex = hexmap.paint_hex(3, 2, FOREST)
    assert updated_hex is not None
    assert updated_hex.terrain == FOREST
    assert hexmap.get_hex(3, 2).terrain == FOREST


def test_get_hexes_in_radius_0_returns_one_hex():
    hexmap = Hexmap(10, 10, 32)
    hexes = hexmap.get_hexes_in_radius(0, 0, 0)
    assert len(hexes) == 1


def test_get_hexes_in_radius_1_returns_seven_hexes():
    assert len(Hexmap(10, 10, 32).get_hexes_in_radius(0, 0, 1)) == 7


def test_get_hexes_in_radius_2_returns_nineteen_hexes():
    assert len(Hexmap(10, 10, 32).get_hexes_in_radius(0, 0, 2)) == 19


def test_paint_radius_changes_all_hexes_in_radius():
    hexmap = Hexmap(10, 10, 32)
    modified = hexmap.paint_radius(0, 0, FOREST, 2)
    assert len(modified) == 19
    assert all(h.terrain == FOREST for h in modified)


def test_new_map_uses_rectangular_flat_top_footprint():
    hexmap = Hexmap(6, 4, 32)
    schema = hexmap.get_coord_schema()

    assert len(schema) == 4
    assert all(len(row) == 6 for row in schema)
    assert len({coord for row in schema for coord in row}) == 24

    # With flat-top axial projection, logical rows stay horizontal apart from
    # the expected half-row stagger between alternating columns.
    def screen_y(q, r):
        return r + q / 2

    for row in schema:
        ys = [screen_y(q, r) for q, r in row]
        assert max(ys) - min(ys) == 0.5


def test_offset_axial_conversion_round_trips():
    for width, height in ((6, 4), (7, 5), (20, 20)):
        for col in range(width):
            for row in range(height):
                q, r = Hexmap.offset_to_axial(col, row, width, height)
                assert Hexmap.axial_to_offset(q, r, width, height) == (col, row)


def test_world_scale_map_does_not_materialize_one_hundred_million_hexes():
    hexmap = Hexmap(10_000, 10_000, 16)
    assert hexmap.width * hexmap.height == 100_000_000
    assert len(hexmap.hexes) == 0
    assert hexmap.layout == "even-q-rect"


def test_map_dimension_guard_rejects_more_than_ten_thousand_per_axis():
    import pytest
    with pytest.raises(ValueError, match="10,000"):
        Hexmap(10_001, 10, 16)
