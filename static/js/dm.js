const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const ui = {
  userId: $('#user-id'), loadUser: $('#load-user'), identity: $('#identity-message'), error: $('#error'),
  campaigns: $('#campaigns'), campaignCount: $('#campaign-count'), campaignMinute: $('#campaign-minute'), campaignDay: $('#campaign-day'),
  campaignTitle: $('#campaign-title'), campaignDescription: $('#campaign-description'), campaignActions: $('#campaign-actions'), stats: $('#stats'),
  statExpeditions: $('#stat-expeditions'), statCharacters: $('#stat-characters'), statMaps: $('#stat-maps'), statEvents: $('#stat-events'), empty: $('#empty'),
  overviewExpeditions: $('#overview-expeditions'), overviewEvents: $('#overview-events'), overviewMaps: $('#overview-maps'),
  expeditionList: $('#expedition-list'), expeditionDetail: $('#expedition-detail'), refreshExpeditions: $('#refresh-expeditions'),
  togglePlanner: $('#toggle-planner'), plannerForm: $('#expedition-planner-form'), planName: $('#plan-name'), planMinute: $('#plan-minute'), planMapVersion: $('#plan-map-version'), planTransport: $('#plan-transport'), planQ: $('#plan-q'), planR: $('#plan-r'), planCharacters: $('#plan-characters'), planStartNow: $('#plan-start-now'), plannerMessage: $('#planner-message'),
  worldMinute: $('#world-minute'), inspectWorld: $('#inspect-world'), useCurrentMinute: $('#use-current-minute'), worldSummary: $('#world-summary'), worldGlobal: $('#world-global'), worldTargets: $('#world-targets'),
  mapsList: $('#maps-list'), charactersList: $('#characters-list'), timelineFrame: $('#timeline-frame'), timelineOpen: $('#timeline-open'),
  mapEditorOpen: $('#map-editor-open'), membersList: $('#members-list'), memberForm: $('#member-form'), memberUserId: $('#member-user-id'), memberRole: $('#member-role'), memberMessage: $('#member-message'), characterForm: $('#character-form'), characterOwner: $('#character-owner'), characterName: $('#character-name'), characterRace: $('#character-race'), characterClass: $('#character-class'), characterLevel: $('#character-level'), characterMinute: $('#character-minute'), characterDescription: $('#character-description'), characterMessage: $('#character-message'),
};

const state = { userId: null, campaigns: [], campaignId: null, dashboard: null, expeditionId: null, tab: 'overview', mapWorkbench: null, selectedHex: null, selectedPoiId: null, selectedEdgeId: null, edgeFrom: null };

