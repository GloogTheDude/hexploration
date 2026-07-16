from models.hexmap import Hexmap
from models.constants import SEA, FOREST


def test_hexmap_is_filled_with_sea():
    hexmap = Hexmap(10, 10, 32)

    assert len(hexmap.hexes) == 100

    for hex_tile in hexmap.hexes.values():
        assert hex_tile.terrain == SEA


def test_get_hex_returns_correct_hex():
    hexmap = Hexmap(10, 10, 32)

    hex_tile = hexmap.get_hex(3, 4)

    assert hex_tile is not None
    assert hex_tile.q == 3
    assert hex_tile.r == 4


def test_paint_hex_changes_terrain():
    hexmap = Hexmap(10, 10, 32)

    updated_hex = hexmap.paint_hex(3, 4, FOREST)

    assert updated_hex is not None
    assert updated_hex.terrain == FOREST
    assert hexmap.get_hex(3, 4).terrain == FOREST


def test_get_hexes_in_radius_0_returns_one_hex():
    hexmap = Hexmap(10, 10, 32)

    hexes = hexmap.get_hexes_in_radius(0, 0, 0)

    assert len(hexes) == 1
    assert hexes[0].q == 0
    assert hexes[0].r == 0


def test_get_hexes_in_radius_1_returns_seven_hexes():
    hexmap = Hexmap(10, 10, 32)

    hexes = hexmap.get_hexes_in_radius(0, 0, 1)

    assert len(hexes) == 7


def test_get_hexes_in_radius_2_returns_nineteen_hexes():
    hexmap = Hexmap(10, 10, 32)

    hexes = hexmap.get_hexes_in_radius(0, 0, 2)

    assert len(hexes) == 19


def test_paint_radius_changes_all_hexes_in_radius():
    hexmap = Hexmap(10, 10, 32)

    modified = hexmap.paint_radius(0, 0, FOREST, 2)

    assert len(modified) == 19

    for hex_tile in modified:
        assert hex_tile.terrain == FOREST

def test_print_coords_schema():
    hexmap = Hexmap(4, 4, 32)
    schema = hexmap.get_coord_schema()
    expected_schema=    [[(-2,-2),(-1,-2),(0,-2),(1,-2)],
[(-2,-1),(-1,-1),(0,-1),(1,-1)],
[(-2,0),(-1,0),(0,0),(1,0)],
[(-2,1),(-1,1),(0,1),(1,1)]]
    assert expected_schema == schema

def test_print_terrain_schema():
    hexmap = Hexmap(4, 4, 32)
    schema = hexmap.get_terrain_schema()
    expected_schema=    [[SEA,SEA,SEA,SEA],
                        [SEA,SEA,SEA,SEA],
                        [SEA,SEA,SEA,SEA],
                        [SEA,SEA,SEA,SEA]]
    assert expected_schema == schema

def test_print_terrain_schema_after_paint():
    hexmap = Hexmap(4, 4, 32)
    updated_hex = hexmap.paint_hex(-1, 1, FOREST)

    schema = hexmap.get_terrain_schema()
    expected_schema=    [[SEA,SEA,SEA,SEA],
                        [SEA,SEA,SEA,SEA],
                        [SEA,SEA,SEA,SEA],
                        [SEA,FOREST, SEA,SEA]]
    
    assert updated_hex is not None
    assert updated_hex.terrain == FOREST
    assert hexmap.get_hex(-1, 1).terrain == FOREST
    assert expected_schema == schema
