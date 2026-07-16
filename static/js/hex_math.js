export function axialToPixel(q, r, size) {
    return {
        x: size * Math.sqrt(3) * (q + r / 2),
        y: size * 1.5 * r
    };
}

export function pixelToAxial(x, y, size) {
    const q = ((Math.sqrt(3) / 3) * x - y / 3) / size;
    const r = ((2 / 3) * y) / size;

    return axialRound(q, r);
}

export function axialRound(q, r) {
    let x = q;
    let z = r;
    let y = -x - z;

    let rx = Math.round(x);
    let ry = Math.round(y);
    let rz = Math.round(z);

    const xDiff = Math.abs(rx - x);
    const yDiff = Math.abs(ry - y);
    const zDiff = Math.abs(rz - z);

    if (xDiff > yDiff && xDiff > zDiff) {
        rx = -ry - rz;
    } else if (yDiff > zDiff) {
        ry = -rx - rz;
    } else {
        rz = -rx - ry;
    }

    return { q: rx, r: rz };
}

export function hexDistance(a, b) {
    return (
        Math.abs(a.q - b.q)
        + Math.abs(a.q + a.r - b.q - b.r)
        + Math.abs(a.r - b.r)
    ) / 2;
}

export function getHexLine(a, b) {
    const distance = hexDistance(a, b);
    const results = [];

    for (let i = 0; i <= distance; i++) {
        const t = distance === 0 ? 0 : i / distance;

        const q = a.q + (b.q - a.q) * t;
        const r = a.r + (b.r - a.r) * t;

        results.push(axialRound(q, r));
    }

    return results;
}