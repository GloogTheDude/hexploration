const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  userId: $("#user-id"), loadBtn: $("#load-user"), userInfo: $("#user-info"), error: $("#error"),
  campaigns: $("#campaigns"), invitations: $("#invitations"), invitationMessage: $("#invitation-message"), refreshInvitations: $("#refresh-invitations"), characters: $("#characters"), toggleCharacterCreate: $("#toggle-character-create"), characterModal: $("#character-modal"), closeCharacterModal: $("#close-character-modal"), cancelCharacterCreate: $("#cancel-character-create"), characterCreateForm: $("#character-create-form"), characterCreateName: $("#character-create-name"), characterCreateRace: $("#character-create-race"), characterCreateClass: $("#character-create-class"), characterCreateLevel: $("#character-create-level"), characterCreateDescription: $("#character-create-description"), characterCreateMessage: $("#character-create-message"), expeditions: $("#expeditions"), campaignLabel: $("#campaign-label"),
  contextTitle: $("#context-title"), contextMeta: $("#context-meta"), contextActions: $("#context-actions"), emptyWorkspace: $("#empty-workspace"),
  mapFrame: $("#map-frame"), mapOpen: $("#map-open"), wikiTitle: $("#wiki-title"), wikiSubtitle: $("#wiki-subtitle"), wikiList: $("#wiki-list"), wikiReader: $("#wiki-reader"), wikiRefresh: $("#wiki-refresh"),
  recallBadge: $("#recall-badge"), recallStatusLine: $("#recall-status-line"), recallDisabled: $("#recall-disabled"), recallActive: $("#recall-active"),
  recallForm: $("#recall-search-form"), recallQuery: $("#recall-query"), recallMessage: $("#recall-message"), recallResults: $("#recall-results"), recallLibrary: $("#recall-library"), recallReader: $("#recall-reader"), recallRefresh: $("#recall-refresh"),
  sheetModal: $("#sheet-modal"), closeSheetModal: $("#close-sheet-modal"), sheetTitle: $("#sheet-modal-title"), sheetCurrentLabel: $("#sheet-current-label"), sheetCurrentMeta: $("#sheet-current-meta"), sheetMessage: $("#sheet-message"), sheetDataForm: $("#sheet-data-form"), sheetExportPdf: $("#sheet-export-pdf"), sheetSave: $("#sheet-save"), sheetHistory: $("#sheet-history"),
};

const state = { user: null, campaigns: [], invitations: [], characters: [], campaign: null, character: null, expeditions: [], expedition: null, tab: "map", sheetVersions: [], sheetLoadedVersion: null };

