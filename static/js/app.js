import { state } from "./state.js?v=320";
import { fetchPersistentMap, fetchTerrains, createMap } from "./api.js?v=320";
import { drawMap, requestMapDraw, resizeCanvasToDisplaySize } from "./renderer.js?v=320";
import { createTerrainButtons } from "./ui.js?v=320";
import { authReady, authFetch } from './auth.js';
import { mouseToHex, paintHexesBatchRadius, flushPendingPaint, beginPaintStroke, endPaintStroke, undoPaint, redoPaint, clearPaintHistory } from "./tools.js?v=320";
import { axialToPixel, getHexLine } from "./hex_math.js?v=320";
import { gameMinuteFromDateInputs, setDateInputs, formatGameDate } from "./game_time.js";

const $ = (s) => document.querySelector(s);
const canvas = $("#hex-canvas");
const canvasWrap = $("#canvas-wrap");
const newMapBtn = $("#new-map-btn");
const reloadMapBtn = $("#reload-map-btn");
const modal = $("#new-map-modal");
const newMapForm = $("#new-map-form");
const cancelNewMapBtn = $("#cancel-new-map-btn");
const brushBtn = $("#brush-btn");
const brushStatus = $("#brush-status");
const radiusSlider = $("#radius-slider");
const radiusSliderValue = $("#radius-slider-value");
const zoomInBtn = $("#zoom-in-btn");
const zoomOutBtn = $("#zoom-out-btn");
const fitMapBtn = $("#fit-map-btn");
const zoomLabel = $("#zoom-label");
const mapSummary = $("#map-summary");
const canvasHint = $("#canvas-hint");
const poiOverlayBtn = $("#toggle-poi-overlay");

const params = new URL(location.href).searchParams;
const editorCampaignId = Number(params.get("campaign"));
let editorMapId = Number(params.get("map")) || null;
let editorVersionId = Number(params.get("version")) || null;
let loadedVersionNumber = null;
let paintMoveFrame = 0;
let pendingPaintEvent = null;

const campaignSavePanel = $("#campaign-save-panel");
const campaignNameLabel = $("#editor-campaign-name");
const campaignContextLabel = $("#editor-campaign-context");
const editorDmLink = $("#editor-dm-link");
const editorWorldLink = $("#editor-world-link");
const persistedVersionSelect = $("#persisted-version-select");
const loadPersistedBtn = $("#load-persisted-btn");
const persistMapBtn = $("#persist-map-btn");
const persistMapMessage = $("#persist-map-message");
const persistMapName = $("#persist-map-name");
const persistVersionName = $("#persist-version-name");

const saveModeWrap = $("#save-mode-wrap");
const updateVersionNumber = $("#update-version-number");

function setMessage(message, error = false) {
  persistMapMessage.textContent = message || "";
  persistMapMessage.classList.toggle("error", error);
}

window.addEventListener("paint-sync-error", event => {
  setMessage(event.detail?.message || "La peinture n’a pas pu être synchronisée.", true);
});

function updateMapSummary() {
  const materialized = state.map?.hexes ? Object.keys(state.map.hexes).length : 0;
  const logical = state.map?.width && state.map?.height ? state.map.width * state.map.height : 0;
  mapSummary.textContent = logical ? `${state.map.width}×${state.map.height} · ${logical.toLocaleString("fr-FR")} hex logiques · ${materialized.toLocaleString("fr-FR")} modifiés` : "Aucune carte chargée";
  canvasHint.textContent = state.isBrushOn
    ? "Clique/glisse pour peindre · Ctrl+Z annule · Ctrl+Shift+Z rétablit · Espace déplace."
    : "Molette pour zoomer · glisser pour déplacer · Espace = déplacement temporaire.";
}


async function refreshPoiOverlay() {
  state.editorPois = [];
  if (!editorCampaignId || !editorVersionId) { redraw(); return; }
  try {
    const workbench = await fetchJson(`/api/campaigns/${editorCampaignId}/dm-map-workbench?map_version_id=${editorVersionId}`);
    state.editorPois = workbench.pois || [];
  } catch (_) {
    state.editorPois = [];
  }
  redraw();
}

