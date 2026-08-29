import { axialToPixel, pixelToAxial, hexDistance } from "./hex_math.js";

const embeddedMode = new URLSearchParams(window.location.search).get("embedded") === "1";
if (embeddedMode) document.body.classList.add("embedded");

const canvas = document.querySelector("#player-canvas");
const ctx = canvas.getContext("2d");
const expeditionInput = document.querySelector("#expedition-id");
const loadBtn = document.querySelector("#load-btn");
const refreshBtn = document.querySelector("#refresh-btn");
const fitBtn = document.querySelector("#fit-btn");
const moveBtn = document.querySelector("#move-btn");
const durationInput = document.querySelector("#base-duration");
const info = document.querySelector("#expedition-info");
const hexInfo = document.querySelector("#hex-info");
const selectionLabel = document.querySelector("#selection-label");
const poiList = document.querySelector("#poi-list");
const errorBox = document.querySelector("#error");
const bootstrapNote = document.querySelector("#bootstrap-note");
const toast = document.querySelector("#toast");

const DIRECTIONS = [
    {q: 1, r: 0}, {q: 1, r: -1}, {q: 0, r: -1},
    {q: -1, r: 0}, {q: -1, r: 1}, {q: 0, r: 1},
];

const terrainFallback = {
    PLAIN: "#7b9655", SEA: "#3f6d99", SWAMP: "#5d7052", HILL: "#8d8057",
    FOREST: "#426742", DEEP_FOREST: "#294a34", LOW_MOUNTAIN: "#77736c",
    MOUNTAIN: "#6c6a69", HIGH_MOUNTAIN: "#9a9996",
};

let state = null;
let terrains = {};
let selected = null;
let view = { scale: 1, offsetX: 0, offsetY: 0 };
let dragging = false;
let dragStart = null;
let dragMoved = false;

function key(q, r) { return `${q},${r}`; }
function showToast(message) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    window.setTimeout(() => toast.classList.add("hidden"), 2200);
}
async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: {"Content-Type": "application/json", ...(options.headers || {})},
        ...options,
    });
    if (!response.ok) {
        let detail = `${response.status} ${response.statusText}`;
        try {
            const body = await response.json();
            detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
        } catch (_) {}
        throw new Error(detail);
    }
    return response.json();
}

function syncCanvasResolution() {
    // Canvas has two sizes: its CSS display size and its backing bitmap size.
    // If the module runs while the grid is still settling, getBoundingClientRect()
    // can temporarily report a tiny size. Drawing into that bitmap and letting CSS
    // stretch it can turn the current-position dot into a full-canvas solid block.
    // Re-sync on every render so the bitmap always matches the final layout.
    const cssWidth = Math.max(1, Math.round(canvas.clientWidth));
    const cssHeight = Math.max(1, Math.round(canvas.clientHeight));
    const ratio = Math.max(1, window.devicePixelRatio || 1);
    const targetWidth = Math.max(1, Math.round(cssWidth * ratio));
    const targetHeight = Math.max(1, Math.round(cssHeight * ratio));

    if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
        canvas.width = targetWidth;
        canvas.height = targetHeight;
    }

    // Setting canvas.width/height resets the whole context state, so always
    // restore the CSS-pixel transform, even when only one dimension changed.
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return {width: cssWidth, height: cssHeight};
}

function resizeCanvas() {
    draw();
}

function worldToScreen(q, r) {
    const size = (state?.hex_size || 32) * view.scale;
    const pixel = axialToPixel(q, r, size);
    return {
        x: canvas.clientWidth / 2 + view.offsetX + pixel.x,
        y: canvas.clientHeight / 2 + view.offsetY + pixel.y,
    };
}

function screenToHex(x, y) {
    const size = (state?.hex_size || 32) * view.scale;
    const localX = x - canvas.clientWidth / 2 - view.offsetX;
    const localY = y - canvas.clientHeight / 2 - view.offsetY;
    return pixelToAxial(localX, localY, size);
}

