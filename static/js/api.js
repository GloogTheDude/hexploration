import { state } from "./state.js?v=320";
import { authFetch } from "./auth.js";

async function jsonRequest(url, options = {}) {
  const response = await authFetch(url, options);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `${response.status} ${response.statusText}`);
  }
  return body;
}

export async function fetchPersistentMap(campaignId, versionId) {
  return jsonRequest(`/api/campaigns/${campaignId}/dm-map-workbench?map_version_id=${versionId}`);
}

export async function fetchTerrains() {
  return jsonRequest("/api/terrains");
}

export async function createMap(campaignId, width, height, hexSize, name, versionName, effectiveFromGameMinute) {
  return jsonRequest(`/api/campaigns/${campaignId}/dm-maps`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      description: null,
      version_name: versionName,
      effective_from_game_minute: effectiveFromGameMinute,
      width,
      height,
      hex_size: hexSize,
    }),
  });
}

function editorPath(suffix) {
  const { campaignId, mapId, versionId } = state.editor;
  if (!campaignId || !mapId || !versionId) throw new Error("Aucune version de carte persistée n'est chargée.");
  return `/api/campaigns/${campaignId}/dm-maps/${mapId}/dm-map-versions/${versionId}/hexes/${suffix}`;
}

export async function paintHexesBatchRadiusApi(hexes, terrainKey, radius) {
  return jsonRequest(editorPath("paint"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ centers: hexes, terrain_key: terrainKey, radius }),
  });
}

export async function paintHexesExactApi(hexes) {
  return jsonRequest(editorPath("exact"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(hexes),
  });
}
