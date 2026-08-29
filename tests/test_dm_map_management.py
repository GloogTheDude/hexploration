from pathlib import Path


def test_dm_map_management_frontend_assets():
    js = Path('static/js/dm.js').read_text()
    assert 'data-delete-map' in js
    assert '/dm-maps/${mapId}?user_id=${state.userId}' in js
    assert 'format=png' in js
    assert 'format=jpeg' in js
    assert 'format=pdf' in js


def test_pillow_declared_for_map_exports():
    requirements = Path('requirements.txt').read_text()
    assert 'Pillow' in requirements