function mapFromWorkbench(workbench) {
  const hexes = {};
  for (const hex of workbench.hexes || []) {
    const terrain = state.terrains[hex.terrain_key];
    if (terrain) {
      hexes[`${hex.q},${hex.r}`] = {
        q: hex.q,
        r: hex.r,
        terrain: { ...terrain, elevation: hex.elevation, visibility_score: hex.visibility_score, travel_cost: hex.travel_cost },
        pois: [],
      };
    }
  }
  return {
    width: workbench.width,
    height: workbench.height,
    hex_size: workbench.hex_size,
    layout: "even-q-rect",
    sparse: Boolean(workbench.default_terrain_key),
    default_terrain_key: workbench.default_terrain_key || "SEA",
    hexes,
  };
}

async function loadWorkbenchIntoCanvas(versionId) {
  const workbench = await fetchPersistentMap(editorCampaignId, versionId);
  state.map = mapFromWorkbench(workbench);
  state.editor = { campaignId: editorCampaignId, mapId: workbench.map_id, versionId: workbench.map_version_id };
  editorMapId = workbench.map_id;
  editorVersionId = workbench.map_version_id;
  loadedVersionNumber = Number(workbench.version);
  clearPaintHistory();
  return workbench;
}

function updatePoiOverlayButton() {
  if (!poiOverlayBtn) return;
  poiOverlayBtn.setAttribute("aria-pressed", String(state.showPoiOverlay));
  poiOverlayBtn.classList.toggle("active", state.showPoiOverlay);
  poiOverlayBtn.textContent = state.showPoiOverlay ? "POI ✓" : "POI";
}

function canvasPixelRatio() {
  const rect = canvas.getBoundingClientRect();
  if (!rect.width) return 1;
  return canvas.width / rect.width;
}

function updateZoomLabel() {
  const cssScale = state.view.scale / canvasPixelRatio();
  zoomLabel.textContent = `${Math.round(cssScale * 100)}%`;
}

function redraw() {
  requestMapDraw(canvas, state.map);
  updateZoomLabel();
  updateMapSummary();
}

function clampScale(value) {
  const ratio = canvasPixelRatio();
  return Math.max(ratio * .0005, Math.min(ratio * 4, value));
}

// Default editor view: one world pixel equals one CSS/display pixel.
// Large maps therefore open at a useful editing scale instead of being
// automatically crushed into the viewport. "Ajuster" still gives a full-map view.
function resetViewOneToOne() {
  resizeCanvasToDisplaySize(canvas);
  state.view = { scale: canvasPixelRatio(), panX: 0, panY: 0 };
  redraw();
}

function fitMap() {
  resizeCanvasToDisplaySize(canvas);
  if (!state.map?.width || !state.map?.height) {
    state.view = { scale: 1, panX: 0, panY: 0 };
    redraw();
    return;
  }
  const size = Number(state.map.hex_size || 32);
  const w = Number(state.map.width);
  const h = Number(state.map.height);
  const q0 = -Math.floor(w / 2);
  const q1 = q0 + w - 1;
  const corners = [
    axialToPixel(q0, -Math.floor(h/2) - Math.floor((q0 + (q0 & 1))/2), size),
    axialToPixel(q1, -Math.floor(h/2) - Math.floor((q1 + (q1 & 1))/2), size),
    axialToPixel(q0, h-1-Math.floor(h/2) - Math.floor((q0 + (q0 & 1))/2), size),
    axialToPixel(q1, h-1-Math.floor(h/2) - Math.floor((q1 + (q1 & 1))/2), size),
  ];
  const minX = Math.min(...corners.map(p=>p.x)) - size;
  const maxX = Math.max(...corners.map(p=>p.x)) + size;
  const minY = Math.min(...corners.map(p=>p.y)) - size;
  const maxY = Math.max(...corners.map(p=>p.y)) + size;
  const padding = 50;
  state.view.scale = clampScale(Math.min((canvas.width-padding*2)/(maxX-minX), (canvas.height-padding*2)/(maxY-minY), 1.5 * canvasPixelRatio()));
  state.view.panX = -((minX+maxX)/2) * state.view.scale;
  state.view.panY = -((minY+maxY)/2) * state.view.scale;
  redraw();
}

