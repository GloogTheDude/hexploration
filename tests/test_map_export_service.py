from io import BytesIO

from PIL import Image

from db.models import Campaign, MapHex, MapVersion, WorldMap
from services.map_export_service import MapExportService


def _make_map(db):
    campaign = Campaign(name='Export campaign', epoch_name='Era')
    db.add(campaign); db.flush()
    world_map = WorldMap(campaign_id=campaign.id, name='Export Map')
    db.add(world_map); db.flush()
    version = MapVersion(map_id=world_map.id, version=1, width=2, height=2, hex_size=20, effective_from_game_minute=0)
    db.add(version); db.flush()
    for q, r, terrain in [(0,0,'SEA'), (0,1,'PLAIN'), (1,0,'FOREST'), (1,-1,'HILL')]:
        db.add(MapHex(map_version_id=version.id, q=q, r=r, terrain_key=terrain, elevation=0, visibility_score=3, travel_cost=1.0, extra_data={}))
    db.commit()
    return campaign, world_map, version


def test_map_export_png_jpeg_pdf(db):
    _, _, version = _make_map(db)
    service = MapExportService(db)
    png, png_type, png_name = service.render(version.id, 'png')
    assert png.startswith(b'\x89PNG') and png_type == 'image/png' and png_name.endswith('.png')
    with Image.open(BytesIO(png)) as img:
        assert img.width > 0 and img.height > 0
    jpg, jpg_type, jpg_name = service.render(version.id, 'jpeg')
    assert jpg.startswith(b'\xff\xd8') and jpg_type == 'image/jpeg' and jpg_name.endswith('.jpg')
    pdf, pdf_type, pdf_name = service.render(version.id, 'pdf')
    assert pdf.startswith(b'%PDF') and pdf_type == 'application/pdf' and pdf_name.endswith('.pdf')


def test_world_export_includes_semantic_layers_and_terrain_mode_stays_plain(db):
    from db.models import MapArea, MapEdge, PointOfInterest

    _, _, version = _make_map(db)
    land = db.scalar(
        __import__('sqlalchemy').select(MapHex).where(
            MapHex.map_version_id == version.id,
            MapHex.q == 1,
            MapHex.r == 0,
        )
    )
    assert land is not None
    db.add(PointOfInterest(feature_id=1, hex_id=land.id, name='Tower', kind='TOWER', dm_description=None, is_landmark=True))
    db.add(MapArea(map_version_id=version.id, feature_type='LAKE', feature_id=1, name='Blue Lake', cells=[{'q': 0, 'r': 1}], extra_data={}))
    db.add(MapEdge(
        map_version_id=version.id, from_q=1, from_r=0, to_q=0, to_r=0,
        feature_type='RIVER', feature_id=2, segment_index=0, name='River',
        extra_data={'path_from': {'q': 1, 'r': 0}, 'path_to': {'q': 0, 'r': 0}},
    ))
    db.add(MapEdge(
        map_version_id=version.id, from_q=1, from_r=0, to_q=1, to_r=-1,
        feature_type='ROAD', feature_id=3, segment_index=0, name='Road',
        extra_data={'path_from': {'q': 1, 'r': 0}, 'path_to': {'q': 1, 'r': -1}},
    ))
    db.commit()

    service = MapExportService(db)
    world_png, _, world_name = service.render(version.id, 'png')
    terrain_png, _, terrain_name = service.render(version.id, 'png', mode='terrain')

    assert world_png.startswith(b'\x89PNG')
    assert terrain_png.startswith(b'\x89PNG')
    assert world_png != terrain_png
    assert world_name == 'Export_Map_v1.png'
    assert terrain_name == 'Export_Map_v1_terrain.png'


def test_world_export_rejects_unknown_mode(db):
    _, _, version = _make_map(db)
    import pytest
    with pytest.raises(ValueError, match='world or terrain'):
        MapExportService(db).render(version.id, 'png', mode='players')


def test_high_quality_export_is_larger_than_standard(db):
    _, _, version = _make_map(db)
    service = MapExportService(db)
    standard, _, _ = service.render(version.id, 'png', quality='standard')
    high, _, _ = service.render(version.id, 'png', quality='high')
    with Image.open(BytesIO(standard)) as a, Image.open(BytesIO(high)) as b:
        assert b.width >= a.width
        assert b.height >= a.height
        assert (b.width, b.height) != (a.width, a.height)


def test_export_rejects_unknown_quality(db):
    _, _, version = _make_map(db)
    import pytest
    with pytest.raises(ValueError, match='standard or high'):
        MapExportService(db).render(version.id, 'png', quality='potato')
