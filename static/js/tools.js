import { state } from "./state.js?v=320";
import { pixelToAxial } from "./hex_math.js?v=320";
import { paintHexesBatchRadiusApi, paintHexesExactApi } from "./api.js?v=320";
import { drawPaintPreview, drawBrushSegmentPreview, mapScreenCenter } from "./renderer.js?v=320";

const pendingCenters = new Map();
let syncTimer = null;
let inflight = Promise.resolve();
const SYNC_AFTER_STROKE_MS = 180;
const MAX_PENDING_CENTERS = 2500;
const MAX_HISTORY = 100;
let activeStrokeBefore = null;

export function mouseToHex(canvas, event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const sx = (event.clientX - rect.left) * scaleX;
  const sy = (event.clientY - rect.top) * scaleY;
  const center = mapScreenCenter(canvas);
  return pixelToAxial((sx - center.x) / state.view.scale, (sy - center.y) / state.view.scale, state.map.hex_size);
}

function axialToOffset(q, r) {
  const col = q + Math.floor(state.map.width / 2);
  const row = r + Math.floor((q + (q & 1)) / 2) + Math.floor(state.map.height / 2);
  return { col, row };
}

function inBounds(q, r) {
  const {col, row} = axialToOffset(q, r);
  return col >= 0 && row >= 0 && col < state.map.width && row < state.map.height;
}

const brushOffsetCache = new Map();

function brushOffsets(radius) {
  const effective = Math.max(0, radius - 1);
  if (brushOffsetCache.has(effective)) return brushOffsetCache.get(effective);
  const offsets = [];
  for (let dq = -effective; dq <= effective; dq++) {
    const drMin = Math.max(-effective, -dq - effective);
    const drMax = Math.min(effective, -dq + effective);
    for (let dr = drMin; dr <= drMax; dr++) offsets.push([dq, dr]);
  }
  brushOffsetCache.set(effective, offsets);
  return offsets;
}

function localCoordsInRadius(center, radius) {
  const out = [];
  for (const [dq, dr] of brushOffsets(radius)) {
    const q = center.q + dq;
    const r = center.r + dr;
    if (inBounds(q, r)) out.push({ q, r });
  }
  return out;
}

function cloneTile(tile) {
  if (!tile) return null;
  return { ...tile, terrain: tile.terrain ? { ...tile.terrain } : null, pois: [...(tile.pois || [])] };
}

function terrainKeyForTile(tile) {
  if (!tile) return state.map.default_terrain_key || "SEA";
  for (const [key, terrain] of Object.entries(state.terrains || {})) {
    if (tile.terrain?.type === terrain.type) return key;
  }
  return state.map.default_terrain_key || "SEA";
}

function applyPersistentWorkbench(workbench) {
  state.map.width = workbench.width;
  state.map.height = workbench.height;
  state.map.hex_size = workbench.hex_size;
  state.map.layout = "even-q-rect";
  state.map.sparse = Boolean(workbench.default_terrain_key);
  state.map.default_terrain_key = workbench.default_terrain_key || "SEA";
  state.map.hexes = {};
  for (const row of workbench.hexes || []) {
    const terrain = state.terrains[row.terrain_key];
    if (!terrain) continue;
    state.map.hexes[`${row.q},${row.r}`] = {
      q: row.q,
      r: row.r,
      terrain: { ...terrain, elevation: row.elevation, visibility_score: row.visibility_score, travel_cost: row.travel_cost },
      pois: [],
    };
  }
}

export function beginPaintStroke() {
  activeStrokeBefore = new Map();
}

export function endPaintStroke() {
  if (!activeStrokeBefore) return false;
  const before = [];
  const after = [];
  for (const [key, oldTile] of activeStrokeBefore.entries()) {
    const [q, r] = key.split(",").map(Number);
    before.push({ q, r, tile: cloneTile(oldTile) });
    after.push({ q, r, tile: cloneTile(state.map.hexes[key] || null) });
  }
  activeStrokeBefore = null;
  if (!before.length) return false;
  state.undoStack.push({ before, after });
  if (state.undoStack.length > MAX_HISTORY) state.undoStack.shift();
  state.redoStack = [];
  return true;
}

async function applyHistorySnapshot(snapshot) {
  await flushPendingPaint();
  const payload = [];
  for (const item of snapshot) {
    const key = `${item.q},${item.r}`;
    if (item.tile) state.map.hexes[key] = cloneTile(item.tile);
    else delete state.map.hexes[key];
    payload.push({ q: item.q, r: item.r, terrain_key: terrainKeyForTile(item.tile) });
  }
  const data = await paintHexesExactApi(payload);
  applyPersistentWorkbench(data);
}

