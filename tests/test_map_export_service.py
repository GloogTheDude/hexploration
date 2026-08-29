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
