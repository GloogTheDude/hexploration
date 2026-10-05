import { formatGameDate } from './game_time.js';
import { axialToPixel, pixelToAxial, hexDistance } from "./hex_math.js";
import { authReady, authFetch } from './auth.js';

const params = new URLSearchParams(window.location.search);
const embeddedMode = params.get("embedded") === "1";
const displayMode = params.get("display") === "1";
let activePingUserId = 0;
if (embeddedMode) document.body.classList.add("embedded");
if (displayMode) document.body.classList.add("shared-display");

const canvas = document.querySelector("#player-canvas");
const ctx = canvas.getContext("2d");
const expeditionInput = document.querySelector("#expedition-id");
const loadBtn = document.querySelector("#load-btn");
const refreshBtn = document.querySelector("#refresh-btn");
const fitBtn = document.querySelector("#fit-btn");
const pingControls = document.querySelector("#ping-controls");
const pingColorControl = document.querySelector("#ping-color-control");
const pingColor = document.querySelector("#ping-color");
const pingToolbar = document.querySelector("#ping-toolbar");
const pingUserControl = document.querySelector("#ping-user-control");
const pingUser = document.querySelector("#ping-user");
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
let pingFlashUntil = 0;

function key(q, r) { return `${q},${r}`; }
function showToast(message) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    window.setTimeout(() => toast.classList.add("hidden"), 2200);
}
async function api(path, options = {}) {
    const response = await authFetch(path, {
        cache: "no-store",
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
    if (!state || state.expedition_status !== "ACTIVE") return [];
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
        ctx.globalAlpha = 1;
        ctx.fill();
        if (hex.visibility_state !== "VISIBLE") {
            // Heroes-style memory state: keep the terrain recognizable but
            // make it unmistakably stale compared with current vision.
            hexPath(p.x, p.y, size - 1);
            ctx.fillStyle = "rgba(2, 7, 9, .58)";
            ctx.fill();
        }
        ctx.strokeStyle = hex.visibility_state === "VISIBLE" ? "#a9d99a" : "#2f4150";
        ctx.lineWidth = hex.visibility_state === "VISIBLE" ? 2.4 : 1.15;
        ctx.stroke();
    }

    // Area features are clipped server-side to known cells, so lakes and
    // wetlands can be rendered without revealing their unexplored extent.
    for (const area of state.areas || []) {
        for (const cell of area.cells || []) {
            const knownHex = known.get(key(cell.q, cell.r));
            if (!knownHex) continue;
            const p = worldToScreen(cell.q, cell.r);
            hexPath(p.x, p.y, size - 2);
            ctx.save();
            ctx.globalAlpha = knownHex.visibility_state === "VISIBLE" ? .34 : .16;
            ctx.fillStyle = (area.feature_type === "LAKE" || area.feature_type === "INLAND_SEA")
                ? "#54a9d9" : area.feature_type === "WETLAND" ? "#6e9270" : "#b0a26c";
            ctx.fill();
            ctx.restore();
        }
    }

    // Semantic geometry is rendered only when the backend says the segment is
    // known.  SEEN segments stay visible as memory but are deliberately dimmer.
    for (const edge of state.edges || []) {
        const a = worldToScreen(edge.from_q, edge.from_r);
        const b = worldToScreen(edge.to_q, edge.to_r);
        const aHex = known.get(key(edge.from_q, edge.from_r));
        const bHex = known.get(key(edge.to_q, edge.to_r));
        const live = aHex?.visibility_state === "VISIBLE" && bHex?.visibility_state === "VISIBLE";
        ctx.save();
        ctx.globalAlpha = live ? 0.95 : 0.5;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = edge.feature_type === "RIVER" ? "#6fbce8" : edge.feature_type === "ROAD" ? "#d9c178" : "#c8a2d8";
        ctx.lineWidth = Math.max(2, 3 * view.scale);
        ctx.stroke();
        ctx.restore();
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
        const remembered = known.get(key(poi.q, poi.r))?.visibility_state !== "VISIBLE";
        ctx.save();
        ctx.globalAlpha = remembered ? 0.62 : 1;
        ctx.beginPath();
        ctx.arc(p.x, y, Math.max(5, 7 * view.scale), 0, Math.PI * 2);
        ctx.fillStyle = poi.exists === false ? "#9c7373" : "#ffd479";
        ctx.fill();
        ctx.strokeStyle = "#10151a";
        ctx.lineWidth = Math.max(2, 2.5 * view.scale);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(p.x, y, Math.max(8, 10 * view.scale), 0, Math.PI * 2);
        ctx.strokeStyle = "#f6e6a8";
        ctx.lineWidth = Math.max(1, 1.5 * view.scale);
        ctx.stroke();
        ctx.restore();
    }

    if (state.ping_q != null && state.ping_r != null) {
        const created = state.ping_created_at ? new Date(state.ping_created_at).getTime() : Date.now();
        const age = Date.now() - created;
        if (age < 3200 && Math.floor(age / 280) % 2 === 0) {
            const ping = worldToScreen(state.ping_q, state.ping_r);
            ctx.beginPath();
            ctx.arc(ping.x, ping.y, Math.max(10, 13 * view.scale), 0, Math.PI * 2);
            ctx.strokeStyle = state.ping_color || "#ff4f64";
            ctx.lineWidth = 4;
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(ping.x - 9, ping.y); ctx.lineTo(ping.x + 9, ping.y);
            ctx.moveTo(ping.x, ping.y - 9); ctx.lineTo(ping.x, ping.y + 9);
            ctx.stroke();
        }
    }

    if (state.dm_ping_q != null && state.dm_ping_r != null) {
        const created = state.dm_ping_created_at ? new Date(state.dm_ping_created_at).getTime() : Date.now();
        const age = Date.now() - created;
        if (age < 3200 && Math.floor(age / 280) % 2 === 0) {
            const ping = worldToScreen(state.dm_ping_q, state.dm_ping_r);
            const r = Math.max(11, 14 * view.scale);
            ctx.save();
            ctx.translate(ping.x, ping.y);
            ctx.rotate(Math.PI / 4);
            ctx.strokeStyle = state.dm_ping_color || "#55c7ff";
            ctx.lineWidth = 4;
            ctx.strokeRect(-r * .65, -r * .65, r * 1.3, r * 1.3);
            ctx.rotate(-Math.PI / 4);
            ctx.beginPath();
            ctx.moveTo(-8, -8); ctx.lineTo(8, 8);
            ctx.moveTo(8, -8); ctx.lineTo(-8, 8);
            ctx.stroke();
            ctx.restore();
        }
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
        ${state.expedition_status === "ACTIVE" ? "" : '<div><strong>Archive en lecture seule</strong></div>'}
        <div>Carte: <strong>${state.map_name}</strong> · v${state.map_version}</div>
        <div>Date: <strong>${formatGameDate(state.current_game_minute)}</strong></div>
        <div>Position: <strong>(${state.current_q}, ${state.current_r})</strong></div>
        <div>Météo: <strong>${state.weather_key || "—"}</strong></div>
        <div>Transport: <strong>${state.transport_key || "—"}</strong></div>
        <div>Hex connus: <strong>${state.hexes.length}</strong></div>`;

    poiList.classList.toggle("muted", state.pois.length === 0);
    poiList.innerHTML = state.pois.length ? state.pois.map(poi => `
        <div class="poi-card ${poi.exists === false ? "destroyed" : ""}" data-q="${poi.q}" data-r="${poi.r}">
            <strong>${escapeHtml(poi.name)}</strong>
            <div>${escapeHtml(poi.kind || "POI")} · (${poi.q}, ${poi.r})</div>
            <div>${escapeHtml(poi.state || "état inconnu")} · vu ${formatGameDate(poi.observed_game_minute)}</div>
            ${poi.description ? `<p>${escapeHtml(poi.description)}</p>` : ""}
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
        selectionLabel.textContent = state?.expedition_status === "ACTIVE"
            ? "Clique simplement un hex adjacent pour le ping."
            : "Expédition terminée · consultation historique en lecture seule.";
        hexInfo.textContent = "Aucun hex sélectionné.";
        return;
    }
    const known = knownMap().get(key(selected.q, selected.r));
    const distance = hexDistance({q: state.current_q, r: state.current_r}, selected);
    selectionLabel.textContent = state.expedition_status === "ACTIVE"
        ? `Clic sur (${selected.q}, ${selected.r})${distance === 1 ? " · ping envoyé si cliqué" : " · hors portée de ping"}`
        : "Archive · aucun ping possible.";
    hexInfo.classList.toggle("muted", !known);
    hexInfo.innerHTML = known ? `
        <div><strong>(${known.q}, ${known.r})</strong></div>
        <div>${known.visibility_state === "VISIBLE" ? "VISIBLE maintenant" : "VU · dernière observation connue"}</div>
        <div>Terrain: <strong>${escapeHtml(known.terrain_key)}</strong></div>
        <div>Élévation: ${known.elevation}</div>
        <div>Dernière observation: ${formatGameDate(known.observed_game_minute)}</div>` : `
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

async function loadMap({fit = false} = {}) {
    const id = Number(expeditionInput.value);
    if (!id) return;
    errorBox.textContent = "";
    bootstrapNote.textContent = "";
    try {
        if (!Object.keys(terrains).length) terrains = await api("/api/terrains");
        // Player display is read-only with regard to discovery. Merely opening
        // or polling the map must never create observations or reveal a POI.
        state = await api(`/api/expeditions/${id}/player-map`);
        selected = null;
        renderInfo();
        const pingUnavailable = state.expedition_status !== "ACTIVE" || !activePingUserId;
        pingControls?.classList.toggle("hidden", pingUnavailable);
        pingColorControl?.classList.toggle("hidden", pingUnavailable);
        updateSelection();
        if (fit) fitKnownMap(); else draw();
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

async function pingHex(target) {
    if (!state || state.expedition_status !== "ACTIVE" || !activePingUserId) return;
    if (hexDistance({q: state.current_q, r: state.current_r}, target) !== 1) return;
    const previousPing = {
        q: state.ping_q, r: state.ping_r, gameMinute: state.ping_game_minute,
        userId: state.ping_user_id, username: state.ping_username,
        color: state.ping_color, createdAt: state.ping_created_at,
    };
    // Immediate local feedback: a single click visibly pings before the round trip.
    state.ping_q = target.q;
    state.ping_r = target.r;
    state.ping_game_minute = state.current_game_minute;
    state.ping_user_id = activePingUserId;
    state.ping_color = pingColor?.value || "#ff4f64";
    state.ping_created_at = new Date().toISOString();
    pingFlashUntil = Date.now() + 3200;
    errorBox.textContent = "";
    draw();
    try {
        const result = await api(`/api/expeditions/${state.expedition_id}/ping?user_id=${activePingUserId}`, {
            method: "PUT",
            body: JSON.stringify({q: target.q, r: target.r}),
        });
        state.ping_q = result.q;
        state.ping_r = result.r;
        state.ping_game_minute = result.game_minute;
        state.ping_user_id = result.user_id;
        state.ping_username = result.username;
        state.ping_color = result.color;
        state.ping_created_at = result.created_at;
        pingFlashUntil = Date.now() + 3200;
        showToast(`Ping ${result.username || "joueur"} : (${result.q}, ${result.r})`);
        draw();
    } catch (error) {
        state.ping_q = previousPing.q; state.ping_r = previousPing.r;
        state.ping_game_minute = previousPing.gameMinute; state.ping_user_id = previousPing.userId;
        state.ping_username = previousPing.username; state.ping_color = previousPing.color;
        state.ping_created_at = previousPing.createdAt;
        errorBox.textContent = error.message;
        draw();
    }
}

async function loadPingColor() {
    if (!activePingUserId) {
        pingControls?.classList.add("hidden");
        pingColorControl?.classList.add("hidden");
        return;
    }
    try {
        const user = await api(`/api/users/${activePingUserId}`);
        pingColor.value = user.ping_color || "#ff4f64";
    } catch (_) {}
}

async function savePingColor() {
    if (!activePingUserId) return;
    try {
        const user = await api(`/api/users/${activePingUserId}/ping-color`, {
            method: "PUT", body: JSON.stringify({ping_color: pingColor.value}),
        });
        pingColor.value = user.ping_color;
        showToast("Couleur du ping enregistrée.");
    } catch (error) { errorBox.textContent = error.message; }
}


async function loadSharedPingUsers(expeditionId) {
    if (!displayMode || !expeditionId || !pingUser) return;
    try {
        const participants = await api(`/api/expeditions/${expeditionId}/characters`);
        const ownerIds = [];
        const owners = [];
        for (const participant of participants) {
            const character = await api(`/api/characters/${participant.character_id}`);
            if (!ownerIds.includes(character.owner_user_id)) {
                ownerIds.push(character.owner_user_id);
                const owner = await api(`/api/users/${character.owner_user_id}`);
                owners.push(owner);
            }
        }
        if (!owners.length) return;
        pingUser.innerHTML = owners.map(u => `<option value="${u.id}">${u.username}</option>`).join("");
        activePingUserId = owners[0].id;
        pingUserControl?.classList.remove("hidden");
        await loadPingColor();
    } catch (error) {
        errorBox.textContent = error.message;
    }
}

pingUser?.addEventListener("change", async () => {
    activePingUserId = Number(pingUser.value) || 0;
    await loadPingColor();
});

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
        if (state.expedition_status === "ACTIVE" && activePingUserId) pingHex(selected);
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
pingColor?.addEventListener("change", savePingColor);
window.addEventListener("resize", resizeCanvas);

// ResizeObserver catches grid/sidebar/font changes that do not emit a window
// resize event. The first requestAnimationFrame waits for the initial layout
// before allocating the backing bitmap.
const canvasResizeObserver = new ResizeObserver(() => draw());
canvasResizeObserver.observe(canvas);
requestAnimationFrame(() => resizeCanvas());

const initialExpedition = Number(new URLSearchParams(window.location.search).get("expedition"));
authReady.then(async () => {
activePingUserId = (await import('./auth.js')).getCurrentUser()?.id || 0;
loadPingColor();
if (initialExpedition) {
    expeditionInput.value = String(initialExpedition);
    if (displayMode) {
        loadSharedPingUsers(initialExpedition).finally(() => loadMap({fit: true}));
    } else {
        loadMap({fit: true});
    }
}
});

window.setInterval(() => { if (state && document.visibilityState === "visible") loadMap().catch?.(()=>{}); }, 900);
window.setInterval(() => { if (state && state.ping_created_at) draw(); }, 140);
