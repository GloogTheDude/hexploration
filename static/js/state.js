export const state = {
  map: {},
  terrains: {},
  selectedTerrainKey: null,
  isBrushOn: false,
  isPainting: false,
  isPanning: false,
  spacePanning: false,
  panMoved: false,
  lastPaintedHex: null,
  brushRadius: 1,
  view: { scale: 1, panX: 0, panY: 0 },
};
