import { formatGameDate, setDateInputs, gameMinuteFromDateInputs } from './game_time.js';
import { authReady, authFetch, getCurrentUser, logout } from './auth.js';
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const ui = {
  userId: $('#user-id'), loadUser: $('#load-user'), identity: $('#identity-message'), error: $('#error'),
  campaigns: $('#campaigns'), campaignCount: $('#campaign-count'), campaignMinute: $('#campaign-minute'), campaignDay: $('#campaign-day'),
  campaignTitle: $('#campaign-title'), campaignDescription: $('#campaign-description'), campaignActions: $('#campaign-actions'), stats: $('#stats'),
  statExpeditions: $('#stat-expeditions'), statCharacters: $('#stat-characters'), statMaps: $('#stat-maps'), statEvents: $('#stat-events'), empty: $('#empty'),
  overviewExpeditions: $('#overview-expeditions'), overviewEvents: $('#overview-events'), overviewMaps: $('#overview-maps'),
  expeditionList: $('#expedition-list'), expeditionDetail: $('#expedition-detail'), refreshExpeditions: $('#refresh-expeditions'),
  togglePlanner: $('#toggle-planner'), plannerForm: $('#expedition-planner-form'), planName: $('#plan-name'), planMap: $('#plan-map'), planMapVersion: $('#plan-map-version'), planHubSummary: $('#plan-hub-summary'), planCharacters: $('#plan-characters'), planStartNow: $('#plan-start-now'), plannerMessage: $('#planner-message'),
  worldMinute: $('#world-minute'), inspectWorld: $('#inspect-world'), useCurrentMinute: $('#use-current-minute'), worldSummary: $('#world-summary'), worldGlobal: $('#world-global'), worldTargets: $('#world-targets'),
  mapsList: $('#maps-list'), charactersList: $('#characters-list'), timelineFrame: $('#timeline-frame'), timelineOpen: $('#timeline-open'),
  mapEditorOpen: $('#map-editor-open'), worldEditorOpen: $('#world-editor-open'), membersList: $('#members-list'), memberForm: $('#member-form'), memberUserId: $('#member-user-id'), memberMessage: $('#member-message'), sentInvitations: $('#sent-invitations'), refreshInvitations: $('#refresh-invitations'),
};

const state = { userId: null, campaigns: [], campaignId: null, dashboard: null, invitations: [], expeditionId: null, tab: 'overview', mapWorkbench: null, selectedHex: null, selectedHexes: [], selectedPoiId: null, selectedEdgeId: null, poiUndoStack: [], poiRedoStack: [] };

Object.assign(ui, {
  toggleCampaignCreate: $('#toggle-campaign-create'), campaignCreateForm: $('#campaign-create-form'), campaignCreateName: $('#campaign-create-name'), campaignCreateEpoch: $('#campaign-create-epoch'), campaignCreateDescription: $('#campaign-create-description'), campaignCreateMessage: $('#campaign-create-message'), cancelCampaignCreate: $('#cancel-campaign-create'),
  workbenchVersion: $('#workbench-version'), loadWorkbench: $('#load-workbench'), workbenchMessage: $('#workbench-message'), mapCanvas: $('#dm-map-canvas'), selectedHex: $('#selected-hex'),
  newPoi: $('#new-poi'), poiList: $('#poi-list'), poiForm: $('#poi-form'), poiId: $('#poi-id'), poiName: $('#poi-name'), poiKind: $('#poi-kind'), poiLandmark: $('#poi-landmark'), poiHub: $('#poi-hub'), poiDescription: $('#poi-description'),
  poiEventForm: $('#poi-event-form'), poiEventMinute: $('#poi-event-minute'), poiEventType: $('#poi-event-type'), poiEventPayload: $('#poi-event-payload'), poiEventNote: $('#poi-event-note'),
  edgeSelection: $('#edge-selection'), edgeForm: $('#edge-form'), edgeType: $('#edge-type'), edgeName: $('#edge-name'), edgeList: $('#edge-list'),
  edgeEventForm: $('#edge-event-form'), edgeEventMinute: $('#edge-event-minute'), edgeEventType: $('#edge-event-type'), edgeEventPayload: $('#edge-event-payload'), edgeEventNote: $('#edge-event-note'),
  areaForm: $('#area-form'), areaType: $('#area-type'), areaName: $('#area-name'), areaList: $('#area-list'),
});

async function api(path, options = {}) {
  const response = await authFetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); } catch (_) {}
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function esc(v) { return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function qs(key, value) { const u = new URL(location.href); value == null ? u.searchParams.delete(key) : u.searchParams.set(key, value); history.replaceState(null, '', u); }
function dayMinute(minute) { return formatGameDate(minute); }
function statusClass(status) { return `status status-${status}`; }

function setTab(name) {
  state.tab = name;
  $$('.tab').forEach(b => b.classList.toggle('selected', b.dataset.tab === name));
  $$('[data-panel]').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== name));
  if (!state.dashboard) return;
  if (name === 'world' && !ui.worldSummary.dataset.loaded) inspectWorld();
  if (name === 'timeline') loadTimeline();
}

function renderCampaigns() {
  ui.campaignCount.textContent = state.campaigns.length;
  ui.campaigns.innerHTML = state.campaigns.map(c => `<div class="campaign-item ${c.id === state.campaignId ? 'selected' : ''}" data-campaign="${c.id}"><strong>${esc(c.name)}</strong><div class="small">${esc(c.epoch_name)} · MJ</div></div>`).join('') || '<div class="empty">Aucune campagne où cet utilisateur est MJ.</div>';
  $$('[data-campaign]').forEach(el => el.addEventListener('click', () => selectCampaign(Number(el.dataset.campaign))));
}

function renderEvent(event) {
  const target = event.target_type ? `${esc(event.target_type)} #${event.target_id ?? '—'}` : 'global';
  return `<div class="event-row"><div class="event-top"><span class="event-type">${esc(event.event_type)}</span><span>${formatGameDate(event.game_minute)}</span></div><div class="small">${target}${event.expedition_id ? ` · expedition #${event.expedition_id}` : ''}</div>${Object.keys(event.payload || {}).length ? `<div class="event-payload">${esc(JSON.stringify(event.payload))}</div>` : ''}${event.dm_note ? `<div class="small">MJ: ${esc(event.dm_note)}</div>` : ''}</div>`;
}

function renderOverview() {
  const d = state.dashboard;
  const active = d.expeditions.filter(e => e.status === 'ACTIVE');
  ui.overviewExpeditions.innerHTML = active.map(e => `<div class="mini-row"><div class="record-head"><strong>${esc(e.name)}</strong><span class="${statusClass(e.status)}">${e.status}</span></div><div class="small">${formatGameDate(e.current_game_minute)} · ${e.current_q == null ? 'non positionnée' : `(${e.current_q}, ${e.current_r})`} · ${e.participants.length} perso.</div></div>`).join('') || '<div class="empty">Aucune expédition active.</div>';
  ui.overviewEvents.innerHTML = d.recent_events.slice(0, 6).map(renderEvent).join('') || '<div class="empty">Aucun WorldEvent.</div>';
  ui.overviewMaps.innerHTML = d.maps.map(m => { const latest = m.versions[0]; return `<div class="map-chip"><strong>${esc(m.name)}</strong><div class="small">${m.versions.length} version(s)</div>${latest ? `<div class="small">Dernière: v${latest.version} · ${latest.hex_count} hex · ${formatGameDate(latest.effective_from_game_minute)}</div>` : '<div class="small">Aucune version</div>'}</div>`; }).join('') || '<div class="empty">Aucune carte persistée.</div>';
}

