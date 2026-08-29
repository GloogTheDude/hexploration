import { state } from "./state.js?v=303";
import { pixelToAxial } from "./hex_math.js?v=303";
import { paintHexesBatchRadiusApi } from "./api.js?v=303";
import { drawPaintPreview, drawBrushSegmentPreview, mapScreenCenter } from "./renderer.js?v=303";

const pendingCenters = new Map();
let syncTimer = null;
let inflight = Promise.resolve();
const SYNC_AFTER_STROKE_MS = 180;
const MAX_PENDING_CENTERS = 2500;

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

function applyLocalTerrain(q, r, terrain) {
  const key = `${q},${r}`;
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
    // Server remains authoritative. Applying the compact response also handles
    // edge-of-map radius clipping exactly like the backend.
    for (const modified of data.modified_hexes || []) {
      state.map.hexes[`${modified.q},${modified.r}`] = modified;
    }
  });
  await inflight;
  // New paint events may have arrived while the request was in flight.
  if (pendingCenters.size) return flushPendingPaint();
}