function hexPath(x, y, size) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 180 * (60 * i);
        const px = x + size * Math.cos(angle);
        const py = y + size * Math.sin(angle);
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.closePath();
}

function terrainColor(terrainKey) {
    return terrains[terrainKey]?.color || terrainFallback[terrainKey] || "#59697a";
}

function knownMap() {
    return new Map((state?.hexes || []).map(hex => [key(hex.q, hex.r), hex]));
}

function ghostNeighbors() {
    if (!state) return [];
    return DIRECTIONS.map(d => ({q: state.current_q + d.q, r: state.current_r + d.r}));
}

function drawUnknownShell(q, r, size, {current = false} = {}) {
    const p = worldToScreen(q, r);
    hexPath(p.x, p.y, size - 1);
    ctx.fillStyle = current ? "#15202a" : "#111820";
    ctx.fill();
    ctx.setLineDash([5, 5]);
    ctx.strokeStyle = current ? "#668099" : "#465565";
    ctx.lineWidth = current ? 2 : 1.5;
    ctx.stroke();
    ctx.setLineDash([]);
}

function draw() {
    const {width, height} = syncCanvasResolution();
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#0b0e12";
    ctx.fillRect(0, 0, width, height);
    if (!state) return;

    const size = state.hex_size * view.scale;
    const known = knownMap();

    // Always render a shell under the current position. This makes a legacy
    // expedition visible even before its first fog-of-war bootstrap.
    if (!known.has(key(state.current_q, state.current_r))) {
        drawUnknownShell(state.current_q, state.current_r, size, {current: true});
    }

    // Unknown adjacent coordinates are shown only as generic movement choices.
    for (const tile of ghostNeighbors()) {
        if (known.has(key(tile.q, tile.r))) continue;
        drawUnknownShell(tile.q, tile.r, size);
    }

    for (const hex of state.hexes) {
        const p = worldToScreen(hex.q, hex.r);
        hexPath(p.x, p.y, size - 1);
        ctx.fillStyle = terrainColor(hex.terrain_key);
        ctx.globalAlpha = hex.discovery_state === "SEEN" ? 0.58 : 0.92;
        ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = hex.discovery_state === "VISITED" ? "#e6c56a" : "#344454";
        ctx.lineWidth = hex.discovery_state === "VISITED" ? 2.5 : 1.2;
        ctx.stroke();
    }

    if (selected) {
        const p = worldToScreen(selected.q, selected.r);
        hexPath(p.x, p.y, size - 3);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 3;
        ctx.stroke();
    }

    for (const poi of state.pois) {
        const p = worldToScreen(poi.q, poi.r);
        const y = p.y - size * 0.15;
        ctx.beginPath();
        ctx.arc(p.x, y, Math.max(4, 6 * view.scale), 0, Math.PI * 2);
        ctx.fillStyle = poi.exists === false ? "#9c7373" : "#ffd479";
        ctx.fill();
        ctx.strokeStyle = "#13171b";
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    const current = worldToScreen(state.current_q, state.current_r);
    ctx.beginPath();
    ctx.arc(current.x, current.y, Math.max(6, 8 * view.scale), 0, Math.PI * 2);
    ctx.fillStyle = "#eef7ff";
    ctx.fill();
    ctx.strokeStyle = "#1d76b8";
    ctx.lineWidth = 4;
    ctx.stroke();
}

function fitKnownMap() {
    if (!state) return;
    const coords = [...state.hexes, {q: state.current_q, r: state.current_r}, ...ghostNeighbors()];
    const rawSize = state.hex_size;
    const points = coords.map(h => axialToPixel(h.q, h.r, rawSize));
    const minX = Math.min(...points.map(p => p.x));
    const maxX = Math.max(...points.map(p => p.x));
    const minY = Math.min(...points.map(p => p.y));
    const maxY = Math.max(...points.map(p => p.y));
    const mapW = Math.max(rawSize * 3, maxX - minX + rawSize * 3);
    const mapH = Math.max(rawSize * 3, maxY - minY + rawSize * 3);
    view.scale = Math.min(2, Math.max(.35, Math.min(canvas.clientWidth / mapW, canvas.clientHeight / mapH) * .82));
    const centerRawX = (minX + maxX) / 2;
    const centerRawY = (minY + maxY) / 2;
    view.offsetX = -centerRawX * view.scale;
    view.offsetY = -centerRawY * view.scale;
    draw();
}

function renderInfo() {
    if (!state) return;
    info.classList.remove("muted");
    info.innerHTML = `
        <div><strong>${state.expedition_name}</strong> · ${state.expedition_status}</div>
        <div>Carte: <strong>${state.map_name}</strong> · v${state.map_version}</div>
        <div>Minute: <strong>${state.current_game_minute}</strong></div>
        <div>Position: <strong>(${state.current_q}, ${state.current_r})</strong></div>
        <div>Météo: <strong>${state.weather_key || "—"}</strong></div>
        <div>Transport: <strong>${state.transport_key || "—"}</strong></div>
        <div>Hex connus: <strong>${state.hexes.length}</strong></div>`;

    poiList.classList.toggle("muted", state.pois.length === 0);
    poiList.innerHTML = state.pois.length ? state.pois.map(poi => `
        <div class="poi-card ${poi.exists === false ? "destroyed" : ""}" data-q="${poi.q}" data-r="${poi.r}">
            <strong>${escapeHtml(poi.name)}</strong>
            <div>${escapeHtml(poi.kind || "POI")} · (${poi.q}, ${poi.r})</div>
            <div>${escapeHtml(poi.state || "état inconnu")} · vu m.${poi.observed_game_minute}</div>
        </div>`).join("") : "Aucun POI connu.";
    poiList.querySelectorAll(".poi-card").forEach(card => card.addEventListener("click", () => {
        selected = {q: Number(card.dataset.q), r: Number(card.dataset.r)};
        centerOn(selected.q, selected.r);
        updateSelection();
    }));
}

function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
}

