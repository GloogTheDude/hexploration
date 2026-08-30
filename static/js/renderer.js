import { axialToPixel } from "./hex_math.js?v=320";
import { state } from "./state.js?v=320";

const SQRT3 = Math.sqrt(3);
const HEX_POINTS = [
  [1, 0], [.5, SQRT3 / 2], [-.5, SQRT3 / 2],
  [-1, 0], [-.5, -SQRT3 / 2], [.5, -SQRT3 / 2],
];
let drawQueued = false;
let queuedCanvas = null;
let queuedMap = null;

export function resizeCanvasToDisplaySize(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.round(rect.width * dpr));
  const height = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
    return true;
  }
  return false;
}

export function mapScreenCenter(canvas) {
  return { x: canvas.width / 2 + state.view.panX, y: canvas.height / 2 + state.view.panY };
}

export function requestMapDraw(canvas, map) {
  queuedCanvas = canvas;
  queuedMap = map;
  if (drawQueued) return;
  drawQueued = true;
  requestAnimationFrame(() => {
    drawQueued = false;
    if (queuedCanvas) drawMap(queuedCanvas, queuedMap);
  });
}


export function drawPaintPreview(canvas, tiles) {
  if (!canvas || !tiles?.length || !state.map) return;
  resizeCanvasToDisplaySize(canvas);
  const ctx = canvas.getContext("2d");
  const size = Number(state.map.hex_size || 32);
  const screenSize = size * state.view.scale;
  const center = mapScreenCenter(canvas);
  const overview = state.map.sparse && screenSize < 1.2;
  const defaultTerrain = state.terrains?.[state.map.default_terrain_key || "SEA"];

  for (const tile of tiles) {
    const p = axialToPixel(tile.q, tile.r, size);
    const x = center.x + p.x * state.view.scale;
    const y = center.y + p.y * state.view.scale;
    if (!onScreen(canvas, x, y, Math.max(2, screenSize))) continue;
    const terrain = tile.terrain || defaultTerrain;
    if (!terrain) continue;
    if (overview) {
      ctx.fillStyle = terrain.color;
      const dot = Math.max(1.5, screenSize * 2);
      ctx.fillRect(x - dot / 2, y - dot / 2, dot, dot);
    } else {
      drawHex(ctx, x, y, screenSize, terrain.color, screenSize >= 2.2);
    }
  }
}


