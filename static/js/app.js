import { state } from "./state.js";
import { fetchMap, fetchTerrains, createMap } from "./api.js";
import { drawMap } from "./renderer.js";
import { createTerrainButtons } from "./ui.js";
import { mouseToHex, paintHexesBatchRadius } from "./tools.js";
import { getHexLine } from "./hex_math.js";

const canvas = document.getElementById("hex-canvas");
const loadMapBtn = document.getElementById("load-map-btn");
const paintMapBtn = document.getElementById("paint-map-btn");
const newMapBtn = document.getElementById("new-map-btn");
const modal = document.getElementById("new-map-modal");
const confirmNewMapBtn = document.getElementById("confirm-new-map-btn");
const cancelNewMapBtn = document.getElementById("cancel-new-map-btn");
const brushBtn = document.getElementById("brush-btn");
const radiusSlider = document.getElementById("radius-slider");
const radiusSliderValue = document.getElementById("radius-slider-value");

loadMapBtn.addEventListener("click", loadMap);
paintMapBtn.addEventListener("click", () => {});
newMapBtn.addEventListener("click", () => modal.classList.remove("hidden"));
cancelNewMapBtn.addEventListener("click", () => modal.classList.add("hidden"));
confirmNewMapBtn.addEventListener("click", createNewMap);

canvas.addEventListener("mousedown", onMouseDown);
canvas.addEventListener("mouseup", stopPainting);
canvas.addEventListener("mouseleave", stopPainting);
canvas.addEventListener("mousemove", onMouseMove);

brushBtn.addEventListener("click", onBrushBtnClicked);
radiusSlider.addEventListener("input", setRadius);

window.onload = async () => {
    state.terrains = await fetchTerrains();
    createTerrainButtons();
};

async function loadMap() {
    state.map = await fetchMap();
    drawMap(canvas, state.map);
}

async function createNewMap() {
    const width = document.getElementById("new-map-width").value;
    const height = document.getElementById("new-map-height").value;
    const hexSize = document.getElementById("new-map-hex-size").value;

    state.map = await createMap(width, height, hexSize);
    drawMap(canvas, state.map);
    modal.classList.add("hidden");
}

async function onMouseDown(event) {
    if (!state.isBrushOn) return;

    state.isPainting = true;
    const hex = mouseToHex(canvas, event);
    await paintHexesBatchRadius(canvas, [hex]);
    state.lastPaintedHex = hex;
}

async function onMouseMove(event) {
    if (!state.isBrushOn || !state.isPainting) return;

    const currentHex = mouseToHex(canvas, event);

    if (state.lastPaintedHex === null) {
        await paintHexesBatchRadius(canvas, [currentHex]);
        state.lastPaintedHex = currentHex;
        return;
    }

    const line = getHexLine(state.lastPaintedHex, currentHex);
    await paintHexesBatchRadius(canvas, line);
    state.lastPaintedHex = currentHex;
}

function stopPainting() {
    state.isPainting = false;
    state.lastPaintedHex = null;
}

function onBrushBtnClicked() {
    state.isBrushOn = !state.isBrushOn;
    brushBtn.classList.toggle("active", state.isBrushOn);
}

function setRadius() {
    state.brushRadius = parseInt(radiusSlider.value);
    radiusSliderValue.textContent = state.brushRadius;
}


// v23 — campaign-aware persistence + true MapVersion editing.
const editorParams = new URL(location.href).searchParams;
const editorUserId = Number(editorParams.get("user"));
const editorCampaignId = Number(editorParams.get("campaign"));
const editorMapId = Number(editorParams.get("map"));
const editorParentVersionId = Number(editorParams.get("version"));
const campaignSavePanel = document.getElementById("campaign-save-panel");
const campaignNameLabel = document.getElementById("editor-campaign-name");
const campaignContextLabel = document.getElementById("editor-campaign-context");
const persistMapBtn = document.getElementById("persist-map-btn");
const persistMapMessage = document.getElementById("persist-map-message");
const editorDmLink = document.getElementById("editor-dm-link");
const persistMapName = document.getElementById("persist-map-name");
const persistVersionName = document.getElementById("persist-version-name");
const persistEffectiveMinute = document.getElementById("persist-effective-minute");

async function loadPersistedVersionForEditing() {
    if (!editorMapId || !editorParentVersionId) return;
    persistMapMessage.textContent = "Chargement de la version persistée…";
    const response = await fetch(`/api/campaigns/${editorCampaignId}/dm-map-versions/${editorParentVersionId}/load-editor?user_id=${editorUserId}`, {method: "POST"});
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
    state.map = await fetchMap();
    drawMap(canvas, state.map);
    persistMapName.disabled = true;
    persistMapBtn.textContent = "Créer la nouvelle version";
    campaignContextLabel.textContent = `Map #${editorMapId} · parent v${body.version} (#${body.map_version_id}) · les POI/features gardent leur identité`;
    persistVersionName.value = `Version ${body.version + 1}`;
    persistEffectiveMinute.value = Math.max(Number(persistEffectiveMinute.value || 0), 1);
    persistMapMessage.textContent = `${body.hex_count} hex chargés depuis v${body.version}. Modifie le terrain puis crée la nouvelle version.`;
}

async function initCampaignContext() {
    if (!editorUserId || !editorCampaignId || !campaignSavePanel) return;
    campaignSavePanel.classList.remove("hidden");
    editorDmLink.href = `/dm.html?user=${editorUserId}&campaign=${editorCampaignId}`;
    try {
        const response = await fetch(`/api/campaigns/${editorCampaignId}`);
        if (!response.ok) throw new Error(`Campagne introuvable (${response.status})`);
        const campaign = await response.json();
        campaignNameLabel.textContent = campaign.name;
        campaignContextLabel.textContent = `Campaign #${campaign.id} · nouvelle carte`;
        if (editorParentVersionId) await loadPersistedVersionForEditing();
    } catch (error) {
        persistMapMessage.textContent = error.message;
    }
}

async function persistEditorMap() {
    if (!editorUserId || !editorCampaignId) return;
    persistMapMessage.textContent = "Sauvegarde…";
    try {
        let response;
        if (editorMapId && editorParentVersionId) {
            const payload = {
                parent_version_id: editorParentVersionId,
                version_name: persistVersionName.value.trim() || null,
                effective_from_game_minute: Number(persistEffectiveMinute.value),
            };
            response = await fetch(`/api/campaigns/${editorCampaignId}/dm-maps/${editorMapId}/versions/from-editor?user_id=${editorUserId}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
        } else {
            const payload = {
                name: persistMapName.value.trim(),
                description: null,
                version_name: persistVersionName.value.trim() || null,
                effective_from_game_minute: Number(persistEffectiveMinute.value),
            };
            response = await fetch(`/api/campaigns/${editorCampaignId}/dm-maps/from-editor?user_id=${editorUserId}`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(payload),
            });
        }
        const body = await response.json();
        if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
        persistMapMessage.innerHTML = `Carte #${body.map_id} · v${body.version} · ${body.hex_count} hex persistés. <a href="/dm.html?user=${editorUserId}&campaign=${editorCampaignId}">Retour dashboard MJ</a>`;
    } catch (error) {
        persistMapMessage.textContent = error.message;
    }
}

persistMapBtn?.addEventListener("click", persistEditorMap);
initCampaignContext();
