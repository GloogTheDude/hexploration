import { state } from "./state.js";

export function createTerrainButtons() {
    const container = document.getElementById("terrain-buttons");
    if (!container) return;

    container.innerHTML = "";

    for (const [key, terrain] of Object.entries(state.terrains)) {
        const button = document.createElement("button");
        button.classList.add("terrain-btn");
        button.dataset.terrain = key;

        button.innerHTML = `
            <span class="color-sample" style="background:${terrain.color}"></span>
            ${terrain.type}
        `;

        button.addEventListener("click", () => {
            state.selectedTerrainKey = key;
        });

        container.appendChild(button);
    }
}