export function drawBrushSegmentPreview(canvas, startHex, endHex, terrain, radius = 1) {
  if (!canvas || !startHex || !endHex || !terrain || !state.map) return;
  const ctx = canvas.getContext("2d");
  const size = Number(state.map.hex_size || 32);
  const scale = state.view.scale;
  const center = mapScreenCenter(canvas);
  const a = axialToPixel(startHex.q, startHex.r, size);
  const b = axialToPixel(endHex.q, endHex.r, size);
  const ax = center.x + a.x * scale;
  const ay = center.y + a.y * scale;
  const bx = center.x + b.x * scale;
  const by = center.y + b.y * scale;
  const screenSize = size * scale;
  // Radius 1 is one hex. Larger brushes approximate the hex footprint with a
  // round screen-space stroke while zoomed out; exact cells are still updated.
  const diameterInHexes = Math.max(1, radius * 2 - 1);
  ctx.save();
  ctx.strokeStyle = terrain.color;
  ctx.fillStyle = terrain.color;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = Math.max(1.5, screenSize * diameterInHexes * 1.35);
  ctx.beginPath();
  ctx.moveTo(ax, ay);
  ctx.lineTo(bx, by);
  ctx.stroke();
  // pointerdown / zero-length segments still need a visible stamp
  if (Math.abs(ax - bx) + Math.abs(ay - by) < 0.01) {
    ctx.beginPath();
    ctx.arc(ax, ay, ctx.lineWidth / 2, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

export function drawMap(canvas, map) {
  resizeCanvasToDisplaySize(canvas);
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#081016";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!map?.hexes) return;

  const size = Number(map.hex_size || 32);
  const screenSize = size * state.view.scale;
  const center = mapScreenCenter(canvas);

  // New rectangular maps can be traversed directly by logical rows/columns.
  // This avoids scanning every tile when zoomed into a very large map.
  if (map.layout === "even-q-rect" && map.width && map.height) {
    drawRectangularVisible(ctx, canvas, map, center, size, screenSize);
  } else {
    // Compatibility path for legacy axial-parallelogram versions.
    for (const hex of Object.values(map.hexes)) {
      const p = axialToPixel(hex.q, hex.r, size);
      const x = center.x + p.x * state.view.scale;
      const y = center.y + p.y * state.view.scale;
      if (!onScreen(canvas, x, y, screenSize)) continue;
      drawHex(ctx, x, y, screenSize, hex.terrain.color, screenSize >= 2.2);
    }
  }
  drawPoiOverlay(ctx, canvas, map, center, size, screenSize);
}

function drawPoiOverlay(ctx, canvas, map, center, size, screenSize) {
  if (!state.showPoiOverlay || !state.editorPois?.length) return;
  const scale = state.view.scale;
  for (const poi of state.editorPois) {
    const p = axialToPixel(poi.q, poi.r, size);
    const x = center.x + p.x * scale;
    const y = center.y + p.y * scale;
    if (!onScreen(canvas, x, y, Math.max(8, screenSize))) continue;
    const radius = Math.max(4, Math.min(10, screenSize * .24));
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = poi.is_landmark ? "#ffd166" : "#ff8bc8";
    ctx.fill();
    ctx.strokeStyle = "#0b1218";
    ctx.lineWidth = Math.max(1.5, radius * .28);
    ctx.stroke();
    if (screenSize >= 18) {
      ctx.font = `${Math.max(10, Math.min(14, screenSize * .28))}px sans-serif`;
      ctx.fillStyle = "#f7fbff";
      ctx.shadowColor = "rgba(0,0,0,.9)";
      ctx.shadowBlur = 3;
      ctx.fillText(poi.name || "POI", x + radius + 4, y - radius - 2);
      ctx.shadowBlur = 0;
    }
  }
}

function drawRectangularVisible(ctx, canvas, map, center, size, screenSize) {
  const scale = state.view.scale;
  const margin = Math.max(screenSize * 2, 8);
  const defaultTerrain = state.terrains?.[map.default_terrain_key || "SEA"];

  // At continent/world overview zooms individual hexes are sub-pixel. Drawing
  // millions of polygons is wasted work: paint the default footprint once and
  // overlay only sparse terrain overrides. Detail returns automatically on zoom.
  if (map.sparse && screenSize < 1.2) {
    const q0 = -Math.floor(map.width / 2);
    const q1 = q0 + map.width - 1;
    const approxW = Math.max(1, (1.5 * size * (map.width - 1) + 2 * size) * scale);
    const approxH = Math.max(1, (SQRT3 * size * (map.height + .5)) * scale);
    ctx.fillStyle = defaultTerrain?.color || "#010554";
    ctx.fillRect(center.x - approxW / 2, center.y - approxH / 2, approxW, approxH);
    for (const hex of Object.values(map.hexes || {})) {
      const p = axialToPixel(hex.q, hex.r, size);
      const x = center.x + p.x * scale;
      const y = center.y + p.y * scale;
      if (!onScreen(canvas, x, y, Math.max(2, screenSize))) continue;
      ctx.fillStyle = hex.terrain.color;
      const dot = Math.max(1.5, screenSize * 2);
      ctx.fillRect(x - dot/2, y - dot/2, dot, dot);
    }
    return;
  }

  const worldMinX = (-center.x - margin) / scale;
  const worldMaxX = (canvas.width - center.x + margin) / scale;
  let colMin = Math.floor(worldMinX / (1.5 * size) + map.width / 2) - 2;
  let colMax = Math.ceil(worldMaxX / (1.5 * size) + map.width / 2) + 2;
  colMin = Math.max(0, colMin);
  colMax = Math.min(map.width - 1, colMax);
  const drawOutline = screenSize >= 2.2;

  for (let col = colMin; col <= colMax; col++) {
    const q = col - Math.floor(map.width / 2);
    const parity = q & 1;
    const worldMinY = (-center.y - margin) / scale;
    const worldMaxY = (canvas.height - center.y + margin) / scale;
    let rowMin = Math.floor(worldMinY / (SQRT3 * size) + map.height / 2 + parity / 2) - 2;
    let rowMax = Math.ceil(worldMaxY / (SQRT3 * size) + map.height / 2 + parity / 2) + 2;
    rowMin = Math.max(0, rowMin);
    rowMax = Math.min(map.height - 1, rowMax);
    for (let row = rowMin; row <= rowMax; row++) {
      const r = row - Math.floor(map.height / 2) - Math.floor((q + parity) / 2);
      const hex = map.hexes?.[`${q},${r}`];
      const terrain = hex?.terrain || defaultTerrain;
      if (!terrain) continue;
      const p = axialToPixel(q, r, size);
      const x = center.x + p.x * scale;
      const y = center.y + p.y * scale;
      drawHex(ctx, x, y, screenSize, terrain.color, drawOutline);
    }
  }
}

function onScreen(canvas, x, y, size) {
  return x >= -size && y >= -size && x <= canvas.width + size && y <= canvas.height + size;
}

function drawHex(ctx, x, y, size, color, outline = true) {
  ctx.beginPath();
  for (let i = 0; i < HEX_POINTS.length; i++) {
    const [dx, dy] = HEX_POINTS[i];
    const px = x + size * dx;
    const py = y + size * dy;
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  if (outline) {
    ctx.strokeStyle = "rgba(15, 24, 31, .78)";
    ctx.lineWidth = Math.max(1, state.view.scale * 1.2);
    ctx.stroke();
  }
}