function updateSelection() {
    if (!state || !selected) {
        moveBtn.disabled = true;
        selectionLabel.textContent = "Sélectionne un hex adjacent.";
        hexInfo.textContent = "Aucun hex sélectionné.";
        return;
    }
    const known = knownMap().get(key(selected.q, selected.r));
    const distance = hexDistance({q: state.current_q, r: state.current_r}, selected);
    const adjacent = distance === 1;
    selectionLabel.textContent = `Destination: (${selected.q}, ${selected.r})${known ? "" : " · inconnue"}`;
    moveBtn.disabled = !adjacent || state.expedition_status !== "ACTIVE";
    hexInfo.classList.toggle("muted", !known);
    hexInfo.innerHTML = known ? `
        <div><strong>(${known.q}, ${known.r})</strong></div>
        <div>${known.discovery_state}</div>
        <div>Terrain: <strong>${escapeHtml(known.terrain_key)}</strong></div>
        <div>Élévation: ${known.elevation}</div>
        <div>Dernière observation: m.${known.observed_game_minute}</div>` : `
        <div><strong>(${selected.q}, ${selected.r})</strong></div>
        <div>UNKNOWN — aucune donnée terrain révélée.</div>`;
    draw();
}

function centerOn(q, r) {
    const raw = axialToPixel(q, r, state.hex_size);
    view.offsetX = -raw.x * view.scale;
    view.offsetY = -raw.y * view.scale;
    draw();
}