async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const headers = isForm ? { ...(options.headers || {}) } : { "Content-Type": "application/json", ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail); } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function esc(value) { return String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
function statusClass(status) { return status === "ACTIVE" ? "status-active" : status === "RETURNED" ? "status-returned" : ""; }
function humanPosition(e) { return e.current_q == null ? "sans position" : `(${e.current_q}, ${e.current_r})`; }
function qs(name, value) { const url = new URL(location.href); if (value == null) url.searchParams.delete(name); else url.searchParams.set(name, value); history.replaceState(null, "", url); }

function renderInvitations() {
  ui.invitations.classList.remove("muted");
  ui.invitations.innerHTML = state.invitations.map(i => `<div class="item"><strong>${esc(i.campaign_name)}</strong><div class="meta"><span>Invité par ${esc(i.invited_by_username)}</span></div><div class="actions"><button data-invite-accept="${i.id}">Accepter</button><button data-invite-refuse="${i.id}">Refuser</button></div></div>`).join("") || '<div class="empty">Aucune invitation en attente.</div>';
  $$('[data-invite-accept]').forEach(b => b.addEventListener('click', () => respondInvitation(Number(b.dataset.inviteAccept), 'accept')));
  $$('[data-invite-refuse]').forEach(b => b.addEventListener('click', () => respondInvitation(Number(b.dataset.inviteRefuse), 'refuse')));
}

async function respondInvitation(id, action) {
  ui.invitationMessage.textContent = 'Traitement…';
  try { await api(`/api/campaign-invitations/${id}/${action}?user_id=${state.user.id}`, {method:'POST'}); ui.invitationMessage.textContent = action === 'accept' ? 'Invitation acceptée.' : 'Invitation refusée.'; await load(); }
  catch(e) { ui.invitationMessage.textContent = e.message; }
}

function renderCampaigns() {
  ui.campaigns.classList.remove("muted");
  ui.campaigns.innerHTML = state.campaigns.map(c => `<div class="item clickable ${state.campaign?.id === c.id ? "selected" : ""}" data-campaign="${c.id}"><strong>${esc(c.name)}</strong><div class="meta"><span>#${c.id}</span><span>${esc(c.epoch_name)}</span></div></div>`).join("") || '<div class="empty">Aucune campagne.</div>';
  $$('[data-campaign]').forEach(el => el.addEventListener("click", () => selectCampaign(Number(el.dataset.campaign))));
}

function renderCharacters() {
  const rows = state.characters.filter(c => c.campaign_id === state.campaign?.id);
  ui.characters.classList.remove("muted");
  ui.toggleCharacterCreate.classList.toggle("hidden", !state.campaign);
  ui.characters.innerHTML = rows.map(c => `<div class="item character-item ${state.character?.id === c.id ? "selected" : ""}"><button class="character-select" data-character="${c.id}" type="button"><strong>${esc(c.name)}</strong><div class="meta"><span>#${c.id}</span><span>${esc(c.race || "—")}</span><span>${esc(c.character_class || "—")}</span><span>niv. ${c.level ?? "—"}</span><span>${esc(c.status)}</span><span>m.${c.current_game_minute}</span></div></button><div class="character-actions"><button type="button" data-character-sheet="${c.id}">Fiche</button><button type="button" class="secondary" data-character-retire="${c.id}" ${c.status !== 'ACTIVE' ? 'disabled' : ''}>Retirer</button><button type="button" class="danger" data-character-delete="${c.id}">Supprimer</button></div></div>`).join("") || '<div class="empty">Aucun personnage dans cette campagne.</div>';
  $$('[data-character]').forEach(el => el.addEventListener("click", () => selectCharacter(Number(el.dataset.character))));
  $$('[data-character-delete]').forEach(el => el.addEventListener('click', () => deleteCharacter(Number(el.dataset.characterDelete))));
  $$('[data-character-retire]').forEach(el => el.addEventListener('click', () => retireCharacter(Number(el.dataset.characterRetire))));
  $$('[data-character-sheet]').forEach(el => el.addEventListener('click', () => openSheetModal(Number(el.dataset.characterSheet))));
}

function renderExpeditions() {
  ui.expeditions.classList.remove("muted");
  if (!state.character) { ui.expeditions.innerHTML = '<div class="empty">Sélectionne un personnage.</div>'; return; }
  ui.campaignLabel.textContent = `${state.campaign.name} · ${state.character.name}`;
  ui.expeditions.innerHTML = state.expeditions.map(e => `<div class="item clickable ${state.expedition?.id === e.id ? "selected" : ""}" data-expedition="${e.id}"><strong>${esc(e.name)}</strong><div class="meta"><span>#${e.id}</span><span class="${statusClass(e.status)}">${esc(e.status)}</span><span>m.${e.current_game_minute}</span><span>${humanPosition(e)}</span></div></div>`).join("") || '<div class="empty">Aucune expédition pour ce personnage.</div>';
  $$('[data-expedition]').forEach(el => el.addEventListener("click", () => selectExpedition(Number(el.dataset.expedition))));
}

function setTab(name) {
  state.tab = name;
  $$(".tab").forEach(tab => tab.classList.toggle("selected", tab.dataset.tab === name));
  $$(".tab-panel").forEach(panel => panel.classList.toggle("hidden", panel.dataset.panel !== name || !state.expedition));
  ui.emptyWorkspace.classList.toggle("hidden", Boolean(state.expedition));
  if (!state.expedition) return;
  if (name === "wiki") loadWiki();
  if (name === "recall") loadRecall();
}

function renderContext() {
  const e = state.expedition;
  if (!e) {
    ui.contextTitle.textContent = "Aucune expédition sélectionnée";
    ui.contextMeta.textContent = "Choisis une campagne, un personnage puis une expédition.";
    ui.contextActions.innerHTML = "";
    ui.mapFrame.removeAttribute("src");
    setTab(state.tab);
    return;
  }
  ui.contextTitle.textContent = e.name;
  ui.contextMeta.innerHTML = `<span class="${statusClass(e.status)}">${esc(e.status)}</span><span>minute ${e.current_game_minute}</span><span>position ${humanPosition(e)}</span><span>${esc(state.character.name)}</span>`;
  ui.contextActions.innerHTML = `<a class="button-link" href="/player.html?expedition=${e.id}">Carte plein écran</a>`;
  const mapUrl = `/player.html?expedition=${e.id}&embedded=1`;
  ui.mapOpen.href = `/player.html?expedition=${e.id}`;
  if (ui.mapFrame.getAttribute("src") !== mapUrl) ui.mapFrame.src = mapUrl;
  setTab(state.tab);
}

async function loadExpeditionsForCharacter() {
  state.expeditions = [];
  state.expedition = null;
  if (!state.campaign || !state.character) { renderExpeditions(); renderContext(); return; }
  const all = await api(`/api/campaigns/${state.campaign.id}/expeditions`);
  const matching = [];
  for (const expedition of all) {
    const participants = await api(`/api/expeditions/${expedition.id}/characters`);
    if (participants.some(p => p.character_id === state.character.id)) matching.push(expedition);
  }
  const rank = { ACTIVE: 0, PLANNING: 1, DEBRIEFING: 2, RETURNED: 3, LOST: 4, DEAD: 5, ARCHIVED: 6 };
  state.expeditions = matching.sort((a,b) => (rank[a.status] ?? 99) - (rank[b.status] ?? 99) || b.current_game_minute - a.current_game_minute);
  renderExpeditions();
  const requested = Number(new URL(location.href).searchParams.get("expedition"));
  const initial = state.expeditions.find(e => e.id === requested) || state.expeditions[0];
  if (initial) await selectExpedition(initial.id);
  else renderContext();
}

async function selectCampaign(id) {
  state.campaign = state.campaigns.find(c => c.id === id) || null;
  state.character = null; state.expedition = null; state.expeditions = [];
  qs("campaign", id); qs("character", null); qs("expedition", null);
  renderInvitations(); renderCampaigns(); renderCharacters(); renderExpeditions(); renderContext();
  const chars = state.characters.filter(c => c.campaign_id === id);
  const requested = Number(new URL(location.href).searchParams.get("character"));
  const initial = chars.find(c => c.id === requested) || chars[0];
  if (initial) await selectCharacter(initial.id);
}

async function selectCharacter(id) {
  state.character = state.characters.find(c => c.id === id && c.campaign_id === state.campaign?.id) || null;
  state.expedition = null;
  qs("character", id); qs("expedition", null);
  renderCharacters(); renderContext();
  await loadExpeditionsForCharacter();
}

async function selectExpedition(id) {
  state.expedition = state.expeditions.find(e => e.id === id) || null;
  qs("expedition", id);
  renderExpeditions(); renderContext();
  await refreshRecallBadge();
}

function renderWikiPage(container, pageState, label = "") {
  const p = pageState.page, r = pageState.revision;
  container.innerHTML = `<h3>${esc(p.title)}</h3><div class="reader-meta">${esc(p.category || "Wiki")} · révision ${r.revision} · effective minute ${r.effective_from_game_minute}${label ? ` · ${esc(label)}` : ""}</div>${esc(r.content)}`;
}

async function loadWiki() {
  if (!state.expedition) return;
  ui.wikiList.innerHTML = '<div class="muted">Chargement…</div>';
  ui.wikiReader.innerHTML = '<p class="muted">Sélectionne une page.</p>';
  try {
    if (state.expedition.status === "ACTIVE") {
      ui.wikiTitle.textContent = "Wiki disponible en expédition";
      ui.wikiSubtitle.textContent = "Seules les pages déjà rappelées sont accessibles hors du hub.";
      const library = await api(`/api/expeditions/${state.expedition.id}/recall`);
      const pages = library.pages || [];
      ui.wikiList.innerHTML = pages.map((entry, i) => `<div class="knowledge-item" data-wiki-index="${i}"><div class="title">${esc(entry.page.title)}</div><div class="small">rappelée m.${entry.recall.recalled_at_game_minute} · cutoff m.${entry.recall.knowledge_cutoff_game_minute}</div></div>`).join("") || '<div class="empty">Aucune page rappelée. Utilise l’onglet Recall.</div>';
      $$('[data-wiki-index]').forEach(el => el.addEventListener("click", () => { const entry = pages[Number(el.dataset.wikiIndex)]; $$('[data-wiki-index]').forEach(x => x.classList.remove("selected")); el.classList.add("selected"); renderWikiPage(ui.wikiReader, entry, "version connue au départ"); }));
    } else {
      ui.wikiTitle.textContent = "Wiki du hub";
      ui.wikiSubtitle.textContent = "Connaissance publiée de la campagne.";
      const wiki = await api(`/api/campaigns/${state.campaign.id}/wiki`);
      const pages = wiki.pages || [];
      ui.wikiList.innerHTML = pages.map((entry, i) => `<div class="knowledge-item" data-wiki-index="${i}"><div class="title">${esc(entry.page.title)}</div><div class="small">${esc(entry.page.category || "Wiki")} · révision ${entry.revision.revision}</div></div>`).join("") || '<div class="empty">Le wiki du hub est vide.</div>';
      $$('[data-wiki-index]').forEach(el => el.addEventListener("click", () => { const entry = pages[Number(el.dataset.wikiIndex)]; $$('[data-wiki-index]').forEach(x => x.classList.remove("selected")); el.classList.add("selected"); renderWikiPage(ui.wikiReader, entry); }));
    }
  } catch (e) { ui.wikiList.innerHTML = `<div class="error">${esc(e.message)}</div>`; }
}

async function refreshRecallBadge() {
  ui.recallBadge.classList.add("hidden");
  if (!state.expedition || !state.character || state.expedition.status !== "ACTIVE") return;
  try {
    const status = await api(`/api/expeditions/${state.expedition.id}/recall/status?character_id=${state.character.id}`);
    ui.recallBadge.textContent = status.remaining;
    ui.recallBadge.classList.remove("hidden");
  } catch (_) {}
}

function renderRecallLibrary(pages) {
  ui.recallLibrary.innerHTML = pages.map((entry, i) => `<div class="knowledge-item" data-recalled-index="${i}"><div class="title">${esc(entry.page.title)}</div><div class="small">rappelée par personnage #${entry.recall.character_id} · m.${entry.recall.recalled_at_game_minute}</div></div>`).join("") || '<div class="empty">Aucune page rappelée par le groupe.</div>';
  $$('[data-recalled-index]').forEach(el => el.addEventListener("click", () => { const entry = pages[Number(el.dataset.recalledIndex)]; $$('[data-recalled-index]').forEach(x => x.classList.remove("selected")); el.classList.add("selected"); renderWikiPage(ui.recallReader, entry, "mémoire partagée de l’expédition"); }));
}

async function loadRecall() {
  if (!state.expedition || !state.character) return;
  ui.recallMessage.textContent = "";
  if (state.expedition.status !== "ACTIVE") {
    ui.recallActive.classList.add("hidden"); ui.recallDisabled.classList.remove("hidden");
    ui.recallDisabled.textContent = `Recall indisponible : l’expédition est ${state.expedition.status}. Le recall est réservé aux expéditions ACTIVE.`;
    ui.recallStatusLine.textContent = "Disponible uniquement pendant une expédition active.";
    return;
  }
  ui.recallDisabled.classList.add("hidden"); ui.recallActive.classList.remove("hidden");
  try {
    const [status, library] = await Promise.all([
      api(`/api/expeditions/${state.expedition.id}/recall/status?character_id=${state.character.id}`),
      api(`/api/expeditions/${state.expedition.id}/recall`),
    ]);
    ui.recallStatusLine.textContent = `${state.character.name} : ${status.remaining}/${status.limit} recalls restants · wiki figé à la minute ${status.knowledge_cutoff_game_minute}.`;
    ui.recallBadge.textContent = status.remaining; ui.recallBadge.classList.remove("hidden");
    renderRecallLibrary(library.pages || []);
  } catch (e) { ui.recallMessage.textContent = e.message; }
}

async function searchRecall(event) {
  event.preventDefault();
  if (!state.expedition || !state.character) return;
  const q = ui.recallQuery.value.trim(); if (!q) return;
  ui.recallMessage.textContent = "Recherche…";
  try {
    const result = await api(`/api/expeditions/${state.expedition.id}/recall/search?character_id=${state.character.id}&q=${encodeURIComponent(q)}`);
    const pages = result.results || [];
    ui.recallMessage.textContent = `${pages.length} résultat(s) dans le wiki connu à la minute ${result.knowledge_cutoff_game_minute}.`;
    ui.recallResults.innerHTML = pages.map((entry, i) => `<div class="knowledge-item"><div class="title">${esc(entry.page.title)}</div><div class="small">${esc(entry.page.category || "Wiki")} · révision ${entry.revision.revision}</div><div class="recall-result-actions"><span class="small">page #${entry.page.id}</span><button type="button" data-recall-index="${i}">Rappeler</button></div></div>`).join("") || '<div class="empty">Aucun résultat.</div>';
    $$('[data-recall-index]').forEach(btn => btn.addEventListener("click", () => recallPage(pages[Number(btn.dataset.recallIndex)])));
  } catch (e) { ui.recallMessage.textContent = e.message; }
}

async function recallPage(entry) {
  try {
    await api(`/api/expeditions/${state.expedition.id}/recall`, { method: "POST", body: JSON.stringify({ character_id: state.character.id, page_id: entry.page.id }) });
    ui.recallMessage.textContent = `${entry.page.title} est maintenant disponible pour toute l’expédition.`;
    await loadRecall(); await refreshRecallBadge();
  } catch (e) { ui.recallMessage.textContent = e.message; }
}


function sheetPdfUrl(characterId, version = null) {
  const suffix = version == null ? "/current/pdf" : `/${version}/pdf`;
  return `/api/characters/${characterId}/sheet-data${suffix}?user_id=${state.user.id}`;
}

const SHEET_NUMERIC_FIELDS = new Set([
  'level','experience_points','strength','dexterity','constitution','intelligence','wisdom','charisma',
  'armor_class','initiative','proficiency_bonus','max_hp','current_hp','temp_hp','passive_perception'
]);

function closeSheetModal(){
  ui.sheetModal.classList.add('hidden');
  state.sheetVersions = [];
  state.sheetLoadedVersion = null;
}

function abilityModifier(score){ return Math.floor((Number(score || 10) - 10) / 2); }
function signedNumber(value){ const n=Number(value); return Number.isFinite(n) ? `${n >= 0 ? '+' : ''}${n}` : '—'; }

function refreshAbilityModifiers(){
  $$('[data-mod-for]').forEach(span => {
    const input = ui.sheetDataForm.elements[span.dataset.modFor];
    span.textContent = signedNumber(abilityModifier(input?.value));
  });
}

function fillSheetForm(data){
  for(const [name, value] of Object.entries(data || {})){
    const field = ui.sheetDataForm.elements[name];
    if(!field) continue;
    field.value = value ?? '';
  }
  refreshAbilityModifiers();
}

function sheetFormPayload(){
  const payload = {};
  for(const element of ui.sheetDataForm.elements){
    if(!element.name) continue;
    if(SHEET_NUMERIC_FIELDS.has(element.name)){
      payload[element.name] = element.value === '' ? null : Number(element.value);
    } else payload[element.name] = element.value;
  }
  for(const ability of ['strength','dexterity','constitution','intelligence','wisdom','charisma']){
    if(payload[ability] == null) payload[ability] = 10;
  }
  return payload;
}

async function openSheetModal(characterId){
  const character = state.characters.find(c => c.id === characterId);
  if(!character || !state.user) return;
  state.character = character;
  state.sheetLoadedVersion = null;
  ui.sheetTitle.textContent = `Fiche · ${character.name}`;
  ui.sheetMessage.textContent = 'Chargement de la fiche…';
  ui.sheetModal.classList.remove('hidden');
  try {
    await api(`/api/characters/${characterId}/sheet-data/initialize?user_id=${state.user.id}`, {method:'POST'});
    await loadCharacterSheetData(characterId);
    ui.sheetMessage.textContent = '';
  } catch(e){ ui.sheetMessage.textContent = e.message; }
}

async function loadCharacterSheetData(characterId){
  const versions = await api(`/api/characters/${characterId}/sheet-data?user_id=${state.user.id}`);
  state.sheetVersions = versions;
  const current = versions.find(v => v.is_current) || versions[0] || null;
  if(!current) return;
  state.sheetLoadedVersion = current.version;
  fillSheetForm(current.data);
  ui.sheetCurrentLabel.textContent = `Version ${current.version} · actuelle`;
  ui.sheetCurrentMeta.textContent = `Enregistrée à la minute ${current.campaign_game_minute}. La base de données est la source de vérité.`;
  ui.sheetExportPdf.href = sheetPdfUrl(characterId);
  ui.sheetExportPdf.classList.remove('hidden');
  renderSheetHistory();
}

function renderSheetHistory(){
  const characterId = state.character?.id;
  ui.sheetHistory.innerHTML = state.sheetVersions.map(v => `<div class="sheet-version ${v.is_current ? 'current' : ''} ${state.sheetLoadedVersion === v.version ? 'loaded' : ''}"><div><strong>Version ${v.version}${v.is_current ? ' · actuelle' : ''}</strong><div class="muted compact">minute ${v.campaign_game_minute} · ${new Date(v.created_at).toLocaleString('fr-BE')}</div></div><div class="sheet-version-actions"><button type="button" class="secondary" data-sheet-load-version="${v.version}">Charger</button><a class="button-link" target="_blank" rel="noopener" href="${sheetPdfUrl(characterId, v.version)}">PDF</a></div></div>`).join('') || '<div class="empty">Aucune version.</div>';
  $$('[data-sheet-load-version]').forEach(button => button.addEventListener('click', () => loadSheetVersion(Number(button.dataset.sheetLoadVersion))));
}

function loadSheetVersion(version){
  const item = state.sheetVersions.find(v => v.version === version);
  if(!item) return;
  state.sheetLoadedVersion = version;
  fillSheetForm(item.data);
  ui.sheetMessage.textContent = version === state.sheetVersions.find(v=>v.is_current)?.version
    ? `Version ${version} actuelle chargée.`
    : `Version ${version} chargée pour consultation. Enregistrer créera une nouvelle version.`;
  renderSheetHistory();
}

async function saveCharacterSheet(event){
  event.preventDefault();
  if(!state.character || !state.user) return;
  ui.sheetSave.disabled = true;
  ui.sheetMessage.textContent = 'Enregistrement…';
  try {
    const saved = await api(`/api/characters/${state.character.id}/sheet-data?user_id=${state.user.id}`, {method:'POST', body:JSON.stringify(sheetFormPayload())});
    ui.sheetMessage.textContent = `Version ${saved.version} enregistrée.`;
    ui.sheetMessage.classList.add('sheet-save-flash');
    setTimeout(()=>ui.sheetMessage.classList.remove('sheet-save-flash'),1200);
    await refreshPlayerData();
    state.character = state.characters.find(c=>c.id===saved.character_id) || state.character;
    await loadCharacterSheetData(saved.character_id);
    renderCharacters();
  } catch(e){ ui.sheetMessage.textContent = e.message; }
  finally { ui.sheetSave.disabled = false; }
}

function openCharacterModal(){ if(!state.campaign) return; ui.characterCreateMessage.textContent=''; ui.characterModal.classList.remove('hidden'); ui.characterCreateName.focus(); }
function closeCharacterModal(){ ui.characterModal.classList.add('hidden'); }

async function refreshPlayerData({preserveCampaign=true}={}) {
  if(!state.user) return;
  const [campaigns, invitations, characters] = await Promise.all([api(`/api/campaigns/by-user/${state.user.id}`), api(`/api/users/${state.user.id}/campaign-invitations`), api(`/api/users/${state.user.id}/characters`)]);
  const campaignId = preserveCampaign ? state.campaign?.id : null;
  state.campaigns=campaigns; state.invitations=invitations; state.characters=characters;
  state.campaign = campaigns.find(c=>c.id===campaignId) || state.campaign;
  if(state.campaign && !campaigns.some(c=>c.id===state.campaign.id)) state.campaign=null;
  if(state.character) state.character = characters.find(c=>c.id===state.character.id) || null;
  renderInvitations(); renderCampaigns(); renderCharacters();
}

async function deleteCharacter(id){
  const c=state.characters.find(x=>x.id===id); if(!c)return;
  if(!confirm(`Supprimer définitivement ${c.name} ?\n\nCette action est irréversible et n'est autorisée que si le personnage n'a jamais participé à une expédition.`)) return;
  try { await api(`/api/characters/${id}?user_id=${state.user.id}`,{method:'DELETE'}); if(state.character?.id===id){state.character=null;state.expedition=null;state.expeditions=[];} await refreshPlayerData(); renderExpeditions(); renderContext(); }
  catch(e){ alert(e.message); }
}

async function retireCharacter(id){
  const c=state.characters.find(x=>x.id===id); if(!c)return;
  if(!confirm(`Retirer ${c.name} ? Le personnage restera dans l'historique de la campagne.`)) return;
  try { await api(`/api/characters/${id}/retire?user_id=${state.user.id}`,{method:'POST'}); await refreshPlayerData(); } catch(e){ alert(e.message); }
}

async function createPlayerCharacter(event) {
  event.preventDefault(); if (!state.campaign || !state.user) return;
  ui.characterCreateMessage.textContent = 'Création…';
  const payload={owner_user_id:state.user.id,name:ui.characterCreateName.value.trim(),race:ui.characterCreateRace.value.trim()||null,character_class:ui.characterCreateClass.value.trim()||null,level:ui.characterCreateLevel.value?Number(ui.characterCreateLevel.value):null,description:ui.characterCreateDescription.value.trim()||null,current_game_minute:0};
  try { const c=await api(`/api/campaigns/${state.campaign.id}/player-characters?user_id=${state.user.id}`,{method:'POST',body:JSON.stringify(payload)}); ui.characterCreateMessage.textContent=`${c.name} créé.`; ui.characterCreateForm.reset(); closeCharacterModal(); await refreshPlayerData(); if(state.campaign) await selectCampaign(state.campaign.id); await openSheetModal(c.id); }
  catch(e){ ui.characterCreateMessage.textContent=e.message; }
}

async function load() {
  ui.error.textContent = "";
  try {
    const id = Number(ui.userId.value); if (!id) return;
    qs("user", id);
    const [user, campaigns, invitations, characters] = await Promise.all([api(`/api/users/${id}`), api(`/api/campaigns/by-user/${id}`), api(`/api/users/${id}/campaign-invitations`), api(`/api/users/${id}/characters`)]);
    state.user = user; state.campaigns = campaigns; state.invitations = invitations; state.characters = characters; state.campaign = null; state.character = null; state.expedition = null;
    ui.userInfo.classList.remove("muted"); ui.userInfo.innerHTML = `<strong>${esc(user.username)}</strong> · ${esc(user.email)} · #${user.id}`;
    renderInvitations(); renderCampaigns(); renderCharacters(); renderExpeditions(); renderContext();
    const requested = Number(new URL(location.href).searchParams.get("campaign"));
    const initial = campaigns.find(c => c.id === requested) || campaigns[0];
    if (initial) await selectCampaign(initial.id);
  } catch (e) { ui.error.textContent = e.message; }
}

ui.toggleCharacterCreate.addEventListener("click", openCharacterModal);
ui.closeCharacterModal.addEventListener("click", closeCharacterModal);
ui.cancelCharacterCreate.addEventListener("click", closeCharacterModal);
ui.characterModal.addEventListener("click", e => { if(e.target===ui.characterModal) closeCharacterModal(); });
ui.characterCreateForm.addEventListener("submit", createPlayerCharacter);
ui.closeSheetModal.addEventListener("click", closeSheetModal);
ui.sheetModal.addEventListener("click", e => { if(e.target===ui.sheetModal) closeSheetModal(); });
ui.sheetDataForm.addEventListener("submit", saveCharacterSheet);
ui.sheetDataForm.addEventListener("input", e => { if(e.target.name && ["strength","dexterity","constitution","intelligence","wisdom","charisma"].includes(e.target.name)) refreshAbilityModifiers(); });
ui.refreshInvitations.addEventListener("click", () => refreshPlayerData());
setInterval(() => { if(state.user && document.visibilityState === 'visible') refreshPlayerData().catch(()=>{}); }, 10000);
ui.loadBtn.addEventListener("click", load);
ui.userId.addEventListener("keydown", e => { if (e.key === "Enter") load(); });
$$(".tab").forEach(tab => tab.addEventListener("click", () => setTab(tab.dataset.tab)));
ui.wikiRefresh.addEventListener("click", loadWiki);
ui.recallRefresh.addEventListener("click", loadRecall);
ui.recallForm.addEventListener("submit", searchRecall);

const initialUser = Number(new URL(location.href).searchParams.get("user"));
if (initialUser) ui.userId.value = initialUser;
load();
