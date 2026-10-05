const SQRT3 = Math.sqrt(3);

/**
 * Return the rectangular even-q columns/rows that can intersect a canvas.
 * The bounds intentionally include a geometry-derived safety margin for hex
 * radius and column parity, then clamp to the logical map dimensions.
 */
export function computeVisibleHexBounds({
  canvasWidth,
  canvasHeight,
  centerX,
  centerY,
  scale,
  size,
  mapWidth,
  mapHeight,
}) {
  const width = Number(mapWidth) || 0;
  const height = Number(mapHeight) || 0;
  const hexSize = Number(size) || 0;
  const safeScale = Math.max(Math.abs(Number(scale) || 0), Number.EPSILON);
  if (width < 1 || height < 1 || hexSize <= 0) {
    return { colMin: 1, colMax: 0, rowBounds: () => ({ rowMin: 1, rowMax: 0 }) };
  }

  const screenHexSize = hexSize * safeScale;
  const margin = Math.max(screenHexSize * 2, 8);
  const worldLeft = (-centerX - margin) / safeScale;
  const worldRight = (canvasWidth - centerX + margin) / safeScale;
  const worldTop = (-centerY - margin) / safeScale;
  const worldBottom = (canvasHeight - centerY + margin) / safeScale;
  const columnWidth = 1.5 * hexSize;
  const rowHeight = SQRT3 * hexSize;
  const columnPadding = Math.ceil((screenHexSize + margin) / (1.5 * screenHexSize));
  const rowPadding = Math.ceil((screenHexSize + margin) / (SQRT3 * screenHexSize));

  const colMin = Math.max(0, Math.floor(worldLeft / columnWidth + width / 2) - columnPadding);
  const colMax = Math.min(width - 1, Math.ceil(worldRight / columnWidth + width / 2) + columnPadding);

  return {
    colMin,
    colMax,
    rowBounds(col) {
      const q = col - Math.floor(width / 2);
      const parity = q & 1;
      return {
        rowMin: Math.max(0, Math.floor(worldTop / rowHeight + height / 2 + parity / 2) - rowPadding),
        rowMax: Math.min(height - 1, Math.ceil(worldBottom / rowHeight + height / 2 + parity / 2) + rowPadding),
      };
    },
  };
}