function renderPlanner() {
  if (!state.dashboard) return;
  const d = state.dashboard;
  const openStatuses = new Set(['PLANNING', 'ACTIVE', 'DEBRIEFING']);
  const assigned = new Set();
  for (const expedition of d.expeditions) {
    if (!openStatuses.has(expedition.status)) continue;
    for (const participant of expedition.participants) {
      if (participant.left_game_minute == null) assigned.add(participant.character_id);
    }
  }

  const previousMapId = Number(ui.planMap.value) || d.maps[0]?.id || null;
  ui.planMap.innerHTML = d.maps.map(map => `<option value="${map.id}">${esc(map.name)}</option>`).join('');
  if (previousMapId && d.maps.some(map => map.id === previousMapId)) ui.planMap.value = String(previousMapId);
  const selectedMap = d.maps.find(map => map.id === Number(ui.planMap.value)) || d.maps[0] || null;
  const previousVersionId = Number(ui.planMapVersion.value) || null;
  const versions = selectedMap?.versions || [];
  ui.planMapVersion.innerHTML = versions.map(version =>
    `<option value="${version.id}">v${version.version}${version.name ? ` · ${esc(version.name)}` : ''} · ${formatGameDate(version.effective_from_game_minute)}</option>`
  ).join('');
  if (previousVersionId && versions.some(v => v.id === previousVersionId)) ui.planMapVersion.value = String(previousVersionId);
  const selectedVersion = versions.find(v => v.id === Number(ui.planMapVersion.value)) || versions[0] || null;
  const hub = selectedVersion?.hub_poi_id ? {id:selectedVersion.hub_poi_id,name:selectedVersion.hub_name,q:selectedVersion.hub_q,r:selectedVersion.hub_r} : null;
  ui.planHubSummary.classList.toggle('error', Boolean(selectedVersion && !hub));
  ui.planHubSummary.innerHTML = !selectedMap ? 'Aucune carte persistée.'
    : !selectedVersion ? 'Cette carte ne possède aucune version.'
    : hub ? `<strong>Hub de départ :</strong> ${esc(hub.name)} · (${hub.q}, ${hub.r})`
    : '<strong>Aucun hub défini.</strong> Ouvre l’Éditeur du monde et marque un POI comme « Hub de départ » pour cette version.';

  const playerMembers = d.members.filter(member => member.role === 'PLAYER');
  const playerCharacters = d.characters.filter(character => character.owner_role === 'PLAYER');
  const availablePlayers = playerMembers.map(member => ({
    member,
    characters: playerCharacters.filter(character =>
      character.owner_user_id === member.user_id
      && character.status === 'ACTIVE'
      && !assigned.has(character.id)
    ),
  })).filter(entry => entry.characters.length > 0);

  ui.planCharacters.innerHTML = availablePlayers.map(({member, characters}) => {
    const picks = characters.map(character =>
      `<label class="character-pick"><input type="checkbox" value="${character.id}"><span><strong>${esc(character.name)}</strong><span class="small">horloge ${esc(formatGameDate(character.current_game_minute))}</span></span></label>`
    ).join('');
    return `<section class="planner-player"><div class="planner-player-head"><strong>${esc(member.username)}</strong><span class="small">joueur #${member.user_id}</span></div>${picks}</section>`;
  }).join('') || '<div class="empty">Aucun personnage disponible pour une nouvelle expédition.</div>';

  if (!ui.planName.value && !ui.planName.dataset.timeInitialized) {
    setDateInputs('plan-time', d.campaign_game_minute);
    ui.planName.dataset.timeInitialized = '1';
  }
  if (!d.maps.length) ui.plannerMessage.textContent = 'Aucune carte persistée : crée d’abord une carte depuis l’éditeur.';
  else if (!ui.plannerMessage.classList.contains('error')) ui.plannerMessage.textContent = '';
}

async function createExpeditionPlan(event) {
  event.preventDefault();
  if (!state.dashboard || !state.campaignId || !state.userId) return;
  const characterIds = [...ui.planCharacters.querySelectorAll('input[type="checkbox"]:checked')].map(input => Number(input.value));
  ui.plannerMessage.classList.remove('error');
  ui.plannerMessage.textContent = 'Création…';
  let startMinute;
  try { startMinute = gameMinuteFromDateInputs('plan-time'); }
  catch (error) { ui.plannerMessage.classList.add('error'); ui.plannerMessage.textContent = error.message; return; }
  const payload = {
    name: ui.planName.value.trim(),
    start_game_minute: startMinute,
    character_ids: characterIds,
    map_version_id: Number(ui.planMapVersion.value),
    start_now: ui.planStartNow.checked,
  };
  try {
    const created = await api(`/api/campaigns/${state.campaignId}/dm-expeditions?user_id=${state.userId}`, { method: 'POST', body: JSON.stringify(payload) });
    state.expeditionId = created.expedition_id;
    ui.planName.value = '';
    await refreshDashboard();
    ui.plannerMessage.classList.remove('error');
    ui.plannerMessage.textContent = `Expédition #${created.expedition_id} créée (${created.status}) · départ ${formatGameDate(created.start_game_minute)}.`;
  } catch (error) {
    ui.plannerMessage.classList.add('error');
    ui.plannerMessage.textContent = error.message;
  }
}

function renderExpeditions() {
  const d = state.dashboard;
  ui.expeditionList.innerHTML = d.expeditions.map(e => `<div class="record ${e.id === state.expeditionId ? 'selected' : ''}" data-expedition="${e.id}"><div class="record-head"><strong>${esc(e.name)}</strong><span class="${statusClass(e.status)}">${e.status}</span></div><div class="record-meta"><span>#${e.id}</span><span>${formatGameDate(e.current_game_minute)}</span><span>${e.current_q == null ? 'sans position' : `(${e.current_q}, ${e.current_r})`}</span><span>${e.participants.length} participant(s)</span></div></div>`).join('') || '<div class="empty">Aucune expédition.</div>';
  $$('[data-expedition]').forEach(el => el.addEventListener('click', () => { state.expeditionId = Number(el.dataset.expedition); renderExpeditions(); renderExpeditionDetail(); }));
  renderExpeditionDetail();
}

