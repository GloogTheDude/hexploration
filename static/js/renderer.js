import { axialToPixel } from "./hex_math.js";

export function drawMap(canvas, map) {
    const ctx = canvas.getContext("2d");

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!map.hexes) return;

    for (const hex of Object.values(map.hexes)) {
        drawHexTile(canvas, map, hex);
    }
}

export function drawHexTile(canvas, map, hex) {
    const ctx = canvas.getContext("2d");

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const hexSize = map.hex_size;

    const { x, y } = axialToPixel(hex.q, hex.r, hexSize);

    drawHex(
        ctx,
        centerX + x,
        centerY + y,
        hexSize,
        hex.terrain.color
    );
}

function drawHex(ctx, x, y, size, color) {
    ctx.beginPath();

    for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 180 * (60 * i - 30);

        const pointX = x + size * Math.cos(angle);
        const pointY = y + size * Math.sin(angle);

        if (i === 0) {
            ctx.moveTo(pointX, pointY);
        } else {
            ctx.lineTo(pointX, pointY);
        }
    }

    ctx.closePath();

    ctx.fillStyle = color;
    ctx.fill();

    ctx.strokeStyle = "#333";
    ctx.stroke();
}