function zoomAt(factor, clientX = null, clientY = null) {
  resizeCanvasToDisplaySize(canvas);
  const oldScale = state.view.scale;
  const nextScale = clampScale(oldScale * factor);
  if (nextScale === oldScale) return;
  const rect = canvas.getBoundingClientRect();
  const sx = clientX == null ? canvas.width / 2 : (clientX - rect.left) * (canvas.width / rect.width);
  const sy = clientY == null ? canvas.height / 2 : (clientY - rect.top) * (canvas.height / rect.height);
  const centerX = canvas.width / 2 + state.view.panX;
  const centerY = canvas.height / 2 + state.view.panY;
  const worldX = (sx - centerX) / oldScale;
  const worldY = (sy - centerY) / oldScale;
  state.view.scale = nextScale;
  state.view.panX = sx - canvas.width / 2 - worldX * nextScale;
  state.view.panY = sy - canvas.height / 2 - worldY * nextScale;
  redraw();
}

function setBrush(on) {
  state.isBrushOn = on;
  brushBtn.classList.toggle("active", on);
  brushBtn.textContent = on ? "Désactiver le pinceau" : "Activer le pinceau";
  brushStatus.textContent = on ? "Pinceau actif" : "Pinceau désactivé";
  canvas.classList.toggle("painting", on);
  updateMapSummary();
}

function setSaveModeUI() {
  if (!editorVersionId) {
    saveModeWrap.classList.add("hidden");
    persistMapName.disabled = false;
    persistMapBtn.textContent = "Créer la carte v1";
    return;
  }
  saveModeWrap.classList.remove("hidden");
  updateVersionNumber.textContent = loadedVersionNumber ?? "?";
  const mode = document.querySelector('input[name="save-mode"]:checked')?.value || "update";
  const updating = mode === "update";
  persistMapName.disabled = !updating;
  persistMapBtn.textContent = updating ? `Mettre à jour v${loadedVersionNumber}` : "Créer une nouvelle version";
  if (!updating && loadedVersionNumber != null) {
    if (!persistVersionName.value || persistVersionName.dataset.auto === "1") {
      persistVersionName.value = `Version ${loadedVersionNumber + 1}`;
      persistVersionName.dataset.auto = "1";
    }
  }
}

function updateUrlContext() {
  const url = new URL(location.href);
  editorMapId ? url.searchParams.set("map", editorMapId) : url.searchParams.delete("map");
  editorVersionId ? url.searchParams.set("version", editorVersionId) : url.searchParams.delete("version");
  history.replaceState(null, "", url);
  if (editorWorldLink) {
    const world = new URL("/world.html", location.origin);
    if (editorCampaignId) world.searchParams.set("campaign", editorCampaignId);
    if (editorVersionId) world.searchParams.set("version", editorVersionId);
  editorWorldLink.href = world.pathname + world.search;
  }
}

async function fetchJson(url, options = {}) {
  const response = await authFetch(url, options);
  let body = null;
  try { body = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : `${response.status} ${response.statusText}`);
  return body;
}

async function refreshPersistedVersionOptions(selectVersionId = editorVersionId) {
  if (!editorCampaignId) return;
  const dashboard = await fetchJson(`/api/campaigns/${editorCampaignId}/dm-dashboard`);
  persistedVersionSelect.innerHTML = '<option value="">— Choisir une carte/version —</option>';
  for (const map of dashboard.maps) {
    for (const version of map.versions) {
      const option = document.createElement("option");
      option.value = String(version.id);
      option.dataset.mapId = String(map.id);
      option.dataset.mapName = map.name;
      option.dataset.versionNumber = String(version.version);
      option.dataset.versionName = version.name || "";
      option.dataset.minute = String(version.effective_from_game_minute);
      option.textContent = `${map.name} · v${version.version}${version.name ? ` · ${version.name}` : ""} · ${formatGameDate(version.effective_from_game_minute)}`;
      if (version.id === selectVersionId) option.selected = true;
      persistedVersionSelect.appendChild(option);
    }
  }
  return dashboard;
}

async function loadPersistedVersion(versionId = null) {
  const selected = versionId
    ? [...persistedVersionSelect.options].find(o => Number(o.value) === Number(versionId))
    : persistedVersionSelect.selectedOptions[0];
  if (!selected?.value) return setMessage("Choisis une carte/version à charger.", true);
  const mapId = Number(selected.dataset.mapId);
  const selectedVersionId = Number(selected.value);
  setMessage("Chargement de la version persistée…");
  try {
    const body = await loadWorkbenchIntoCanvas(selectedVersionId);
    persistMapName.value = selected.dataset.mapName || `Map #${mapId}`;
    persistVersionName.value = selected.dataset.versionName || `Version ${body.version}`;
    persistVersionName.dataset.auto = "0";
    setDateInputs("persist-time", Number(selected.dataset.minute || 0));
    campaignContextLabel.textContent = `Map #${mapId} · v${body.version} (#${body.map_version_id})`;
    updateUrlContext();
    setSaveModeUI();
    await refreshPoiOverlay();
    resetViewOneToOne();
    setMessage(`${body.hex_count} hex chargés. Tu peux mettre à jour cette version ou en créer une nouvelle.`);
  } catch (error) { setMessage(error.message, true); }
}

