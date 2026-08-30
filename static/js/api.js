export async function fetchMap() {
    const response = await fetch("/api/map");
    return await response.json();
}

export async function fetchTerrains() {
    const response = await fetch("/api/terrains");
    return await response.json();
}

export async function createMap(width, height, hexSize) {
    const response = await fetch(`/api/newmap/${width}/${height}/${hexSize}`, {
        method: "POST"
    });
    return await response.json();
}

export async function paintHexApi(q, r, terrainKey) {
    const response = await fetch(`/api/hex/${q}/${r}/${terrainKey}`, {
        method: "POST"
    });
    return await response.json();
}

export async function paintHexesBatchApi(hexes, terrainKey) {
    const payload = hexes.map(hex => ({
        q: hex.q,
        r: hex.r,
        terrain_key: terrainKey
    }));

    const response = await fetch("/api/hex/paint", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
    return await response.json();
}

export async function paintHexesBatchRadiusApi(hexes, terrainKey, radius) {
    const payload = hexes.map(hex => ({
        q: hex.q,
        r: hex.r,
        terrain_key: terrainKey
    }));

    const response = await fetch(`/api/hex/paintRadius?radius=${radius}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });
    return await response.json();
}

export async function paintHexesExactApi(hexes) {
    const response = await fetch("/api/hex/paintExact", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(hexes)
    });
    if (!response.ok) throw new Error(`Exact paint failed: ${response.status}`);
    return await response.json();
}