async function loadMap({fit = false, allowBootstrap = true} = {}) {
    const id = Number(expeditionInput.value);
    if (!id) return;
    errorBox.textContent = "";
    bootstrapNote.textContent = "";
    try {
        if (!Object.keys(terrains).length) terrains = await api("/api/terrains");
        state = await api(`/api/expeditions/${id}/player-map`);

        if (allowBootstrap && state.expedition_status === "ACTIVE" && state.hexes.length === 0) {
            bootstrapNote.textContent = "Initialisation de la visibilité à la position actuelle…";
            const bootstrap = await api(`/api/expeditions/${id}/player-map/bootstrap`, {method: "POST"});
            if (bootstrap.initialized) {
                bootstrapNote.textContent = `Visibilité initialisée maintenant: ${bootstrap.map_observations_created} hex, ${bootstrap.poi_observations_created} POI.`;
                state = await api(`/api/expeditions/${id}/player-map`);
            } else {
                bootstrapNote.textContent = "La connaissance cartographique était déjà initialisée.";
            }
        }

        selected = null;
        renderInfo();
        updateSelection();
        if (fit) fitKnownMap(); else draw();
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

async function move() {
    if (!state || !selected || moveBtn.disabled) return;
    moveBtn.disabled = true;
    try {
        const movement = await api(`/api/expeditions/${state.expedition_id}/move`, {
            method: "POST",
            body: JSON.stringify({
                to_q: selected.q,
                to_r: selected.r,
                base_duration_minutes: Number(durationInput.value) || 60,
            }),
        });
        showToast(`Arrivée minute ${movement.arrival_game_minute} (+${movement.effective_duration_minutes} min)`);
        await loadMap();
        centerOn(state.current_q, state.current_r);
    } catch (error) {
        errorBox.textContent = error.message;
        updateSelection();
    }
}

canvas.addEventListener("pointerdown", event => {
    dragging = true; dragMoved = false;
    dragStart = {x: event.clientX, y: event.clientY, offsetX: view.offsetX, offsetY: view.offsetY};
    canvas.classList.add("dragging");
    canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", event => {
    if (!dragging) return;
    const dx = event.clientX - dragStart.x;
    const dy = event.clientY - dragStart.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) dragMoved = true;
    view.offsetX = dragStart.offsetX + dx;
    view.offsetY = dragStart.offsetY + dy;
    draw();
});
canvas.addEventListener("pointerup", event => {
    canvas.classList.remove("dragging");
    if (!dragging) return;
    dragging = false;
    if (!dragMoved && state) {
        const rect = canvas.getBoundingClientRect();
        selected = screenToHex(event.clientX - rect.left, event.clientY - rect.top);
        updateSelection();
    }
});
canvas.addEventListener("wheel", event => {
    if (!state) return;
    event.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    const before = screenToHex(mouseX, mouseY);
    const oldScale = view.scale;
    view.scale = Math.min(3.5, Math.max(.25, view.scale * (event.deltaY < 0 ? 1.12 : .89)));
    const oldPixel = axialToPixel(before.q, before.r, state.hex_size * oldScale);
    const newPixel = axialToPixel(before.q, before.r, state.hex_size * view.scale);
    view.offsetX += oldPixel.x - newPixel.x;
    view.offsetY += oldPixel.y - newPixel.y;
    draw();
}, {passive: false});

loadBtn.addEventListener("click", () => loadMap({fit: true}));
refreshBtn.addEventListener("click", () => loadMap());
fitBtn.addEventListener("click", fitKnownMap);
moveBtn.addEventListener("click", move);
window.addEventListener("resize", resizeCanvas);

// ResizeObserver catches grid/sidebar/font changes that do not emit a window
// resize event. The first requestAnimationFrame waits for the initial layout
// before allocating the backing bitmap.
const canvasResizeObserver = new ResizeObserver(() => draw());
canvasResizeObserver.observe(canvas);
requestAnimationFrame(() => resizeCanvas());

const initialExpedition = Number(new URLSearchParams(window.location.search).get("expedition"));
if (initialExpedition) {
    expeditionInput.value = String(initialExpedition);
    loadMap({fit: true});
}
