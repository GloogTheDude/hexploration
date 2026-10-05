import json
import shutil
import subprocess

import pytest


NODE = shutil.which("node")


def visible_bounds(*, canvas_width, canvas_height, center_x, center_y, scale, size, width, height):
    if NODE is None:
        pytest.skip("Node.js is required for the frontend viewport helper test")
    script = f"""
import {{ computeVisibleHexBounds }} from './static/js/viewport.js';
const bounds = computeVisibleHexBounds({{
  canvasWidth: {canvas_width}, canvasHeight: {canvas_height},
  centerX: {center_x}, centerY: {center_y}, scale: {scale}, size: {size},
  mapWidth: {width}, mapHeight: {height}
}});
let count = 0;
for (let col = bounds.colMin; col <= bounds.colMax; col++) {{
  const rows = bounds.rowBounds(col);
  count += Math.max(0, rows.rowMax - rows.rowMin + 1);
}}
console.log(JSON.stringify({{ colMin: bounds.colMin, colMax: bounds.colMax, count }}));
"""
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_close_viewport_does_not_scan_a_400_by_400_map():
    result = visible_bounds(
        canvas_width=1200,
        canvas_height=780,
        center_x=600,
        center_y=390,
        scale=1,
        size=32,
        width=400,
        height=400,
    )
    assert 0 < result["count"] < 160_000
    assert result["colMin"] >= 0
    assert result["colMax"] < 400


def test_full_viewport_can_still_cover_the_whole_map_without_overflow():
    result = visible_bounds(
        canvas_width=30_000,
        canvas_height=30_000,
        center_x=15_000,
        center_y=15_000,
        scale=1,
        size=32,
        width=400,
        height=400,
    )
    assert result["count"] == 160_000


def test_viewport_outside_map_is_empty_and_clamped():
    result = visible_bounds(
        canvas_width=800,
        canvas_height=600,
        center_x=100_000,
        center_y=100_000,
        scale=1,
        size=32,
        width=400,
        height=400,
    )
    assert result["count"] == 0
    assert result["colMin"] >= 0
    assert result["colMax"] <= 399