export async function undoPaint() {
  const command = state.undoStack.pop();
  if (!command) return false;
  await applyHistorySnapshot(command.before);
  state.redoStack.push(command);
  return true;
}

export async function redoPaint() {
  const command = state.redoStack.pop();
  if (!command) return false;
  await applyHistorySnapshot(command.after);
  state.undoStack.push(command);
  return true;
}

export function clearPaintHistory() {
  state.undoStack = [];
  state.redoStack = [];
  activeStrokeBefore = null;
}

function applyLocalTerrain(q, r, terrain) {
  const key = `${q},${r}`;
  if (activeStrokeBefore && !activeStrokeBefore.has(key)) {
    activeStrokeBefore.set(key, cloneTile(state.map.hexes[key] || null));
  }
  const defaultKey = state.map.default_terrain_key || "SEA";
  if (state.selectedTerrainKey === defaultKey) {
    delete state.map.hexes[key];
    return { q, r, terrain: state.terrains[defaultKey], isDefault: true };
  }
  const tile = state.map.hexes[key] || { q, r, terrain };
  tile.terrain = terrain;
  state.map.hexes[key] = tile;
  return tile;
}

export function paintHexesBatchRadius(canvas, centers) {
  if (!state.selectedTerrainKey || !state.map.hexes || centers.length === 0) return;
  const terrain = state.terrains[state.selectedTerrainKey];
  if (!terrain) return;

  // A high polling-rate mouse can feed the same centers repeatedly. Deduplicate
  // before expanding the brush footprint: this matters a lot at overview zoom.
  const uniqueCenters = [];
  let previousKey = null;
  for (const center of centers) {
    const key = `${center.q},${center.r}`;
    if (key === previousKey) continue;
    previousKey = key;
    uniqueCenters.push(center);
    pendingCenters.set(key, { q: center.q, r: center.r });
  }

  const changed = new Map();
  for (const center of uniqueCenters) {
    for (const coord of localCoordsInRadius(center, state.brushRadius)) {
      const tile = applyLocalTerrain(coord.q, coord.r, terrain);
      changed.set(`${coord.q},${coord.r}`, tile);
    }
  }

  // Below ~60% CSS zoom the exact per-hex preview becomes more expensive than
  // useful: dozens/hundreds of logical hexes can pass under one mouse movement.
  // Draw one screen-space brush segment instead. The logical map still receives
  // every exact hex, and the canonical renderer rebuilds it when the stroke ends.
  const ratio = Math.max(1, canvas.width / Math.max(1, canvas.getBoundingClientRect().width));
  const cssZoom = state.view.scale / ratio;
  if (cssZoom < 0.60 && uniqueCenters.length > 1) {
    drawBrushSegmentPreview(canvas, uniqueCenters[0], uniqueCenters[uniqueCenters.length - 1], terrain, state.brushRadius);
  } else {
    drawPaintPreview(canvas, [...changed.values()]);
  }
  scheduleSync();
}

function scheduleSync() {
  if (pendingCenters.size >= MAX_PENDING_CENTERS) {
    if (syncTimer) clearTimeout(syncTimer);
    syncTimer = null;
    flushPendingPaint().catch(console.error);
    return;
  }
  if (syncTimer) clearTimeout(syncTimer);
  syncTimer = setTimeout(() => {
    syncTimer = null;
    // Network/server synchronization is intentionally kept out of an active
    // brush stroke. Pointer rendering stays entirely local and frame-budgeted.
    if (state.isPainting) {
      scheduleSync();
      return;
    }
    flushPendingPaint().catch(console.error);
  }, SYNC_AFTER_STROKE_MS);
}

export async function flushPendingPaint() {
  if (syncTimer) {
    clearTimeout(syncTimer);
    syncTimer = null;
  }
  if (!pendingCenters.size || !state.selectedTerrainKey) return inflight;
  const centers = [...pendingCenters.values()];
  pendingCenters.clear();
  const terrainKey = state.selectedTerrainKey;
  const radius = state.brushRadius;
  inflight = inflight.then(async () => {
    const data = await paintHexesBatchRadiusApi(centers, terrainKey, radius);
    // Server remains authoritative. The response is the complete sparse
    // workbench, so undo/redo and edge clipping use the persisted result.
    applyPersistentWorkbench(data);
  });
  await inflight;
  // New paint events may have arrived while the request was in flight.
  if (pendingCenters.size) return flushPendingPaint();
}
