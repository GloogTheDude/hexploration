from pathlib import Path


def test_world_editor_event_form_does_not_overflow_inspector():
    css = Path('static/css/world.css').read_text(encoding='utf-8')
    assert '.world-inspector{overflow-y:auto;overflow-x:hidden' in css
    assert '.event-date-block .game-date-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr))!important' in css
    assert '.event-form-actions{grid-template-columns:minmax(0,1fr) minmax(92px,.36fr)}' in css


def test_world_editor_event_edit_has_explicit_submit_feedback_and_cache_bust():
    html = Path('static/world.html').read_text(encoding='utf-8')
    js = Path('static/js/world.js').read_text(encoding='utf-8')
    assert 'id="world-poi-event-submit"' in html
    assert 'id="world-poi-event-feedback"' in html
    assert "submit.textContent=event?'Enregistrer les modifications':'Ajouter l’événement'" in js
    assert "Mise à jour de l’événement #${id}" in js
    assert '/js/world.js?v=444' in html
    assert '/css/world.css?v=444' in html