function renderExpeditionDetail() {
  const e = state.dashboard?.expeditions.find(x => x.id === state.expeditionId);
  if (!e) { ui.expeditionDetail.innerHTML = '<p class="muted">Sélectionne une expédition.</p>'; return; }
  const map = state.dashboard.maps.flatMap(m => m.versions.map(v => ({map:m, version:v}))).find(x => x.version.id === e.current_map_version_id);
  const canStart = e.status === 'PLANNING'; const canReturn = e.status === 'ACTIVE';
  ui.expeditionDetail.innerHTML = `<div class="eyebrow">Expédition #${e.id}</div><h3>${esc(e.name)}</h3><span class="${statusClass(e.status)}">${e.status}</span>
    <div class="detail-section"><div class="small">Départ</div><strong>${formatGameDate(e.start_game_minute)}</strong><div class="small">Horloge actuelle</div><strong>${formatGameDate(e.current_game_minute)} · ${dayMinute(e.current_game_minute)}</strong></div>
    <div class="detail-section"><div class="small">Position</div><strong>${e.current_q == null ? 'Non positionnée' : `(${e.current_q}, ${e.current_r})`}</strong><div class="small">Carte</div><strong>${map ? `${esc(map.map.name)} · v${map.version.version}` : (e.current_map_version_id ? `MapVersion #${e.current_map_version_id}` : '—')}</strong><div class="small">Météo / transport</div><strong>${esc(e.weather_key || '—')} / ${esc(e.transport_key || '—')}</strong></div>
    <div class="detail-section"><strong>Participants</strong>${e.participants.map(p => `<div class="participant"><span>${esc(p.character_name)} <span class="small">#${p.character_id}</span></span><span>${p.left_game_minute == null ? 'présent' : `sorti ${formatGameDate(p.left_game_minute)}`}</span></div>`).join('') || '<div class="empty">Aucun participant.</div>'}</div>
    <div class="detail-actions">${canStart ? '<button id="action-start">Démarrer</button>' : ''}${canReturn ? '<button id="action-return">Retour au hub</button>' : ''}${e.current_map_version_id && e.current_q != null ? `<a class="button-link" href="/dm_expedition.html?user=${state.userId}&campaign=${state.campaignId}&expedition=${e.id}">Carte d'expédition MJ</a><a class="button-link" target="_blank" rel="noopener" href="/player.html?expedition=${e.id}&display=1&user=${state.userId}">Carte joueur ↗</a>` : ''}<a class="button-link" href="/timeline.html?campaign_id=${state.campaignId}">Timeline</a></div>
    <p id="expedition-action-message" class="error"></p>`;
  $('#action-start')?.addEventListener('click', () => expeditionAction('start'));
  $('#action-return')?.addEventListener('click', () => expeditionAction('return'));
}

async function expeditionAction(action) {
  const msg = $('#expedition-action-message'); if (msg) msg.textContent = 'Traitement…';
  try { await api(`/api/campaigns/${state.campaignId}/dm-expeditions/${state.expeditionId}/${action}?user_id=${state.userId}`, { method:'POST' }); await refreshDashboard(); if (msg) msg.textContent = ''; }
  catch (e) { if (msg) msg.textContent = e.message; }
}

function renderMaps() {
  ui.mapsList.innerHTML = state.dashboard.maps.map(m => `<article class="map-card"><div class="map-title"><div><strong>${esc(m.name)}</strong><div class="small">Map #${m.id}${m.description ? ` · ${esc(m.description)}` : ''}</div></div><div class="map-title-actions"><span class="badge">${m.versions.length} version(s)</span><button type="button" class="ghost danger-outline" data-delete-map="${m.id}" data-map-name="${esc(m.name)}">Supprimer</button></div></div><table class="version-table"><thead><tr><th>Version</th><th>Effective</th><th>Hub</th><th>Taille</th><th>Hex</th><th>POI</th><th>Edges</th><th>Actions</th></tr></thead><tbody>${m.versions.map(v => `<tr><td>v${v.version}${v.name ? ` · ${v.name}` : ''} <span class="small">#${v.id}</span></td><td>${formatGameDate(v.effective_from_game_minute)}</td><td>${v.hub_poi_id ? `${esc(v.hub_name)} (${v.hub_q}, ${v.hub_r})` : `<span class="muted">Non défini</span>`}</td><td>${v.width}×${v.height} · ${v.hex_size}px</td><td>${v.hex_count}</td><td>${v.poi_count}</td><td>${v.edge_count}</td><td><div class="map-version-actions"><a class="button-link compact" href="/?user=${state.userId}&campaign=${state.campaignId}&map=${m.id}&version=${v.id}">Terrain</a><a class="button-link compact" href="/world.html?campaign=${state.campaignId}&version=${v.id}">Monde</a><div class="export-links" aria-label="Exporter la version"><span class="export-label">Monde</span><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=png&mode=world">PNG</a><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=jpeg&mode=world">JPEG</a><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=pdf&mode=world">PDF</a><span class="export-label">Terrain</span><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=png&mode=terrain">PNG</a><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=jpeg&mode=terrain">JPEG</a><a class="export-format" href="/api/campaigns/${state.campaignId}/dm-map-versions/${v.id}/export?user_id=${state.userId}&format=pdf&mode=terrain">PDF</a></div></div></td></tr>`).join('')}</tbody></table></article>`).join('') || '<div class="empty">Aucune carte persistée pour cette campagne.</div>';
  ui.mapsList.querySelectorAll('[data-delete-map]').forEach(btn => btn.addEventListener('click', () => deleteMap(Number(btn.dataset.deleteMap), btn.dataset.mapName)));
  renderWorkbenchVersionOptions();
}

async function deleteMap(mapId, mapName) {
  const typed = prompt(`Suppression définitive de la carte « ${mapName} ».\n\nTape exactement le nom de la carte pour confirmer :`);
  if (typed === null) return;
  if (typed !== mapName) { alert('Nom incorrect : suppression annulée.'); return; }
  try {
    await api(`/api/campaigns/${state.campaignId}/dm-maps/${mapId}?user_id=${state.userId}`, { method: 'DELETE' });
    if (state.mapWorkbench?.map_id === mapId) { state.mapWorkbench = null; state.selectedHex = null; state.selectedHexes = []; state.selectedPoiId = null; state.selectedEdgeId = null; }
    await refreshDashboard();
  } catch (error) {
    alert(`Impossible de supprimer la carte : ${error.message}`);
  }
}

