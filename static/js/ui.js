import { state } from "./state.js?v=320";

export function createTerrainButtons() {
  const container = document.getElementById("terrain-buttons");
  const label = document.getElementById("selected-terrain-label");
  if (!container) return;
  container.innerHTML = "";
  for (const [key, terrain] of Object.entries(state.terrains)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "terrain-btn";
    button.dataset.terrain = key;
    button.innerHTML = `<span class="color-sample" style="background:${terrain.color}"></span><span>${terrain.type}</span><span class="terrain-meta">E${terrain.elevation} · V${terrain.visibility_score}</span>`;
    button.addEventListener("click", () => {
      state.selectedTerrainKey = key;
      container.querySelectorAll(".terrain-btn").forEach(el => el.classList.toggle("selected", el === button));
      if (label) label.textContent = terrain.type;
    });
    container.appendChild(button);
  }
}