async function initCampaignContext() {
  if (!editorCampaignId) return;
  campaignSavePanel.classList.remove("hidden");
  editorDmLink.href = `/dm.html?campaign=${editorCampaignId}`;
  updateUrlContext();
  try {
    const campaign = await fetchJson(`/api/campaigns/${editorCampaignId}`);
    campaignNameLabel.textContent = campaign.name;
    campaignContextLabel.textContent = `Campagne #${campaign.id} · nouveau brouillon`;
    await refreshPersistedVersionOptions(editorVersionId);
    if (editorVersionId) await loadPersistedVersion(editorVersionId);
  } catch (error) { setMessage(error.message, true); }
}

async function createNewMap(event) {
  event.preventDefault();
  const width = Number($("#new-map-width").value);
  const height = Number($("#new-map-height").value);
  const hexSize = Number($("#new-map-hex-size").value);
  if (!Number.isInteger(width) || !Number.isInteger(height) || !Number.isInteger(hexSize) || width < 1 || height < 1 || width > 10000 || height > 10000 || hexSize < 8) {
    return setMessage("Dimensions invalides : maximum 10 000×10 000 hex.", true);
  }
  const createBtn = $("#confirm-new-map-btn");
  let body;
  createBtn.disabled = true;
  createBtn.textContent = "Création…";
  try {
    await flushPendingPaint();
    body = await createMap(
      editorCampaignId,
      width,
      height,
      hexSize,
      persistMapName.value.trim() || "Carte principale",
      persistVersionName.value.trim() || "Initial version",
      gameMinuteFromDateInputs("persist-time"),
    );
    await refreshPersistedVersionOptions(body.map_version_id);
    await loadWorkbenchIntoCanvas(body.map_version_id);
  } catch (error) {
    setMessage(error.message, true);
    return;
  } finally {
    createBtn.disabled = false;
    createBtn.textContent = "Créer le brouillon";
  }
  editorMapId = body.map_id;
  editorVersionId = body.map_version_id;
  state.editorPois = [];
  loadedVersionNumber = null;
  persistMapName.disabled = false;
  persistMapName.value = "Carte principale";
  persistVersionName.value = "Initial version";
  persistVersionName.dataset.auto = "0";
  setDateInputs("persist-time", 0);
  campaignContextLabel.textContent = `Campagne #${editorCampaignId} · carte #${body.map_id}`;
  updateUrlContext();
  setSaveModeUI();
  modal.classList.add("hidden");
  resetViewOneToOne();
  setMessage("Carte persistée créée. Les peintures sont enregistrées automatiquement.");
}

async function reloadDraft() {
  try {
    await flushPendingPaint();
    if (!editorVersionId) return setMessage("Aucune version persistée n'est chargée.", true);
    await loadWorkbenchIntoCanvas(editorVersionId);
    redraw();
  } catch (error) { setMessage(error.message, true); }
}