function statValue(v) { return v == null ? '—' : esc(v); }
function renderCharacters() {
  const d=state.dashboard;
  ui.membersList.innerHTML=d.members.map(m=>`<div class="member-row"><div><strong>${esc(m.username)}</strong><span class="small">${esc(m.email)} · user #${m.user_id}</span></div><span class="badge">${m.role}</span></div>`).join('')||'<div class="empty">Aucun membre.</div>';
  ui.charactersList.innerHTML=d.characters.map(c=>{const owner=d.members.find(m=>m.user_id===c.owner_user_id);const hp=c.current_hp==null&&c.max_hp==null?'— / —':`${statValue(c.current_hp)} / ${statValue(c.max_hp)}`;return `<article class="character-card"><div class="record-head"><h3>${esc(c.name)}</h3><span class="status status-${c.status}">${c.status}</span></div><div class="small">#${c.id} · ${owner?esc(owner.username):`owner #${c.owner_user_id}`}</div><div>${esc(c.race||'—')} · ${esc(c.character_class||'—')}${c.level?` niv.${c.level}`:''}</div><div class="dm-character-stats"><span><b>PV</b> ${hp}</span><span><b>CA</b> ${statValue(c.armor_class)}</span><span><b>PP</b> ${statValue(c.passive_perception)}</span></div><button type="button" class="ghost dm-sheet-open" data-character-sheet="${c.id}" ${c.sheet_data?'':'disabled'}>${c.sheet_data?'Voir la fiche':'Fiche non initialisée'}</button></article>`}).join('')||'<div class="empty">Aucun personnage.</div>';
  ui.charactersList.querySelectorAll('[data-character-sheet]').forEach(btn=>btn.addEventListener('click',()=>openDMSheet(Number(btn.dataset.characterSheet))));
}
function openDMSheet(id){const c=state.dashboard?.characters.find(x=>x.id===id);if(!c?.sheet_data)return;const d=c.sheet_data;const f=[['FOR',d.strength],['DEX',d.dexterity],['CON',d.constitution],['INT',d.intelligence],['SAG',d.wisdom],['CHA',d.charisma],['PV',`${statValue(d.current_hp)} / ${statValue(d.max_hp)}`],['CA',d.armor_class],['Perception passive',d.passive_perception],['Initiative',d.initiative],['Maîtrise',d.proficiency_bonus],['Background',d.background],['Alignement',d.alignment]];const t=[['Attaques & sorts',d.attacks_spellcasting],['Équipement',d.equipment],['Maîtrises & langues',d.proficiencies_languages],['Traits',d.features_traits],['Notes',d.notes]];const m=document.createElement('div');m.className='dm-sheet-backdrop';m.innerHTML=`<section class="dm-sheet-modal" role="dialog" aria-modal="true"><div class="dm-sheet-head"><div><span class="eyebrow">Fiche personnage · lecture seule · v${c.sheet_version}</span><h2>${esc(c.name)}</h2><div class="muted">${esc(c.race||'—')} · ${esc(c.character_class||'—')}${c.level?` niv.${c.level}`:''}</div></div><button type="button" class="ghost" data-close-sheet>Fermer</button></div><div class="dm-sheet-stat-grid">${f.map(([k,v])=>`<div><span>${esc(k)}</span><strong>${statValue(v)}</strong></div>`).join('')}</div><div class="dm-sheet-text-grid">${t.map(([k,v])=>`<section><strong>${esc(k)}</strong><p>${esc(v||'—')}</p></section>`).join('')}</div></section>`;document.body.appendChild(m);const close=()=>m.remove();m.querySelector('[data-close-sheet]').addEventListener('click',close);m.addEventListener('click',e=>{if(e.target===m)close()})}

function invitationStatusLabel(status){ return status==='PENDING'?'En attente':status==='ACCEPTED'?'Acceptée':status==='REFUSED'?'Refusée':status; }
function renderSentInvitations(){
  if(!ui.sentInvitations) return;
  ui.sentInvitations.innerHTML = state.invitations.map(i => `<div class="invitation-row"><div><strong>${esc(i.invited_username)}</strong><span class="small">user #${i.invited_user_id}</span></div><span class="invite-status invite-${i.status}">${invitationStatusLabel(i.status)}</span>${i.status==='REFUSED'?`<button type="button" class="ghost" data-reinvite="${i.invited_user_id}">Réinviter</button>`:''}</div>`).join('') || '<div class="empty">Aucune invitation envoyée.</div>';
  ui.sentInvitations.querySelectorAll('[data-reinvite]').forEach(btn=>btn.addEventListener('click',()=>reinvite(Number(btn.dataset.reinvite))));
}
async function refreshInvitations(){
  if(!state.campaignId||!state.userId)return;
  try{ state.invitations=await api(`/api/campaigns/${state.campaignId}/invitations?user_id=${state.userId}`); renderSentInvitations(); }
  catch(e){ if(ui.memberMessage){ui.memberMessage.classList.add('error');ui.memberMessage.textContent=e.message;} }
}
async function reinvite(userId){ ui.memberUserId.value=userId; await addMember(new Event('submit')); }

async function addMember(event) {
  event.preventDefault();
  ui.memberMessage.classList.remove('error'); ui.memberMessage.textContent = 'Ajout…';
  try {
    await api(`/api/campaigns/${state.campaignId}/invitations?user_id=${state.userId}`, {method:'POST', body:JSON.stringify({invited_user_id:Number(ui.memberUserId.value)})});
    ui.memberUserId.value=''; ui.memberMessage.textContent='Invitation envoyée.'; await refreshInvitations();
  } catch(e) { ui.memberMessage.classList.add('error'); ui.memberMessage.textContent=e.message; }
}

async function inspectWorld() {
  if (!state.dashboard) return;
  let minute; try { minute = gameMinuteFromDateInputs('world-inspect'); ui.worldMinute.value = String(minute); } catch (e) { ui.worldSummary.innerHTML = `<p class="error">${esc(e.message)}</p>`; return; }
  ui.worldSummary.innerHTML = '<p class="muted">Résolution…</p>';
  try {
    const w = await api(`/api/campaigns/${state.campaignId}/world-state?game_minute=${minute}`);
    ui.worldSummary.dataset.loaded = '1';
    ui.worldSummary.innerHTML = `<div class="eyebrow">World Truth · ${formatGameDate(w.game_minute)}</div><strong>${w.weather_key ? `Météo : ${esc(w.weather_key)}` : 'Aucune météo globale résolue'}</strong><div class="small">${dayMinute(w.game_minute)} · ${w.latest_global_events.length} global · ${w.latest_target_events.length} ciblé(s)</div>`;
    ui.worldGlobal.innerHTML = w.latest_global_events.map(renderEvent).join('') || '<div class="empty">Aucun événement global applicable.</div>';
    ui.worldTargets.innerHTML = w.latest_target_events.map(renderEvent).join('') || '<div class="empty">Aucun état ciblé applicable.</div>';
  } catch (e) { ui.worldSummary.innerHTML = `<p class="error">${esc(e.message)}</p>`; }
}

function loadTimeline() {
  if (!state.campaignId) return;
  const src = `/timeline.html?campaign_id=${state.campaignId}&embedded=1`;
  if (!ui.timelineFrame.src.endsWith(src)) ui.timelineFrame.src = src;
  ui.timelineOpen.href = `/timeline.html?campaign_id=${state.campaignId}`;
}

function openCampaignEditor() {
  const campaign = state.dashboard?.campaign;
  if (!campaign) return;
  const modal = document.createElement('div');
  modal.className = 'dm-sheet-backdrop';
  modal.innerHTML = `<section class="dm-sheet-modal campaign-settings-modal" role="dialog" aria-modal="true" aria-labelledby="campaign-settings-title">
    <div class="dm-sheet-head"><div><span class="eyebrow">Paramètres campagne</span><h2 id="campaign-settings-title">Modifier ${esc(campaign.name)}</h2></div><button type="button" class="ghost" data-close-campaign-settings>Fermer</button></div>
    <form id="campaign-settings-form" class="campaign-settings-form">
      <label>Nom<input id="campaign-settings-name" maxlength="160" required value="${esc(campaign.name)}"></label>
      <label>Nom de l'époque<input id="campaign-settings-epoch" maxlength="80" required value="${esc(campaign.epoch_name)}"></label>
      <label>Description<textarea id="campaign-settings-description" rows="5">${esc(campaign.description || '')}</textarea></label>
      <div class="planner-actions"><button type="submit">Enregistrer</button><button type="button" class="secondary" data-close-campaign-settings>Annuler</button></div>
      <p id="campaign-settings-message" class="muted"></p>
    </form>
  </section>`;
  document.body.appendChild(modal);
  const close = () => modal.remove();
  modal.querySelectorAll('[data-close-campaign-settings]').forEach(button => button.addEventListener('click', close));
  modal.addEventListener('click', event => { if (event.target === modal) close(); });
  modal.querySelector('#campaign-settings-form').addEventListener('submit', async event => {
    event.preventDefault();
    const message = modal.querySelector('#campaign-settings-message');
    message.classList.remove('error'); message.textContent = 'Enregistrement…';
    try {
      await api(`/api/campaigns/${state.campaignId}/dm-settings?user_id=${state.userId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: modal.querySelector('#campaign-settings-name').value.trim(),
          epoch_name: modal.querySelector('#campaign-settings-epoch').value.trim(),
          description: modal.querySelector('#campaign-settings-description').value.trim() || null,
        }),
      });
      state.campaigns = await api(`/api/users/${state.userId}/dm-campaigns`);
      renderCampaigns();
      await refreshDashboard();
      close();
    } catch (error) {
      message.classList.add('error'); message.textContent = error.message;
    }
  });
}

async function deleteCurrentCampaign() {
  const campaign = state.dashboard?.campaign;
  if (!campaign) return;
  const typed = window.prompt(`Suppression définitive de « ${campaign.name} » et de toutes ses données.\n\nTape exactement le nom de la campagne pour confirmer :`);
  if (typed === null) return;
  if (typed !== campaign.name) {
    ui.error.textContent = 'Suppression annulée : le nom saisi ne correspond pas.';
    return;
  }
  try {
    await api(`/api/campaigns/${campaign.id}/dm-settings?user_id=${state.userId}`, { method: 'DELETE' });
    state.campaigns = await api(`/api/users/${state.userId}/dm-campaigns`);
    state.campaignId = null; state.dashboard = null; state.expeditionId = null;
    qs('campaign', null); renderCampaigns();
    ui.campaignTitle.textContent = 'Aucune campagne sélectionnée';
    ui.campaignDescription.textContent = 'Choisis une campagne MJ dans la colonne de gauche.';
    ui.campaignActions.innerHTML = '';
    ui.campaignMinute.textContent = '—'; ui.campaignDay.textContent = 'Sélectionne une campagne.';
    ui.stats.classList.add('hidden'); ui.empty.classList.remove('hidden');
    ui.identity.textContent = `${state.campaigns.length} campagne(s) administrée(s) comme MJ.`;
    const next = state.campaigns[0];
    if (next) await selectCampaign(next.id);
  } catch (error) {
    ui.error.textContent = error.message;
  }
}

function renderDashboard() {
  const d = state.dashboard;
  ui.empty.classList.add('hidden'); ui.stats.classList.remove('hidden');
  $$('[data-panel]').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== state.tab));
  ui.campaignTitle.textContent = d.campaign.name; ui.campaignDescription.textContent = d.campaign.description || 'Aucune description.';
  ui.campaignMinute.textContent = formatGameDate(d.campaign_game_minute); ui.campaignDay.textContent = d.campaign.epoch_name;
  ui.statExpeditions.textContent = d.active_expedition_count; ui.statCharacters.textContent = d.character_count; ui.statMaps.textContent = d.map_count; ui.statEvents.textContent = d.recent_events.length;
  ui.campaignActions.innerHTML = `<button type="button" class="secondary" id="edit-campaign">Modifier</button><button type="button" class="danger" id="delete-campaign">Supprimer</button><a class="button-link" href="/timeline.html?campaign_id=${d.campaign.id}">Timeline</a><a class="button-link" href="/?user=${state.userId}&campaign=${d.campaign.id}">Map editor</a><a class="button-link" href="/world.html?campaign=${d.campaign.id}">World editor</a><a class="button-link" href="/dashboard.html?user=${state.userId}&campaign=${d.campaign.id}">Vue joueur</a>`;
  $('#edit-campaign')?.addEventListener('click', openCampaignEditor);
  $('#delete-campaign')?.addEventListener('click', deleteCurrentCampaign);
  if (ui.mapEditorOpen) ui.mapEditorOpen.href = `/?user=${state.userId}&campaign=${d.campaign.id}`;
  if (ui.worldEditorOpen) ui.worldEditorOpen.href = `/world.html?campaign=${d.campaign.id}`;
  ui.worldMinute.value = d.campaign_game_minute; setDateInputs('world-inspect', d.campaign_game_minute); delete ui.worldSummary.dataset.loaded;
  if (!state.expeditionId || !d.expeditions.some(e => e.id === state.expeditionId)) state.expeditionId = d.expeditions.find(e => e.status === 'ACTIVE')?.id || d.expeditions[0]?.id || null;
  renderOverview(); renderPlanner(); renderExpeditions(); renderMaps(); renderCharacters(); if (state.tab === 'timeline') loadTimeline();
}

async function refreshDashboard() {
  if (!state.campaignId || !state.userId) return;
  const [dashboard, invitations] = await Promise.all([api(`/api/campaigns/${state.campaignId}/dm-dashboard?user_id=${state.userId}`), api(`/api/campaigns/${state.campaignId}/invitations?user_id=${state.userId}`)]);
  state.dashboard = dashboard; state.invitations = invitations;
  renderDashboard(); renderSentInvitations();
}

async function selectCampaign(id) {
  state.campaignId = id; qs('campaign', id); renderCampaigns(); ui.error.textContent = '';
  try { await refreshDashboard(); }
  catch (e) { state.dashboard = null; ui.error.textContent = e.message; }
}

async function loadUser() {
  const user = getCurrentUser(); if (!user) return;
  const userId = user.id;
  state.userId = userId; ui.error.textContent = ''; ui.identity.textContent = 'Chargement…';
  try {
    state.campaigns = await api(`/api/users/${userId}/dm-campaigns`);
    ui.identity.textContent = `${state.campaigns.length} campagne(s) administrée(s) comme MJ.`;
    renderCampaigns();
    const requested = Number(new URL(location.href).searchParams.get('campaign'));
    const initial = state.campaigns.find(c => c.id === requested) || state.campaigns[0];
    if (initial) await selectCampaign(initial.id);
    else { state.dashboard = null; state.campaignId = null; ui.empty.classList.remove('hidden'); ui.stats.classList.add('hidden'); }
  } catch (e) { ui.identity.textContent = 'Impossible de charger les campagnes MJ.'; ui.error.textContent = e.message; }
}

ui.loadUser?.addEventListener('click', loadUser); ui.userId?.addEventListener('keydown', e => { if (e.key === 'Enter') loadUser(); });
$$('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
$$('[data-jump]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.jump)));

ui.togglePlanner.addEventListener('click', () => {
  const hidden = ui.plannerForm.classList.toggle('hidden');
  ui.togglePlanner.textContent = hidden ? 'Afficher le planner' : 'Masquer le planner';
  if (!hidden) renderPlanner();
});
ui.plannerForm.addEventListener('submit', createExpeditionPlan);
ui.planMap.addEventListener('change', renderPlanner);
ui.planMapVersion.addEventListener('change', renderPlanner);
ui.memberForm?.addEventListener('submit', addMember);
ui.refreshInvitations?.addEventListener('click', refreshInvitations);
ui.refreshExpeditions.addEventListener('click', refreshDashboard); ui.inspectWorld.addEventListener('click', inspectWorld); ui.useCurrentMinute.addEventListener('click', () => { if (state.dashboard) { ui.worldMinute.value = state.dashboard.campaign_game_minute; inspectWorld(); } });
authReady.then(loadUser);

// --- v21: campaign creation + persisted map feature workbench -----------------
async function createCampaign(event) {
  event.preventDefault();
  if (!state.userId) return;
  ui.campaignCreateMessage.classList.remove('error');
  ui.campaignCreateMessage.textContent = 'Création…';
  try {
    const created = await api('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify({
        name: ui.campaignCreateName.value.trim(),
        description: ui.campaignCreateDescription.value.trim() || null,
        epoch_name: ui.campaignCreateEpoch.value.trim() || 'Day 1',
        creator_user_id: state.userId,
      }),
    });
    ui.campaignCreateForm.reset();
    ui.campaignCreateEpoch.value = 'Day 1';
    ui.campaignCreateForm.classList.add('hidden');
    ui.toggleCampaignCreate.textContent = '+ Nouvelle campagne';
    state.campaigns = await api(`/api/users/${state.userId}/dm-campaigns`);
    renderCampaigns();
    await selectCampaign(created.id);
    ui.identity.textContent = `${state.campaigns.length} campagne(s) administrée(s) comme MJ.`;
  } catch (error) {
    ui.campaignCreateMessage.classList.add('error');
    ui.campaignCreateMessage.textContent = error.message;
  }
}

function renderWorkbenchVersionOptions() {
  if (!state.dashboard || !ui.workbenchVersion) return;
  const current = Number(ui.workbenchVersion.value);
  const versions = state.dashboard.maps.flatMap(map => map.versions.map(version => ({map, version})));
  ui.workbenchVersion.innerHTML = versions.map(({map, version}) =>
    `<option value="${version.id}">${esc(map.name)} · v${version.version} · ${formatGameDate(version.effective_from_game_minute)}</option>`
  ).join('');
  if (versions.some(x => x.version.id === current)) ui.workbenchVersion.value = String(current);
  if (!versions.length) ui.workbenchMessage.textContent = 'Persiste d’abord une carte depuis l’éditeur terrain.';
}

const workbenchView = { scale: 1, panX: 0, panY: 0, centers: new Map(), dragging: false, moved: false, lastX: 0, lastY: 0 };
let workbenchHexByCoord = new Map(), indexedWorkbench = null;
const TERRAIN_COLORS = { SEA:'#1f4b70', PLAIN:'#5d7f3d', SWAMP:'#4c6351', HILL:'#7c7647', FOREST:'#315b39', DEEP_FOREST:'#203f2a', LOW_MOUNTAIN:'#77736c', MOUNTAIN:'#8f8c86', HIGH_MOUNTAIN:'#b4b2ae' };
function coordKey(q,r) { return `${q},${r}`; }
function axialDistance(a,b) { return (Math.abs(a.q-b.q)+Math.abs(a.q+a.r-b.q-b.r)+Math.abs(a.r-b.r))/2; }
function hexWorld(q, r, size=34) { return { x: 1.5*size*q, y: Math.sqrt(3)*size*(r+q/2) }; }
function polygon(ctx,cx,cy,size) { ctx.beginPath(); for(let i=0;i<6;i++){ const a=(Math.PI/180)*(60*i); const x=cx+size*Math.cos(a), y=cy+size*Math.sin(a); i?ctx.lineTo(x,y):ctx.moveTo(x,y); } ctx.closePath(); }

function resetWorkbenchView() { workbenchView.scale=1; workbenchView.panX=0; workbenchView.panY=0; }
function wbOffsetToAxial(col,row,w){const q=col-Math.floor(w.width/2), parity=q&1;return {q,r:row-Math.floor(w.height/2)-Math.floor((q+parity)/2)};}
function wbInBounds(q,r,w){const col=q+Math.floor(w.width/2),row=r+Math.floor((q+(q&1))/2)+Math.floor(w.height/2);return col>=0&&row>=0&&col<w.width&&row<w.height;}
function ensureWorkbenchHexIndex(){if(indexedWorkbench===state.mapWorkbench)return;indexedWorkbench=state.mapWorkbench;workbenchHexByCoord=new Map((indexedWorkbench?.hexes||[]).map(h=>[coordKey(h.q,h.r),h]));}
function wbOverride(q,r){ensureWorkbenchHexIndex();return workbenchHexByCoord.get(coordKey(q,r))||null;}
function wbVirtualHex(q,r){const w=state.mapWorkbench;if(!w||!wbInBounds(q,r,w))return null;return wbOverride(q,r)||{id:null,q,r,terrain_key:w.default_terrain_key||'SEA',elevation:0,visibility_score:'défaut',travel_cost:'défaut',extra_data:{}};}
function fitWorkbench() {
  const w=state.mapWorkbench; if(!w?.width||!w?.height)return;
  const a=wbOffsetToAxial(0,0,w),b=wbOffsetToAxial(w.width-1,w.height-1,w),pa=hexWorld(a.q,a.r),pb=hexWorld(b.q,b.r);
  const spanX=Math.abs(pb.x-pa.x)+90,spanY=Math.abs(pb.y-pa.y)+90,canvas=ui.mapCanvas;
  workbenchView.scale=Math.max(.0005,Math.min((canvas.clientWidth||900)/spanX,(canvas.clientHeight||620)/spanY,1.35));
  workbenchView.panX=-(pa.x+pb.x)/2*workbenchView.scale;workbenchView.panY=-(pa.y+pb.y)/2*workbenchView.scale;
}
function drawWorkbench() {
  const canvas=ui.mapCanvas,w=state.mapWorkbench;if(!canvas)return;
  const dpr=window.devicePixelRatio||1,width=Math.max(400,canvas.clientWidth||900),height=Math.max(400,canvas.clientHeight||680);
  if(canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)){canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);}
  const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#0b1015';ctx.fillRect(0,0,width,height);workbenchView.centers.clear();
  if(!w?.width){ctx.fillStyle='#8091a2';ctx.font='14px system-ui';ctx.fillText('Charge une MapVersion persistée.',24,36);return;}
  const cx0=width/2+workbenchView.panX,cy0=height/2+workbenchView.panY,size=32*workbenchView.scale,centerFor=h=>{const p=hexWorld(h.q,h.r);return{x:cx0+p.x*workbenchView.scale,y:cy0+p.y*workbenchView.scale};};
  if(size<1.2){ctx.fillStyle=TERRAIN_COLORS[w.default_terrain_key||'SEA']||'#010554';ctx.fillRect(0,0,width,height);for(const h of w.hexes){const c=centerFor(h);if(c.x<0||c.y<0||c.x>width||c.y>height)continue;ctx.fillStyle=TERRAIN_COLORS[h.terrain_key]||'#394754';ctx.fillRect(c.x-1,c.y-1,3,3);}}
  else{
    const worldLeft=(-cx0-50)/workbenchView.scale,worldRight=(width-cx0+50)/workbenchView.scale;
    let c0=Math.max(0,Math.floor(worldLeft/(1.5*34)+w.width/2)-2),c1=Math.min(w.width-1,Math.ceil(worldRight/(1.5*34)+w.width/2)+2);
    for(let col=c0;col<=c1;col++){const q=col-Math.floor(w.width/2),parity=q&1,worldTop=(-cy0-50)/workbenchView.scale,worldBottom=(height-cy0+50)/workbenchView.scale;let r0=Math.max(0,Math.floor(worldTop/(Math.sqrt(3)*34)+w.height/2+parity/2)-2),r1=Math.min(w.height-1,Math.ceil(worldBottom/(Math.sqrt(3)*34)+w.height/2+parity/2)+2);for(let row=r0;row<=r1;row++){const h=wbVirtualHex(q,row-Math.floor(w.height/2)-Math.floor((q+parity)/2));const c=centerFor(h);workbenchView.centers.set(coordKey(h.q,h.r),c);polygon(ctx,c.x,c.y,size*.96);ctx.fillStyle=TERRAIN_COLORS[h.terrain_key]||'#394754';ctx.fill();ctx.strokeStyle='#26394a';ctx.lineWidth=1;ctx.stroke();}}
  }
  // Area features live below linear features. They are semantic overlays: the
  // underlying terrain remains independent.
  for(const area of (w.areas||[])){ctx.save();ctx.globalAlpha=.28;for(const cell of area.cells||[]){const c=centerFor(cell);polygon(ctx,c.x,c.y,Math.max(2,size*.82));ctx.fillStyle=area.feature_type==='LAKE'||area.feature_type==='INLAND_SEA'?'#55aee6':'#7bbf86';ctx.fill();}ctx.restore();}

  // Multiple semantic features may share the same geometric edge (e.g. a road
  // following a river). Draw them as parallel, slightly offset strokes rather
  // than hiding one underneath the other.
  const edgeGroups=new Map();
  for(const edge of w.edges){const a=[edge.from_q,edge.from_r],b=[edge.to_q,edge.to_r],key=(a[0]<b[0]||(a[0]===b[0]&&a[1]<=b[1]))?`${a[0]},${a[1]}|${b[0]},${b[1]}`:`${b[0]},${b[1]}|${a[0]},${a[1]}`;(edgeGroups.get(key)||edgeGroups.set(key,[]).get(key)).push(edge);}
  for(const group of edgeGroups.values()){const ordered=[...group].sort((a,b)=>{const rank={RIVER:0,ROAD:1,BRIDGE:2,PASSAGE:3,TRAVERSAL:4};return (rank[a.feature_type]??9)-(rank[b.feature_type]??9)||a.feature_id-b.feature_id;});for(let i=0;i<ordered.length;i++){const edge=ordered[i],aa=centerFor({q:edge.from_q,r:edge.from_r}),bb=centerFor({q:edge.to_q,r:edge.to_r});const dx=bb.x-aa.x,dy=bb.y-aa.y,len=Math.hypot(dx,dy)||1;let offset=0;if(ordered.length>1){if(edge.feature_type==='RIVER')offset=0;else offset=(i-(ordered.length-1)/2)*Math.max(3,4*workbenchView.scale);}const ox=-dy/len*offset,oy=dx/len*offset;ctx.strokeStyle=edge.id===state.selectedEdgeId?'#ffd166':edge.feature_type==='RIVER'?'#4bb6e8':edge.feature_type==='BRIDGE'?'#e7d8bd':'#d9b26f';ctx.lineWidth=Math.max(edge.feature_type==='RIVER'?3:2,(edge.feature_type==='RIVER'?7:4)*workbenchView.scale);ctx.lineCap='round';ctx.beginPath();ctx.moveTo(aa.x+ox,aa.y+oy);ctx.lineTo(bb.x+ox,bb.y+oy);ctx.stroke();}}
  for(const poi of w.pois){const c=centerFor(poi);ctx.beginPath();ctx.arc(c.x,c.y,poi.id===state.selectedPoiId?8:6,0,Math.PI*2);ctx.fillStyle=poi.is_landmark?'#ffd166':'#ff8fab';ctx.fill();ctx.strokeStyle='#10161d';ctx.lineWidth=2;ctx.stroke();}
  for(const [index,h] of state.selectedHexes.entries()){const c=centerFor(h);polygon(ctx,c.x,c.y,Math.max(4,size*.88));ctx.strokeStyle=index===state.selectedHexes.length-1?'#7bc3ff':'#b7ddff';ctx.lineWidth=index===state.selectedHexes.length-1?4:3;ctx.stroke();}
}
function nearestWorkbenchHex(x,y){const w=state.mapWorkbench;if(!w)return null;const cx=(ui.mapCanvas.clientWidth||900)/2+workbenchView.panX,cy=(ui.mapCanvas.clientHeight||680)/2+workbenchView.panY,wx=(x-cx)/workbenchView.scale,wy=(y-cy)/workbenchView.scale,size=34,qf=(2/3*wx)/size,rf=(-1/3*wx+Math.sqrt(3)/3*wy)/size;let xq=qf,z=rf,yc=-xq-z,rx=Math.round(xq),ry=Math.round(yc),rz=Math.round(z),xd=Math.abs(rx-xq),yd=Math.abs(ry-yc),zd=Math.abs(rz-z);if(xd>yd&&xd>zd)rx=-ry-rz;else if(yd>zd)ry=-rx-rz;else rz=-rx-ry;return wbVirtualHex(rx,rz);}

function sameHex(a,b){return Boolean(a&&b&&a.q===b.q&&a.r===b.r);}
function syncPrimarySelectedHex(){state.selectedHex=state.selectedHexes.length?state.selectedHexes[state.selectedHexes.length-1]:null;}
function setHexSelection(h,{additive=false}={}){if(!h)return;if(!additive){state.selectedHexes=[h];}else{const index=state.selectedHexes.findIndex(x=>sameHex(x,h));if(index>=0)state.selectedHexes.splice(index,1);else state.selectedHexes.push(h);}syncPrimarySelectedHex();state.selectedPoiId=null;renderSelectedHex();updateEdgeSelection();drawWorkbench();}
function clearHexSelection(){state.selectedHexes=[];state.selectedHex=null;state.selectedPoiId=null;renderSelectedHex();updateEdgeSelection();drawWorkbench();}
function renderSelectedHex(){const selected=state.selectedHexes;if(!selected.length){ui.selectedHex.innerHTML='Aucun hex sélectionné.<div class="small">Clic : nouvelle sélection · Ctrl+clic : ajouter/retirer · Esc : effacer.</div>';renderPoiList();return;}if(selected.length>1){ui.selectedHex.innerHTML=`<strong>${selected.length} hex sélectionnés</strong><div class="small">${selected.map(h=>`(${h.q}, ${h.r})`).join(' · ')}</div><div class="small">Ctrl+clic ajoute/retire un hex · Esc efface la sélection.</div>`;renderPoiList();return;}const h=selected[0];const pois=(state.mapWorkbench?.pois||[]).filter(p=>p.q===h.q&&p.r===h.r);ui.selectedHex.innerHTML=`<strong>(${h.q}, ${h.r}) · ${esc(h.terrain_key)}</strong><div class="small">${h.id?`Hex #${h.id}`:'Hex par défaut'} · élévation ${h.elevation} · visibilité ${h.visibility_score} · coût ${h.travel_cost}</div><div class="small">${pois.length} POI sur cet hex.</div>`;renderPoiList();}
function renderPoiList(){const all=state.mapWorkbench?.pois||[];if(state.selectedHexes.length>1){ui.poiList.innerHTML='<div class="empty">Sélection multiple active : garde un seul hex pour gérer ses POI.</div>';return;}const h=state.selectedHexes[0];const rows=h?all.filter(p=>p.q===h.q&&p.r===h.r):all;ui.poiList.innerHTML=rows.map(p=>`<button type="button" class="feature-row ${p.id===state.selectedPoiId?'selected':''}" data-poi="${p.id}"><strong>${esc(p.name)}</strong><span>${esc(p.kind||'POI')} · identité POI #${p.feature_id} · row #${p.id}${p.is_landmark?' · landmark':''}${p.is_hub?' · HUB':''}</span></button>`).join('')||(h?'<div class="empty">Aucun POI sur cet hex.</div>':'<div class="empty">Aucun POI sur cette carte.</div>');ui.poiList.querySelectorAll('[data-poi]').forEach(el=>el.addEventListener('click',()=>selectPoi(Number(el.dataset.poi))));}
function selectPoi(id){const p=state.mapWorkbench?.pois.find(x=>x.id===id);if(!p)return;const h=wbVirtualHex(p.q,p.r);state.selectedPoiId=id;if(h){state.selectedHexes=[h];syncPrimarySelectedHex();}ui.poiId.value=p.id;ui.poiName.value=p.name;ui.poiKind.value=p.kind||'';ui.poiDescription.value=p.dm_description||'';ui.poiLandmark.checked=p.is_landmark;ui.poiHub.checked=Boolean(p.is_hub);renderSelectedHex();updateEdgeSelection();drawWorkbench();}
function clearPoiForm(){state.selectedPoiId=null;ui.poiId.value='';ui.poiName.value='';ui.poiKind.value='';ui.poiDescription.value='';ui.poiLandmark.checked=false;ui.poiHub.checked=false;renderPoiList();drawWorkbench();}
function renderEdgeList(){const edges=state.mapWorkbench?.edges||[];const groups=new Map();for(const e of edges){const key=`${e.feature_type}:${e.feature_id}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e);}ui.edgeList.innerHTML=[...groups.values()].map(group=>{group.sort((a,b)=>(a.segment_index??0)-(b.segment_index??0));const first=group[0],selected=group.some(e=>e.id===state.selectedEdgeId);return `<button type="button" class="feature-row ${selected?'selected':''}" data-edge="${first.id}"><strong>${esc(first.name||first.feature_type)}</strong><span>${first.feature_type} #${first.feature_id} · ${group.length} segment(s)</span></button>`;}).join('')||'<div class="empty">Aucune feature linéaire.</div>';ui.edgeList.querySelectorAll('[data-edge]').forEach(el=>el.addEventListener('click',()=>{state.selectedEdgeId=Number(el.dataset.edge);renderEdgeList();drawWorkbench();}));}
function renderAreaList(){const areas=state.mapWorkbench?.areas||[];ui.areaList.innerHTML=areas.map(a=>`<div class="feature-row"><strong>${esc(a.name||a.feature_type)}</strong><span>${a.feature_type} #${a.feature_id} · ${(a.cells||[]).length} hex</span></div>`).join('')||'<div class="empty">Aucune zone sémantique.</div>';}
function updateEdgeSelection(){const selected=state.selectedHexes;if(!selected.length){ui.edgeSelection.textContent='Sélectionne au moins deux waypoints avec Ctrl+clic.';return;}if(selected.length===1){ui.edgeSelection.textContent=`Départ (${selected[0].q}, ${selected[0].r}) · ajoute un waypoint avec Ctrl+clic.`;return;}ui.edgeSelection.textContent=`${selected.length} waypoint(s) ordonnés · ${selected.map(h=>`(${h.q},${h.r})`).join(' → ')}`;}

async function loadMapWorkbench({fit=true}={}){
  if(!state.campaignId||!state.userId||!ui.workbenchVersion.value)return;
  ui.workbenchMessage.classList.remove('error');ui.workbenchMessage.textContent='Chargement…';
  try{state.mapWorkbench=await api(`/api/campaigns/${state.campaignId}/dm-map-workbench?user_id=${state.userId}&map_version_id=${Number(ui.workbenchVersion.value)}`);state.selectedHex=null;state.selectedHexes=[];state.selectedPoiId=null;state.selectedEdgeId=null;if(fit){resetWorkbenchView();requestAnimationFrame(()=>{fitWorkbench();drawWorkbench();});}else drawWorkbench();renderSelectedHex();renderPoiList();renderEdgeList();renderAreaList();updateEdgeSelection();ui.poiEventMinute.value=state.dashboard?.campaign_game_minute??0;ui.edgeEventMinute.value=state.dashboard?.campaign_game_minute??0;ui.workbenchMessage.textContent=`${(state.mapWorkbench.width*state.mapWorkbench.height).toLocaleString("fr-FR")} hex logiques · ${state.mapWorkbench.hexes.length} matérialisés · ${state.mapWorkbench.pois.length} POI · ${state.mapWorkbench.edges.length} features`;}
  catch(error){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=error.message;}
}
async function savePoi(event){
  event.preventDefault();
  if(state.selectedHexes.length!==1)return void(ui.workbenchMessage.textContent='Sélectionne exactement un hex pour créer ou modifier un POI.');
  const payload={name:ui.poiName.value.trim(),kind:ui.poiKind.value.trim()||null,dm_description:ui.poiDescription.value.trim()||null,is_landmark:ui.poiLandmark.checked,is_hub:ui.poiHub.checked};
  try{
    if(state.selectedPoiId){
      const previous=state.mapWorkbench?.pois.find(p=>p.id===state.selectedPoiId);
      const result=await api(`/api/campaigns/${state.campaignId}/dm-pois/${state.selectedPoiId}?user_id=${state.userId}`,{method:'PATCH',body:JSON.stringify(payload)});
      if(previous)state.poiUndoStack.push({type:'update',poiId:result.id,before:{name:previous.name,kind:previous.kind,dm_description:previous.dm_description,is_landmark:previous.is_landmark,is_hub:previous.is_hub},after:payload});
    }else{
      const q=state.selectedHex.q,r=state.selectedHex.r;
      const result=await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/pois?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({...payload,q,r})});
      state.poiUndoStack.push({type:'create',poiId:result.id,featureId:result.feature_id,q,r,payload});
    }
    state.poiRedoStack=[];if(state.poiUndoStack.length>100)state.poiUndoStack.shift();
    await refreshDashboard();await loadMapWorkbench({fit:false});clearPoiForm();ui.workbenchMessage.textContent='POI enregistré. Ctrl+Z pour annuler.';
  }catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}
}

async function undoPoi(){
  const cmd=state.poiUndoStack.pop();if(!cmd)return false;
  if(cmd.type==='create')await api(`/api/campaigns/${state.campaignId}/dm-pois/${cmd.poiId}?user_id=${state.userId}`,{method:'DELETE'});
  else if(cmd.type==='update')await api(`/api/campaigns/${state.campaignId}/dm-pois/${cmd.poiId}?user_id=${state.userId}`,{method:'PATCH',body:JSON.stringify(cmd.before)});
  state.poiRedoStack.push(cmd);await refreshDashboard();await loadMapWorkbench({fit:false});return true;
}
async function redoPoi(){
  const cmd=state.poiRedoStack.pop();if(!cmd)return false;
  if(cmd.type==='create'){
    const result=await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/pois?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({...cmd.payload,q:cmd.q,r:cmd.r,feature_id:cmd.featureId})});cmd.poiId=result.id;
  }else if(cmd.type==='update')await api(`/api/campaigns/${state.campaignId}/dm-pois/${cmd.poiId}?user_id=${state.userId}`,{method:'PATCH',body:JSON.stringify(cmd.after)});
  state.poiUndoStack.push(cmd);await refreshDashboard();await loadMapWorkbench({fit:false});return true;
}
function parseJSONField(input){try{return JSON.parse(input.value||'{}');}catch(_){throw new Error('Payload JSON invalide');}}
async function savePoiEvent(event){event.preventDefault();if(!state.selectedPoiId)return void(ui.workbenchMessage.textContent='Sélectionne un POI.');try{await api(`/api/campaigns/${state.campaignId}/dm-pois/${state.selectedPoiId}/world-events?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({game_minute:Number(ui.poiEventMinute.value),event_type:ui.poiEventType.value,payload:parseJSONField(ui.poiEventPayload),dm_note:ui.poiEventNote.value.trim()||null})});await refreshDashboard();ui.workbenchMessage.textContent='WorldEvent POI ajouté à la timeline.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}
async function saveEdge(event){
  event.preventDefault();
  const selected=state.selectedHexes,type=ui.edgeType.value;
  if(selected.length<2)return void(ui.workbenchMessage.textContent='Sélectionne au moins deux hex/waypoints avec Ctrl+clic.');
  if(!['ROAD','RIVER'].includes(type)){
    if(selected.length!==2||axialDistance(selected[0],selected[1])!==1)return void(ui.workbenchMessage.textContent=`${type} exige exactement deux hex adjacents.`);
  }
  try{
    const created=await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/linear-features?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({waypoints:selected.map(h=>({q:h.q,r:h.r})),feature_type:type,name:ui.edgeName.value.trim()||null,extra_data:{}})});
    ui.edgeName.value='';await refreshDashboard();await loadMapWorkbench({fit:false});ui.workbenchMessage.textContent=`${type} créé : ${created.length} segment(s).`;
  }catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}
}
async function saveArea(event){
  event.preventDefault();if(!state.selectedHexes.length)return void(ui.workbenchMessage.textContent='Sélectionne au moins un hex pour créer une zone.');
  try{const area=await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/area-features?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({cells:state.selectedHexes.map(h=>({q:h.q,r:h.r})),feature_type:ui.areaType.value,name:ui.areaName.value.trim()||null,extra_data:{}})});ui.areaName.value='';await refreshDashboard();await loadMapWorkbench({fit:false});ui.workbenchMessage.textContent=`${area.feature_type} #${area.feature_id} créé sur ${area.cells.length} hex.`;}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}
}
async function saveEdgeEvent(event){event.preventDefault();if(!state.selectedEdgeId)return void(ui.workbenchMessage.textContent='Sélectionne une feature dans la liste.');try{await api(`/api/campaigns/${state.campaignId}/dm-map-edges/${state.selectedEdgeId}/world-events?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({game_minute:Number(ui.edgeEventMinute.value),event_type:ui.edgeEventType.value,payload:parseJSONField(ui.edgeEventPayload),dm_note:ui.edgeEventNote.value.trim()||null})});await refreshDashboard();ui.workbenchMessage.textContent='WorldEvent de feature ajouté à la timeline.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}

ui.toggleCampaignCreate?.addEventListener('click',()=>{const hidden=ui.campaignCreateForm.classList.toggle('hidden');ui.toggleCampaignCreate.textContent=hidden?'+ Nouvelle campagne':'Masquer le formulaire';});
ui.cancelCampaignCreate?.addEventListener('click',()=>{ui.campaignCreateForm.classList.add('hidden');ui.toggleCampaignCreate.textContent='+ Nouvelle campagne';});
ui.campaignCreateForm?.addEventListener('submit',createCampaign);
ui.loadWorkbench?.addEventListener('click',()=>loadMapWorkbench());
ui.workbenchVersion?.addEventListener('change',()=>loadMapWorkbench());
ui.newPoi?.addEventListener('click',clearPoiForm);ui.poiForm?.addEventListener('submit',savePoi);ui.poiEventForm?.addEventListener('submit',savePoiEvent);
ui.edgeForm?.addEventListener('submit',saveEdge);ui.edgeEventForm?.addEventListener('submit',saveEdgeEvent);ui.areaForm?.addEventListener('submit',saveArea);

window.addEventListener('keydown',async e=>{const target=e.target;if(target instanceof HTMLElement&&(target.matches('input, textarea, select')||target.isContentEditable))return;const mod=e.ctrlKey||e.metaKey;if(mod&&e.key.toLowerCase()==='z'){if(!ui.workbenchMessage)return;e.preventDefault();try{const changed=e.shiftKey?await redoPoi():await undoPoi();ui.workbenchMessage.textContent=changed?(e.shiftKey?'POI rétabli.':'Modification POI annulée.'):(e.shiftKey?'Rien à rétablir.':'Rien à annuler côté POI.');}catch(err){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=err.message;}return;}if(e.key!=='Escape')return;if(!state.selectedHexes.length)return;clearHexSelection();});

if(ui.mapCanvas){ui.mapCanvas.addEventListener('mousedown',e=>{workbenchView.dragging=true;workbenchView.moved=false;workbenchView.lastX=e.clientX;workbenchView.lastY=e.clientY;});window.addEventListener('mouseup',()=>workbenchView.dragging=false);ui.mapCanvas.addEventListener('mousemove',e=>{if(!workbenchView.dragging)return;const dx=e.clientX-workbenchView.lastX,dy=e.clientY-workbenchView.lastY;if(Math.abs(dx)+Math.abs(dy)>2)workbenchView.moved=true;workbenchView.panX+=dx;workbenchView.panY+=dy;workbenchView.lastX=e.clientX;workbenchView.lastY=e.clientY;drawWorkbench();});ui.mapCanvas.addEventListener('click',e=>{if(workbenchView.moved)return;const rect=ui.mapCanvas.getBoundingClientRect(),h=nearestWorkbenchHex(e.clientX-rect.left,e.clientY-rect.top);if(!h)return;setHexSelection(h,{additive:e.ctrlKey||e.metaKey});});ui.mapCanvas.addEventListener('wheel',e=>{e.preventDefault();workbenchView.scale=Math.max(.0005,Math.min(3,workbenchView.scale*(e.deltaY<0?1.1:.9)));drawWorkbench();},{passive:false});new ResizeObserver(()=>drawWorkbench()).observe(ui.mapCanvas);}