Object.assign(ui, {
  toggleCampaignCreate: $('#toggle-campaign-create'), campaignCreateForm: $('#campaign-create-form'), campaignCreateName: $('#campaign-create-name'), campaignCreateEpoch: $('#campaign-create-epoch'), campaignCreateDescription: $('#campaign-create-description'), campaignCreateMessage: $('#campaign-create-message'), cancelCampaignCreate: $('#cancel-campaign-create'),
  workbenchVersion: $('#workbench-version'), loadWorkbench: $('#load-workbench'), workbenchMessage: $('#workbench-message'), mapCanvas: $('#dm-map-canvas'), selectedHex: $('#selected-hex'),
  newPoi: $('#new-poi'), poiList: $('#poi-list'), poiForm: $('#poi-form'), poiId: $('#poi-id'), poiName: $('#poi-name'), poiKind: $('#poi-kind'), poiLandmark: $('#poi-landmark'), poiDescription: $('#poi-description'),
  poiEventForm: $('#poi-event-form'), poiEventMinute: $('#poi-event-minute'), poiEventType: $('#poi-event-type'), poiEventPayload: $('#poi-event-payload'), poiEventNote: $('#poi-event-note'),
  edgeUseSelected: $('#edge-use-selected'), edgeSelection: $('#edge-selection'), edgeForm: $('#edge-form'), edgeType: $('#edge-type'), edgeName: $('#edge-name'), edgeList: $('#edge-list'),
  edgeEventForm: $('#edge-event-form'), edgeEventMinute: $('#edge-event-minute'), edgeEventType: $('#edge-event-type'), edgeEventPayload: $('#edge-event-payload'), edgeEventNote: $('#edge-event-note'),
});

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); } catch (_) {}
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function esc(v) { return String(v ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function qs(key, value) { const u = new URL(location.href); value == null ? u.searchParams.delete(key) : u.searchParams.set(key, value); history.replaceState(null, '', u); }
function dayMinute(minute) { const day = Math.floor(minute / 1440) + 1; const rest = minute % 1440; const h = Math.floor(rest / 60); const m = rest % 60; return `Jour ${day} · ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`; }
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
  return `<div class="event-row"><div class="event-top"><span class="event-type">${esc(event.event_type)}</span><span>m.${event.game_minute}</span></div><div class="small">${target}${event.expedition_id ? ` · expedition #${event.expedition_id}` : ''}</div>${Object.keys(event.payload || {}).length ? `<div class="event-payload">${esc(JSON.stringify(event.payload))}</div>` : ''}${event.dm_note ? `<div class="small">MJ: ${esc(event.dm_note)}</div>` : ''}</div>`;
}

function renderOverview() {
  const d = state.dashboard;
  const active = d.expeditions.filter(e => e.status === 'ACTIVE');
  ui.overviewExpeditions.innerHTML = active.map(e => `<div class="mini-row"><div class="record-head"><strong>${esc(e.name)}</strong><span class="${statusClass(e.status)}">${e.status}</span></div><div class="small">m.${e.current_game_minute} · ${e.current_q == null ? 'non positionnée' : `(${e.current_q}, ${e.current_r})`} · ${e.participants.length} perso.</div></div>`).join('') || '<div class="empty">Aucune expédition active.</div>';
  ui.overviewEvents.innerHTML = d.recent_events.slice(0, 6).map(renderEvent).join('') || '<div class="empty">Aucun WorldEvent.</div>';
  ui.overviewMaps.innerHTML = d.maps.map(m => { const latest = m.versions[0]; return `<div class="map-chip"><strong>${esc(m.name)}</strong><div class="small">${m.versions.length} version(s)</div>${latest ? `<div class="small">Dernière: v${latest.version} · ${latest.hex_count} hex · m.${latest.effective_from_game_minute}</div>` : '<div class="small">Aucune version</div>'}</div>`; }).join('') || '<div class="empty">Aucune carte persistée.</div>';
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

  const versions = d.maps.flatMap(map => map.versions.map(version => ({ map, version })));
  ui.planMapVersion.innerHTML = versions.map(({map, version}) =>
    `<option value="${version.id}">${esc(map.name)} · v${version.version} · m.${version.effective_from_game_minute}</option>`
  ).join('');

  ui.planCharacters.innerHTML = d.characters.map(character => {
    const unavailable = assigned.has(character.id) || character.status !== 'ACTIVE';
    const reason = assigned.has(character.id) ? 'déjà en expédition' : character.status !== 'ACTIVE' ? character.status : `m.${character.current_game_minute}`;
    return `<label class="character-pick ${unavailable ? 'unavailable' : ''}"><input type="checkbox" value="${character.id}" ${unavailable ? 'disabled' : ''}><span><strong>${esc(character.name)}</strong><span class="small">${esc(reason)}</span></span></label>`;
  }).join('') || '<div class="empty">Aucun personnage disponible.</div>';

  if (!ui.planName.value) ui.planMinute.value = d.campaign_game_minute;
  if (!versions.length) {
    ui.plannerMessage.textContent = 'Aucune MapVersion persistée : crée d’abord un snapshot depuis l’éditeur.';
  } else if (!ui.plannerMessage.classList.contains('error')) {
    ui.plannerMessage.textContent = '';
  }
}

async function createExpeditionPlan(event) {
  event.preventDefault();
  if (!state.dashboard || !state.campaignId || !state.userId) return;
  const characterIds = [...ui.planCharacters.querySelectorAll('input[type="checkbox"]:checked')].map(input => Number(input.value));
  ui.plannerMessage.classList.remove('error');
  ui.plannerMessage.textContent = 'Création…';
  const payload = {
    name: ui.planName.value.trim(),
    start_game_minute: Number(ui.planMinute.value),
    character_ids: characterIds,
    map_version_id: Number(ui.planMapVersion.value),
    q: Number(ui.planQ.value),
    r: Number(ui.planR.value),
    transport_key: ui.planTransport.value || null,
    start_now: ui.planStartNow.checked,
  };
  try {
    const created = await api(`/api/campaigns/${state.campaignId}/dm-expeditions?user_id=${state.userId}`, { method: 'POST', body: JSON.stringify(payload) });
    state.expeditionId = created.expedition_id;
    ui.planName.value = '';
    await refreshDashboard();
    ui.plannerMessage.classList.remove('error');
    ui.plannerMessage.textContent = `Expédition #${created.expedition_id} créée (${created.status}).`;
  } catch (error) {
    ui.plannerMessage.classList.add('error');
    ui.plannerMessage.textContent = error.message;
  }
}

function renderExpeditions() {
  const d = state.dashboard;
  ui.expeditionList.innerHTML = d.expeditions.map(e => `<div class="record ${e.id === state.expeditionId ? 'selected' : ''}" data-expedition="${e.id}"><div class="record-head"><strong>${esc(e.name)}</strong><span class="${statusClass(e.status)}">${e.status}</span></div><div class="record-meta"><span>#${e.id}</span><span>m.${e.current_game_minute}</span><span>${e.current_q == null ? 'sans position' : `(${e.current_q}, ${e.current_r})`}</span><span>${e.participants.length} participant(s)</span></div></div>`).join('') || '<div class="empty">Aucune expédition.</div>';
  $$('[data-expedition]').forEach(el => el.addEventListener('click', () => { state.expeditionId = Number(el.dataset.expedition); renderExpeditions(); renderExpeditionDetail(); }));
  renderExpeditionDetail();
}

function renderExpeditionDetail() {
  const e = state.dashboard?.expeditions.find(x => x.id === state.expeditionId);
  if (!e) { ui.expeditionDetail.innerHTML = '<p class="muted">Sélectionne une expédition.</p>'; return; }
  const map = state.dashboard.maps.flatMap(m => m.versions.map(v => ({map:m, version:v}))).find(x => x.version.id === e.current_map_version_id);
  const canStart = e.status === 'PLANNING'; const canReturn = e.status === 'ACTIVE';
  ui.expeditionDetail.innerHTML = `<div class="eyebrow">Expédition #${e.id}</div><h3>${esc(e.name)}</h3><span class="${statusClass(e.status)}">${e.status}</span>
    <div class="detail-section"><div class="small">Départ</div><strong>m.${e.start_game_minute}</strong><div class="small">Horloge actuelle</div><strong>m.${e.current_game_minute} · ${dayMinute(e.current_game_minute)}</strong></div>
    <div class="detail-section"><div class="small">Position</div><strong>${e.current_q == null ? 'Non positionnée' : `(${e.current_q}, ${e.current_r})`}</strong><div class="small">Carte</div><strong>${map ? `${esc(map.map.name)} · v${map.version.version}` : (e.current_map_version_id ? `MapVersion #${e.current_map_version_id}` : '—')}</strong><div class="small">Météo / transport</div><strong>${esc(e.weather_key || '—')} / ${esc(e.transport_key || '—')}</strong></div>
    <div class="detail-section"><strong>Participants</strong>${e.participants.map(p => `<div class="participant"><span>${esc(p.character_name)} <span class="small">#${p.character_id}</span></span><span>${p.left_game_minute == null ? 'présent' : `sorti m.${p.left_game_minute}`}</span></div>`).join('') || '<div class="empty">Aucun participant.</div>'}</div>
    <div class="detail-actions">${canStart ? '<button id="action-start">Démarrer</button>' : ''}${canReturn ? '<button id="action-return">Retour au hub</button>' : ''}${e.current_map_version_id && e.current_q != null ? `<a class="button-link" href="/player.html?expedition=${e.id}">Voir carte joueur</a>` : ''}<a class="button-link" href="/timeline.html?campaign_id=${state.campaignId}">Timeline</a></div>
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
  ui.mapsList.innerHTML = state.dashboard.maps.map(m => `<article class="map-card"><div class="map-title"><div><strong>${esc(m.name)}</strong><div class="small">Map #${m.id}${m.description ? ` · ${esc(m.description)}` : ''}</div></div><span class="badge">${m.versions.length} version(s)</span></div><table class="version-table"><thead><tr><th>Version</th><th>Effective</th><th>Taille</th><th>Hex</th><th>POI</th><th>Edges</th><th></th></tr></thead><tbody>${m.versions.map(v => `<tr><td>v${v.version}${v.name ? ` · ${esc(v.name)}` : ''} <span class="small">#${v.id}</span></td><td>m.${v.effective_from_game_minute}</td><td>${v.width}×${v.height} · ${v.hex_size}px</td><td>${v.hex_count}</td><td>${v.poi_count}</td><td>${v.edge_count}</td><td><a class="button-link compact" href="/?user=${state.userId}&campaign=${state.campaignId}&map=${m.id}&version=${v.id}">Éditer → nouvelle version</a></td></tr>`).join('')}</tbody></table></article>`).join('') || '<div class="empty">Aucune carte persistée pour cette campagne.</div>';
  renderWorkbenchVersionOptions();
}

function renderCharacters() {
  const d = state.dashboard;
  ui.membersList.innerHTML = d.members.map(m => `<div class="member-row"><div><strong>${esc(m.username)}</strong><span class="small">${esc(m.email)} · user #${m.user_id}</span></div><span class="badge">${m.role}</span></div>`).join('') || '<div class="empty">Aucun membre.</div>';
  ui.characterOwner.innerHTML = d.members.map(m => `<option value="${m.user_id}">${esc(m.username)} · ${m.role} · #${m.user_id}</option>`).join('');
  if (!ui.characterName.value) ui.characterMinute.value = d.campaign_game_minute;
  ui.charactersList.innerHTML = d.characters.map(c => { const owner=d.members.find(m=>m.user_id===c.owner_user_id); return `<article class="character-card"><div class="record-head"><h3>${esc(c.name)}</h3><span class="status status-${c.status}">${c.status}</span></div><div class="small">#${c.id} · ${owner ? esc(owner.username) : `owner #${c.owner_user_id}`}</div><div>${esc(c.race || '—')} · ${esc(c.character_class || '—')}${c.level ? ` niv.${c.level}` : ''}</div><div class="small">Horloge: m.${c.current_game_minute} · ${dayMinute(c.current_game_minute)}</div></article>`; }).join('') || '<div class="empty">Aucun personnage.</div>';
}

async function addMember(event) {
  event.preventDefault();
  ui.memberMessage.classList.remove('error'); ui.memberMessage.textContent = 'Ajout…';
  try {
    await api(`/api/campaigns/${state.campaignId}/dm-members?user_id=${state.userId}`, {method:'POST', body:JSON.stringify({user_id:Number(ui.memberUserId.value), role:ui.memberRole.value})});
    ui.memberUserId.value=''; await refreshDashboard(); ui.memberMessage.textContent='Membre ajouté.';
  } catch(e) { ui.memberMessage.classList.add('error'); ui.memberMessage.textContent=e.message; }
}

async function createCharacter(event) {
  event.preventDefault();
  ui.characterMessage.classList.remove('error'); ui.characterMessage.textContent='Création…';
  const level = ui.characterLevel.value ? Number(ui.characterLevel.value) : null;
  const payload={owner_user_id:Number(ui.characterOwner.value),name:ui.characterName.value.trim(),race:ui.characterRace.value.trim()||null,character_class:ui.characterClass.value.trim()||null,level,description:ui.characterDescription.value.trim()||null,current_game_minute:Number(ui.characterMinute.value)};
  try {
    const c=await api(`/api/campaigns/${state.campaignId}/dm-characters?user_id=${state.userId}`,{method:'POST',body:JSON.stringify(payload)});
    ui.characterName.value='';ui.characterRace.value='';ui.characterClass.value='';ui.characterDescription.value='';await refreshDashboard();ui.characterMessage.textContent=`${c.name} créé (#${c.id}).`;
  } catch(e) { ui.characterMessage.classList.add('error'); ui.characterMessage.textContent=e.message; }
}

async function inspectWorld() {
  if (!state.dashboard) return;
  const minute = Number(ui.worldMinute.value); if (!Number.isFinite(minute) || minute < 0) return;
  ui.worldSummary.innerHTML = '<p class="muted">Résolution…</p>';
  try {
    const w = await api(`/api/campaigns/${state.campaignId}/world-state?game_minute=${minute}`);
    ui.worldSummary.dataset.loaded = '1';
    ui.worldSummary.innerHTML = `<div class="eyebrow">World Truth @ minute ${w.game_minute}</div><strong>${w.weather_key ? `Météo : ${esc(w.weather_key)}` : 'Aucune météo globale résolue'}</strong><div class="small">${dayMinute(w.game_minute)} · ${w.latest_global_events.length} global · ${w.latest_target_events.length} ciblé(s)</div>`;
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

function renderDashboard() {
  const d = state.dashboard;
  ui.empty.classList.add('hidden'); ui.stats.classList.remove('hidden');
  $$('[data-panel]').forEach(p => p.classList.toggle('hidden', p.dataset.panel !== state.tab));
  ui.campaignTitle.textContent = d.campaign.name; ui.campaignDescription.textContent = d.campaign.description || 'Aucune description.';
  ui.campaignMinute.textContent = d.campaign_game_minute; ui.campaignDay.textContent = `${d.campaign.epoch_name} · ${dayMinute(d.campaign_game_minute)}`;
  ui.statExpeditions.textContent = d.active_expedition_count; ui.statCharacters.textContent = d.character_count; ui.statMaps.textContent = d.map_count; ui.statEvents.textContent = d.recent_events.length;
  ui.campaignActions.innerHTML = `<a class="button-link" href="/timeline.html?campaign_id=${d.campaign.id}">Timeline</a><a class="button-link" href="/?user=${state.userId}&campaign=${d.campaign.id}">Map editor</a><a class="button-link" href="/dashboard.html?user=${state.userId}&campaign=${d.campaign.id}">Vue joueur</a>`;
  if (ui.mapEditorOpen) ui.mapEditorOpen.href = `/?user=${state.userId}&campaign=${d.campaign.id}`;
  ui.worldMinute.value = d.campaign_game_minute; delete ui.worldSummary.dataset.loaded;
  if (!state.expeditionId || !d.expeditions.some(e => e.id === state.expeditionId)) state.expeditionId = d.expeditions.find(e => e.status === 'ACTIVE')?.id || d.expeditions[0]?.id || null;
  renderOverview(); renderPlanner(); renderExpeditions(); renderMaps(); renderCharacters(); if (state.tab === 'timeline') loadTimeline();
}

async function refreshDashboard() {
  if (!state.campaignId || !state.userId) return;
  state.dashboard = await api(`/api/campaigns/${state.campaignId}/dm-dashboard?user_id=${state.userId}`);
  renderDashboard();
}

async function selectCampaign(id) {
  state.campaignId = id; qs('campaign', id); renderCampaigns(); ui.error.textContent = '';
  try { await refreshDashboard(); }
  catch (e) { state.dashboard = null; ui.error.textContent = e.message; }
}

async function loadUser() {
  const userId = Number(ui.userId.value); if (!userId) return;
  state.userId = userId; qs('user', userId); ui.error.textContent = ''; ui.identity.textContent = 'Chargement…';
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

ui.loadUser.addEventListener('click', loadUser); ui.userId.addEventListener('keydown', e => { if (e.key === 'Enter') loadUser(); });
$$('.tab').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
$$('[data-jump]').forEach(b => b.addEventListener('click', () => setTab(b.dataset.jump)));

ui.togglePlanner.addEventListener('click', () => {
  const hidden = ui.plannerForm.classList.toggle('hidden');
  ui.togglePlanner.textContent = hidden ? 'Afficher le planner' : 'Masquer le planner';
  if (!hidden) renderPlanner();
});
ui.plannerForm.addEventListener('submit', createExpeditionPlan);
ui.memberForm?.addEventListener('submit', addMember);
ui.characterForm?.addEventListener('submit', createCharacter);
ui.refreshExpeditions.addEventListener('click', refreshDashboard); ui.inspectWorld.addEventListener('click', inspectWorld); ui.useCurrentMinute.addEventListener('click', () => { if (state.dashboard) { ui.worldMinute.value = state.dashboard.campaign_game_minute; inspectWorld(); } });
const initialUser = Number(new URL(location.href).searchParams.get('user')); if (initialUser) ui.userId.value = initialUser;
loadUser();

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
    `<option value="${version.id}">${esc(map.name)} · v${version.version} · m.${version.effective_from_game_minute}</option>`
  ).join('');
  if (versions.some(x => x.version.id === current)) ui.workbenchVersion.value = String(current);
  if (!versions.length) ui.workbenchMessage.textContent = 'Persiste d’abord une carte depuis l’éditeur terrain.';
}

const workbenchView = { scale: 1, panX: 0, panY: 0, centers: new Map(), dragging: false, moved: false, lastX: 0, lastY: 0 };
const TERRAIN_COLORS = { SEA:'#1f4b70', PLAIN:'#5d7f3d', SWAMP:'#4c6351', HILL:'#7c7647', FOREST:'#315b39', DEEP_FOREST:'#203f2a', LOW_MOUNTAIN:'#77736c', MOUNTAIN:'#8f8c86', HIGH_MOUNTAIN:'#b4b2ae' };
function coordKey(q,r) { return `${q},${r}`; }
function axialDistance(a,b) { return (Math.abs(a.q-b.q)+Math.abs(a.q+a.r-b.q-b.r)+Math.abs(a.r-b.r))/2; }
function hexWorld(q, r, size=34) { return { x: Math.sqrt(3)*size*(q+r/2), y: 1.5*size*r }; }
function polygon(ctx,cx,cy,size) { ctx.beginPath(); for(let i=0;i<6;i++){ const a=(Math.PI/180)*(60*i-30); const x=cx+size*Math.cos(a), y=cy+size*Math.sin(a); i?ctx.lineTo(x,y):ctx.moveTo(x,y); } ctx.closePath(); }

function resetWorkbenchView() { workbenchView.scale=1; workbenchView.panX=0; workbenchView.panY=0; }
function fitWorkbench() {
  const w=state.mapWorkbench; if(!w?.hexes.length) return;
  const pts=w.hexes.map(h=>hexWorld(h.q,h.r));
  const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y); const spanX=Math.max(...xs)-Math.min(...xs)+90, spanY=Math.max(...ys)-Math.min(...ys)+90;
  const canvas=ui.mapCanvas; workbenchView.scale=Math.min((canvas.clientWidth||900)/spanX,(canvas.clientHeight||620)/spanY,1.35);
  const midX=(Math.min(...xs)+Math.max(...xs))/2, midY=(Math.min(...ys)+Math.max(...ys))/2;
  workbenchView.panX=-midX*workbenchView.scale; workbenchView.panY=-midY*workbenchView.scale;
}
function drawWorkbench() {
  const canvas=ui.mapCanvas, w=state.mapWorkbench; if(!canvas) return;
  const dpr=window.devicePixelRatio||1, width=Math.max(400,canvas.clientWidth||900), height=Math.max(400,canvas.clientHeight||680);
  if(canvas.width!==Math.round(width*dpr)||canvas.height!==Math.round(height*dpr)){canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);}
  const ctx=canvas.getContext('2d'); ctx.setTransform(dpr,0,0,dpr,0,0); ctx.fillStyle='#0b1015';ctx.fillRect(0,0,width,height); workbenchView.centers.clear();
  if(!w?.hexes.length){ctx.fillStyle='#8091a2';ctx.font='14px system-ui';ctx.fillText('Charge une MapVersion persistée.',24,36);return;}
  const cx0=width/2+workbenchView.panX, cy0=height/2+workbenchView.panY, size=32*workbenchView.scale;
  const centerFor=h=>{const p=hexWorld(h.q,h.r);return{x:cx0+p.x*workbenchView.scale,y:cy0+p.y*workbenchView.scale};};
  for(const h of w.hexes){const c=centerFor(h);workbenchView.centers.set(coordKey(h.q,h.r),c);polygon(ctx,c.x,c.y,size*.96);ctx.fillStyle=TERRAIN_COLORS[h.terrain_key]||'#394754';ctx.fill();ctx.strokeStyle='#26394a';ctx.lineWidth=1;ctx.stroke();}
  for(const edge of w.edges){const a=workbenchView.centers.get(coordKey(edge.from_q,edge.from_r)),b=workbenchView.centers.get(coordKey(edge.to_q,edge.to_r));if(!a||!b)continue;ctx.strokeStyle=edge.id===state.selectedEdgeId?'#ffd166':edge.feature_type==='BRIDGE'?'#d7c5a0':'#d9b26f';ctx.lineWidth=Math.max(3,5*workbenchView.scale);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
  for(const poi of w.pois){const c=workbenchView.centers.get(coordKey(poi.q,poi.r));if(!c)continue;ctx.beginPath();ctx.arc(c.x,c.y,poi.id===state.selectedPoiId?8:6,0,Math.PI*2);ctx.fillStyle=poi.is_landmark?'#ffd166':'#ff8fab';ctx.fill();ctx.strokeStyle='#10161d';ctx.lineWidth=2;ctx.stroke();}
  if(state.edgeFrom){const c=workbenchView.centers.get(coordKey(state.edgeFrom.q,state.edgeFrom.r));if(c){polygon(ctx,c.x,c.y,size*.82);ctx.strokeStyle='#ffd166';ctx.lineWidth=4;ctx.stroke();}}
  if(state.selectedHex){const c=workbenchView.centers.get(coordKey(state.selectedHex.q,state.selectedHex.r));if(c){polygon(ctx,c.x,c.y,size*.88);ctx.strokeStyle='#7bc3ff';ctx.lineWidth=4;ctx.stroke();}}
}

function nearestWorkbenchHex(x,y){let best=null,dist=Infinity;for(const h of state.mapWorkbench?.hexes||[]){const c=workbenchView.centers.get(coordKey(h.q,h.r));if(!c)continue;const d=Math.hypot(c.x-x,c.y-y);if(d<dist){dist=d;best=h;}}return dist<42*workbenchView.scale+8?best:null;}
function renderSelectedHex(){const h=state.selectedHex;if(!h){ui.selectedHex.innerHTML='Aucun hex sélectionné.';return;}const pois=(state.mapWorkbench?.pois||[]).filter(p=>p.q===h.q&&p.r===h.r);ui.selectedHex.innerHTML=`<strong>(${h.q}, ${h.r}) · ${esc(h.terrain_key)}</strong><div class="small">Hex #${h.id} · élévation ${h.elevation} · visibilité ${h.visibility_score} · coût ${h.travel_cost}</div><div class="small">${pois.length} POI sur cet hex.</div>`;renderPoiList();}
function renderPoiList(){const all=state.mapWorkbench?.pois||[];const rows=state.selectedHex?all.filter(p=>p.q===state.selectedHex.q&&p.r===state.selectedHex.r):all;ui.poiList.innerHTML=rows.map(p=>`<button type="button" class="feature-row ${p.id===state.selectedPoiId?'selected':''}" data-poi="${p.id}"><strong>${esc(p.name)}</strong><span>${esc(p.kind||'POI')} · identité POI #${p.feature_id} · row #${p.id}${p.is_landmark?' · landmark':''}</span></button>`).join('')||'<div class="empty">Aucun POI sur cet hex.</div>';ui.poiList.querySelectorAll('[data-poi]').forEach(el=>el.addEventListener('click',()=>selectPoi(Number(el.dataset.poi))));}
function selectPoi(id){const p=state.mapWorkbench?.pois.find(x=>x.id===id);if(!p)return;state.selectedPoiId=id;state.selectedHex=state.mapWorkbench.hexes.find(h=>h.id===p.hex_id)||state.selectedHex;ui.poiId.value=p.id;ui.poiName.value=p.name;ui.poiKind.value=p.kind||'';ui.poiDescription.value=p.dm_description||'';ui.poiLandmark.checked=p.is_landmark;renderSelectedHex();drawWorkbench();}
function clearPoiForm(){state.selectedPoiId=null;ui.poiId.value='';ui.poiName.value='';ui.poiKind.value='';ui.poiDescription.value='';ui.poiLandmark.checked=false;renderPoiList();drawWorkbench();}
function renderEdgeList(){const edges=state.mapWorkbench?.edges||[];ui.edgeList.innerHTML=edges.map(e=>`<button type="button" class="feature-row ${e.id===state.selectedEdgeId?'selected':''}" data-edge="${e.id}"><strong>${esc(e.name||e.feature_type)}</strong><span>${e.feature_type} #${e.feature_id} · (${e.from_q},${e.from_r})→(${e.to_q},${e.to_r})</span></button>`).join('')||'<div class="empty">Aucune feature entre hex.</div>';ui.edgeList.querySelectorAll('[data-edge]').forEach(el=>el.addEventListener('click',()=>{state.selectedEdgeId=Number(el.dataset.edge);renderEdgeList();drawWorkbench();}));}
function updateEdgeSelection(){if(!state.edgeFrom){ui.edgeSelection.textContent='Choisis un hex, puis “Départ = hex”, puis clique un hex adjacent.';return;}const to=state.selectedHex&&!(state.selectedHex.q===state.edgeFrom.q&&state.selectedHex.r===state.edgeFrom.r)?state.selectedHex:null;ui.edgeSelection.textContent=to?`(${state.edgeFrom.q}, ${state.edgeFrom.r}) → (${to.q}, ${to.r})${axialDistance(state.edgeFrom,to)===1?' · adjacent':' · PAS adjacent'}`:`Départ (${state.edgeFrom.q}, ${state.edgeFrom.r}) · clique la destination adjacente.`;}

async function loadMapWorkbench({fit=true}={}){
  if(!state.campaignId||!state.userId||!ui.workbenchVersion.value)return;
  ui.workbenchMessage.classList.remove('error');ui.workbenchMessage.textContent='Chargement…';
  try{state.mapWorkbench=await api(`/api/campaigns/${state.campaignId}/dm-map-workbench?user_id=${state.userId}&map_version_id=${Number(ui.workbenchVersion.value)}`);state.selectedHex=null;state.selectedPoiId=null;state.selectedEdgeId=null;state.edgeFrom=null;if(fit){resetWorkbenchView();requestAnimationFrame(()=>{fitWorkbench();drawWorkbench();});}else drawWorkbench();renderSelectedHex();renderPoiList();renderEdgeList();updateEdgeSelection();ui.poiEventMinute.value=state.dashboard?.campaign_game_minute??0;ui.edgeEventMinute.value=state.dashboard?.campaign_game_minute??0;ui.workbenchMessage.textContent=`${state.mapWorkbench.hexes.length} hex · ${state.mapWorkbench.pois.length} POI · ${state.mapWorkbench.edges.length} features`;}
  catch(error){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=error.message;}
}
async function savePoi(event){event.preventDefault();if(!state.selectedHex)return void(ui.workbenchMessage.textContent='Sélectionne d’abord un hex.');const payload={name:ui.poiName.value.trim(),kind:ui.poiKind.value.trim()||null,dm_description:ui.poiDescription.value.trim()||null,is_landmark:ui.poiLandmark.checked};try{if(state.selectedPoiId){await api(`/api/campaigns/${state.campaignId}/dm-pois/${state.selectedPoiId}?user_id=${state.userId}`,{method:'PATCH',body:JSON.stringify(payload)});}else{await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/pois?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({...payload,q:state.selectedHex.q,r:state.selectedHex.r})});}await refreshDashboard();await loadMapWorkbench({fit:false});clearPoiForm();ui.workbenchMessage.textContent='POI enregistré.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}
function parseJSONField(input){try{return JSON.parse(input.value||'{}');}catch(_){throw new Error('Payload JSON invalide');}}
async function savePoiEvent(event){event.preventDefault();if(!state.selectedPoiId)return void(ui.workbenchMessage.textContent='Sélectionne un POI.');try{await api(`/api/campaigns/${state.campaignId}/dm-pois/${state.selectedPoiId}/world-events?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({game_minute:Number(ui.poiEventMinute.value),event_type:ui.poiEventType.value,payload:parseJSONField(ui.poiEventPayload),dm_note:ui.poiEventNote.value.trim()||null})});await refreshDashboard();ui.workbenchMessage.textContent='WorldEvent POI ajouté à la timeline.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}
async function saveEdge(event){event.preventDefault();const from=state.edgeFrom,to=state.selectedHex;if(!from||!to)return void(ui.workbenchMessage.textContent='Sélectionne le départ et la destination.');if(axialDistance(from,to)!==1)return void(ui.workbenchMessage.textContent='La destination doit être un hex adjacent.');try{await api(`/api/campaigns/${state.campaignId}/dm-map-versions/${state.mapWorkbench.map_version_id}/edges?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({from_q:from.q,from_r:from.r,to_q:to.q,to_r:to.r,feature_type:ui.edgeType.value,name:ui.edgeName.value.trim()||null,extra_data:{}})});state.edgeFrom=null;ui.edgeName.value='';await refreshDashboard();await loadMapWorkbench({fit:false});ui.workbenchMessage.textContent='Feature créée.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}
async function saveEdgeEvent(event){event.preventDefault();if(!state.selectedEdgeId)return void(ui.workbenchMessage.textContent='Sélectionne une feature dans la liste.');try{await api(`/api/campaigns/${state.campaignId}/dm-map-edges/${state.selectedEdgeId}/world-events?user_id=${state.userId}`,{method:'POST',body:JSON.stringify({game_minute:Number(ui.edgeEventMinute.value),event_type:ui.edgeEventType.value,payload:parseJSONField(ui.edgeEventPayload),dm_note:ui.edgeEventNote.value.trim()||null})});await refreshDashboard();ui.workbenchMessage.textContent='WorldEvent de feature ajouté à la timeline.';}catch(e){ui.workbenchMessage.classList.add('error');ui.workbenchMessage.textContent=e.message;}}

ui.toggleCampaignCreate?.addEventListener('click',()=>{const hidden=ui.campaignCreateForm.classList.toggle('hidden');ui.toggleCampaignCreate.textContent=hidden?'+ Nouvelle campagne':'Masquer le formulaire';});
ui.cancelCampaignCreate?.addEventListener('click',()=>{ui.campaignCreateForm.classList.add('hidden');ui.toggleCampaignCreate.textContent='+ Nouvelle campagne';});
ui.campaignCreateForm?.addEventListener('submit',createCampaign);
ui.loadWorkbench?.addEventListener('click',()=>loadMapWorkbench());
ui.workbenchVersion?.addEventListener('change',()=>loadMapWorkbench());
ui.newPoi?.addEventListener('click',clearPoiForm);ui.poiForm?.addEventListener('submit',savePoi);ui.poiEventForm?.addEventListener('submit',savePoiEvent);
ui.edgeUseSelected?.addEventListener('click',()=>{if(state.selectedHex){state.edgeFrom=state.selectedHex;updateEdgeSelection();drawWorkbench();}});ui.edgeForm?.addEventListener('submit',saveEdge);ui.edgeEventForm?.addEventListener('submit',saveEdgeEvent);

if(ui.mapCanvas){ui.mapCanvas.addEventListener('mousedown',e=>{workbenchView.dragging=true;workbenchView.moved=false;workbenchView.lastX=e.clientX;workbenchView.lastY=e.clientY;});window.addEventListener('mouseup',()=>workbenchView.dragging=false);ui.mapCanvas.addEventListener('mousemove',e=>{if(!workbenchView.dragging)return;const dx=e.clientX-workbenchView.lastX,dy=e.clientY-workbenchView.lastY;if(Math.abs(dx)+Math.abs(dy)>2)workbenchView.moved=true;workbenchView.panX+=dx;workbenchView.panY+=dy;workbenchView.lastX=e.clientX;workbenchView.lastY=e.clientY;drawWorkbench();});ui.mapCanvas.addEventListener('click',e=>{if(workbenchView.moved)return;const rect=ui.mapCanvas.getBoundingClientRect(),h=nearestWorkbenchHex(e.clientX-rect.left,e.clientY-rect.top);if(!h)return;state.selectedHex=h;if(state.edgeFrom&&axialDistance(state.edgeFrom,h)===1){}renderSelectedHex();updateEdgeSelection();drawWorkbench();});ui.mapCanvas.addEventListener('wheel',e=>{e.preventDefault();workbenchView.scale=Math.max(.25,Math.min(3,workbenchView.scale*(e.deltaY<0?1.1:.9)));drawWorkbench();},{passive:false});new ResizeObserver(()=>drawWorkbench()).observe(ui.mapCanvas);}