async function persistEditorMap() {
  if (!editorCampaignId || !state.map?.hexes) return;
  const mode = editorVersionId ? (document.querySelector('input[name="save-mode"]:checked')?.value || "update") : "create";
  setMessage("Synchronisation du pinceau…");
  try {
    await flushPendingPaint();
    setMessage("Sauvegarde…");
    let body;
    if (mode === "update") {
      body = await fetchJson(`/api/campaigns/${editorCampaignId}/dm-maps/${editorMapId}/versions/${editorVersionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          map_name: persistMapName.value.trim(),
          version_name: persistVersionName.value.trim() || null,
          effective_from_game_minute: gameMinuteFromDateInputs("persist-time"),
        }),
      });
      setMessage(`Carte #${body.map_id} · v${body.version} mise à jour · ${body.hex_count} hex.`);
    } else if (mode === "new-version") {
      body = await fetchJson(`/api/campaigns/${editorCampaignId}/dm-maps/${editorMapId}/versions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parent_version_id: editorVersionId,
          version_name: persistVersionName.value.trim() || null,
          effective_from_game_minute: gameMinuteFromDateInputs("persist-time"),
        }),
      });
      editorVersionId = body.map_version_id;
      loadedVersionNumber = body.version;
      await loadWorkbenchIntoCanvas(editorVersionId);
      updateUrlContext();
      setMessage(`Nouvelle version créée : carte #${body.map_id} · v${body.version} · ${body.hex_count} hex.`);
    } else {
      throw new Error("Crée d'abord une carte persistée avec le bouton Nouvelle.");
    }
    await refreshPersistedVersionOptions(editorVersionId);
    const selected = persistedVersionSelect.selectedOptions[0];
    if (selected?.value) {
      persistMapName.value = selected.dataset.mapName || persistMapName.value;
      persistVersionName.value = selected.dataset.versionName || persistVersionName.value;
    }
    setSaveModeUI();
    await refreshPoiOverlay();
  } catch (error) {
    const suffix = mode === "update" && /history|version/i.test(error.message) ? " — Utilise ‘Créer une nouvelle version’." : "";
    setMessage(error.message + suffix, true);
  }
}

function onPointerDown(event) {
  if (!state.map?.hexes) return;
  canvas.setPointerCapture?.(event.pointerId);
  // Space is a temporary navigation override, Photoshop/Figma style.
  // It never changes the selected tool: releasing Space restores the brush.
  if (state.spacePanning && event.button === 0) {
    state.isPanning = true;
    state.panMoved = false;
    state.panLastX = event.clientX;
    state.panLastY = event.clientY;
    canvas.classList.add("panning");
    return;
  }
  if (state.isBrushOn && event.button === 0) {
    state.isPainting = true;
    beginPaintStroke();
    const hex = mouseToHex(canvas, event);
    paintHexesBatchRadius(canvas, [hex]);
    state.lastPaintedHex = hex;
    return;
  }
  state.isPanning = true;
  state.panMoved = false;
  state.panLastX = event.clientX;
  state.panLastY = event.clientY;
  canvas.classList.add("panning");
}

function processPaintMove(event) {
  const currentHex = mouseToHex(canvas, event);
  if (state.lastPaintedHex?.q === currentHex.q && state.lastPaintedHex?.r === currentHex.r) return;
  const line = state.lastPaintedHex ? getHexLine(state.lastPaintedHex, currentHex) : [currentHex];
  paintHexesBatchRadius(canvas, line);
  state.lastPaintedHex = currentHex;
}

function onPointerMove(event) {
  if (state.isPainting && state.isBrushOn) {
    // Browsers can emit pointermove far above display refresh rate (500-1000 Hz
    // mice are common). Keep only the newest event and process at most once per
    // animation frame. getHexLine preserves a continuous logical stroke.
    pendingPaintEvent = event;
    if (!paintMoveFrame) {
      paintMoveFrame = requestAnimationFrame(() => {
        paintMoveFrame = 0;
        const latest = pendingPaintEvent;
        pendingPaintEvent = null;
        if (latest && state.isPainting && state.isBrushOn) processPaintMove(latest);
      });
    }
    return;
  }
  if (!state.isPanning) return;
  const rect = canvas.getBoundingClientRect();
  const dx = (event.clientX - state.panLastX) * (canvas.width / rect.width);
  const dy = (event.clientY - state.panLastY) * (canvas.height / rect.height);
  if (Math.abs(dx) + Math.abs(dy) > 1) state.panMoved = true;
  state.view.panX += dx;
  state.view.panY += dy;
  state.panLastX = event.clientX;
  state.panLastY = event.clientY;
  redraw();
}

function stopPointer(event) {
  const finishedPainting = state.isPainting;
  if (finishedPainting && pendingPaintEvent) {
    if (paintMoveFrame) cancelAnimationFrame(paintMoveFrame);
    paintMoveFrame = 0;
    const latest = pendingPaintEvent;
    pendingPaintEvent = null;
    processPaintMove(latest);
  }
  state.isPainting = false;
  state.isPanning = false;
  state.lastPaintedHex = null;
  canvas.classList.remove("panning");
  if (event?.pointerId != null) canvas.releasePointerCapture?.(event.pointerId);
  if (finishedPainting) {
    endPaintStroke();
    // Rebuild outlines/LOD once, after the interactive stroke, then synchronize
    // the sparse changes without blocking pointer movement.
    redraw();
    flushPendingPaint().catch(error => setMessage(error.message, true));
  }
}

function isTypingTarget(target) {
  return target instanceof HTMLInputElement
    || target instanceof HTMLTextAreaElement
    || target instanceof HTMLSelectElement
    || target?.isContentEditable;
}

function setSpacePanning(active) {
  if (state.spacePanning === active) return;
  state.spacePanning = active;
  canvas.classList.toggle("space-pan", active);

  // If Space is pressed while a brush stroke is active, stop that stroke.
  // The next pointerdown can immediately start panning without changing tools.
  if (active && state.isPainting) {
    if (paintMoveFrame) cancelAnimationFrame(paintMoveFrame);
    paintMoveFrame = 0;
    pendingPaintEvent = null;
    state.isPainting = false;
    state.lastPaintedHex = null;
    endPaintStroke();
    redraw();
    flushPendingPaint().catch(error => setMessage(error.message, true));
  }
}

window.addEventListener("keydown", async event => {
  if (isTypingTarget(event.target)) return;
  const mod = event.ctrlKey || event.metaKey;
  if (mod && event.key.toLowerCase() === "z") {
    event.preventDefault();
    try {
      const changed = event.shiftKey ? await redoPaint() : await undoPaint();
      if (changed) {
        redraw();
        setMessage(event.shiftKey ? "Rétabli." : "Annulé.");
      } else {
        setMessage(event.shiftKey ? "Rien à rétablir." : "Rien à annuler.");
      }
    } catch (error) { setMessage(error.message, true); }
    return;
  }
  if (event.code !== "Space") return;
  event.preventDefault();
  setSpacePanning(true);
});

window.addEventListener("keyup", event => {
  if (event.code !== "Space") return;
  if (!isTypingTarget(event.target)) event.preventDefault();
  setSpacePanning(false);
});

window.addEventListener("blur", () => setSpacePanning(false));

canvas.addEventListener("pointerdown", onPointerDown);
canvas.addEventListener("pointermove", onPointerMove);
canvas.addEventListener("pointerup", stopPointer);
canvas.addEventListener("pointercancel", stopPointer);
canvas.addEventListener("wheel", event => { event.preventDefault(); zoomAt(event.deltaY < 0 ? 1.12 : .89, event.clientX, event.clientY); }, { passive: false });
canvas.addEventListener("contextmenu", event => event.preventDefault());

newMapBtn.addEventListener("click", () => modal.classList.remove("hidden"));
cancelNewMapBtn.addEventListener("click", () => modal.classList.add("hidden"));
newMapForm.addEventListener("submit", createNewMap);
reloadMapBtn.addEventListener("click", reloadDraft);
brushBtn.addEventListener("click", () => setBrush(!state.isBrushOn));
radiusSlider.addEventListener("input", () => { state.brushRadius = Number(radiusSlider.value); radiusSliderValue.textContent = state.brushRadius; });
zoomInBtn.addEventListener("click", () => zoomAt(1.2));
zoomOutBtn.addEventListener("click", () => zoomAt(.83));
fitMapBtn.addEventListener("click", fitMap);
poiOverlayBtn?.addEventListener("click", () => { state.showPoiOverlay = !state.showPoiOverlay; updatePoiOverlayButton(); redraw(); });
loadPersistedBtn?.addEventListener("click", () => loadPersistedVersion());
persistMapBtn?.addEventListener("click", persistEditorMap);
document.querySelectorAll('input[name="save-mode"]').forEach(input => input.addEventListener("change", setSaveModeUI));
persistVersionName.addEventListener("input", () => persistVersionName.dataset.auto = "0");

if (window.ResizeObserver && canvasWrap) new ResizeObserver(() => redraw()).observe(canvasWrap);
window.addEventListener("resize", redraw);

(async function init() {
  try {
    await authReady;
    state.terrains = await fetchTerrains();
    createTerrainButtons();
    setBrush(false);
    setSaveModeUI();
    updatePoiOverlayButton();
    await initCampaignContext();
    if (editorVersionId) await loadWorkbenchIntoCanvas(editorVersionId);
    if (state.map?.hexes) resetViewOneToOne();
    else redraw();
  } catch (error) { setMessage(error.message, true); }
})();
