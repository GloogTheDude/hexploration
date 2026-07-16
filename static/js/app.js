import { state } from "./state.js";
import { fetchMap, fetchTerrains, createMap, paintHexesBatchRadiusApi } from "./api.js";
import { drawMap } from "./renderer.js";
import { createTerrainButtons } from "./ui.js";
import { mouseToHex, paintHex, paintHexesBatchRadius } from "./tools.js";
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
paintMapBtn.addEventListener("click", () => paintHex(canvas, { q: 2, r: 3 }));

newMapBtn.addEventListener("click", () => {
    modal.classList.remove("hidden");
});

cancelNewMapBtn.addEventListener("click", () => {
    modal.classList.add("hidden");
});

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
    if (!state.isBrushOn)
        return;

    state.isPainting = true;

    const hex = mouseToHex(
        canvas,
        event
    );

    await paintHexesBatchRadius(
        canvas,
        [hex]
    );

    state.lastPaintedHex = hex;
}

async function onMouseMove(event) {
    if (!state.isBrushOn || !state.isPainting) return;

    const currentHex = mouseToHex(canvas, event);

    if (state.lastPaintedHex === null) {
        await paintHexesBatchRadiusApi(hexes, state.selectedTerrainKey, state.brushRadius);
        state.lastPaintedHex = currentHex;
        return;
    }

    const line = getHexLine(
        state.lastPaintedHex,
        currentHex
    );

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

function setRadius(){
    state.brushRadius = parseInt(radiusSlider.value);
    radiusSliderValue.textContent = state.brushRadius;
    console.log(state.brushRadius);
}