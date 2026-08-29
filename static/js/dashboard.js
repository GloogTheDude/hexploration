const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  userId: $("#user-id"), loadBtn: $("#load-user"), userInfo: $("#user-info"), error: $("#error"),
  campaigns: $("#campaigns"), characters: $("#characters"), expeditions: $("#expeditions"), campaignLabel: $("#campaign-label"),
  contextTitle: $("#context-title"), contextMeta: $("#context-meta"), contextActions: $("#context-actions"), emptyWorkspace: $("#empty-workspace"),
  mapFrame: $("#map-frame"), mapOpen: $("#map-open"), wikiTitle: $("#wiki-title"), wikiSubtitle: $("#wiki-subtitle"), wikiList: $("#wiki-list"), wikiReader: $("#wiki-reader"), wikiRefresh: $("#wiki-refresh"),
  recallBadge: $("#recall-badge"), recallStatusLine: $("#recall-status-line"), recallDisabled: $("#recall-disabled"), recallActive: $("#recall-active"),
  recallForm: $("#recall-search-form"), recallQuery: $("#recall-query"), recallMessage: $("#recall-message"), recallResults: $("#recall-results"), recallLibrary: $("#recall-library"), recallReader: $("#recall-reader"), recallRefresh: $("#recall-refresh"),
};

const state = { user: null, campaigns: [], characters: [], campaign: null, character: null, expeditions: [], expedition: null, tab: "map" };

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
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

function renderCampaigns() {
  ui.campaigns.classList.remove("muted");
  ui.campaigns.innerHTML = state.campaigns.map(c => `<div class="item clickable ${state.campaign?.id === c.id ? "selected" : ""}" data-campaign="${c.id}"><strong>${esc(c.name)}</strong><div class="meta"><span>#${c.id}</span><span>${esc(c.epoch_name)}</span></div></div>`).join("") || '<div class="empty">Aucune campagne.</div>';
  $$('[data-campaign]').forEach(el => el.addEventListener("click", () => selectCampaign(Number(el.dataset.campaign))));
}

function renderCharacters() {
  const rows = state.characters.filter(c => c.campaign_id === state.campaign?.id);
  ui.characters.classList.remove("muted");
  ui.characters.innerHTML = rows.map(c => `<div class="item clickable ${state.character?.id === c.id ? "selected" : ""}" data-character="${c.id}"><strong>${esc(c.name)}</strong><div class="meta"><span>#${c.id}</span><span>${esc(c.race || "—")}</span><span>${esc(c.character_class || "—")}</span><span>niv. ${c.level ?? "—"}</span><span>${esc(c.status)}</span><span>m.${c.current_game_minute}</span></div></div>`).join("") || '<div class="empty">Aucun personnage dans cette campagne.</div>';
  $$('[data-character]').forEach(el => el.addEventListener("click", () => selectCharacter(Number(el.dataset.character))));
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
  renderCampaigns(); renderCharacters(); renderExpeditions(); renderContext();
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

async function load() {
  ui.error.textContent = "";
  try {
    const id = Number(ui.userId.value); if (!id) return;
    qs("user", id);
    const [user, campaigns, characters] = await Promise.all([api(`/api/users/${id}`), api(`/api/campaigns/by-user/${id}`), api(`/api/users/${id}/characters`)]);
    state.user = user; state.campaigns = campaigns; state.characters = characters; state.campaign = null; state.character = null; state.expedition = null;
    ui.userInfo.classList.remove("muted"); ui.userInfo.innerHTML = `<strong>${esc(user.username)}</strong> · ${esc(user.email)} · #${user.id}`;
    renderCampaigns(); renderCharacters(); renderExpeditions(); renderContext();
    const requested = Number(new URL(location.href).searchParams.get("campaign"));
    const initial = campaigns.find(c => c.id === requested) || campaigns[0];
    if (initial) await selectCampaign(initial.id);
  } catch (e) { ui.error.textContent = e.message; }
}

ui.loadBtn.addEventListener("click", load);
ui.userId.addEventListener("keydown", e => { if (e.key === "Enter") load(); });
$$(".tab").forEach(tab => tab.addEventListener("click", () => setTab(tab.dataset.tab)));
ui.wikiRefresh.addEventListener("click", loadWiki);
ui.recallRefresh.addEventListener("click", loadRecall);
ui.recallForm.addEventListener("submit", searchRecall);

const initialUser = Number(new URL(location.href).searchParams.get("user"));
if (initialUser) ui.userId.value = initialUser;
load();
