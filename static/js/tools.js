import { state } from "./state.js";
import { pixelToAxial } from "./hex_math.js";
import { paintHexApi, paintHexesBatchApi, paintHexesBatchRadiusApi } from "./api.js";
import { drawHexTile } from "./renderer.js";

export function mouseToHex(canvas, event) {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    return pixelToAxial(
        event.offsetX - centerX,
        event.offsetY - centerY,
        state.map.hex_size
    );
}

export async function paintHex(canvas, hex) {
    if (!state.selectedTerrainKey) return;
    if (!state.map.hexes) return;

    const data = await paintHexApi(
        hex.q,
        hex.r,
        state.selectedTerrainKey
    );

    applyModifiedHexes(canvas, data.modified_hexes);
}

export async function paintHexesBatch(canvas, hexes) {
    if (!state.selectedTerrainKey) return;
    if (!state.map.hexes) return;
    if (hexes.length === 0) return;

    const data = await paintHexesBatchApi(
        hexes,
        state.selectedTerrainKey
    );

    applyModifiedHexes(canvas, data.modified_hexes);
}

export async function paintHexesBatchRadius(canvas, hexes) {
    if (!state.selectedTerrainKey) return;
    if (!state.map.hexes) return;
    if (hexes.length === 0) return;

    const data = await paintHexesBatchRadiusApi(
        hexes,
        state.selectedTerrainKey,
        state.brushRadius
    );

    applyModifiedHexes(canvas, data.modified_hexes);
}

function applyModifiedHexes(canvas, modifiedHexes) {
    for (const modifiedHex of modifiedHexes) {
        state.map.hexes[`${modifiedHex.q},${modifiedHex.r}`] = modifiedHex;

        drawHexTile(
            canvas,
            state.map,
            modifiedHex
        );
    }
}