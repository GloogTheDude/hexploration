import { formatGameDate, datePartsFromGameMinute, gameMinuteFromDateInputs, optionalGameMinuteFromDateInputs, clearDateInputs, setDateInputs } from './game_time.js';
const embedded = new URLSearchParams(window.location.search).get("embedded") === "1";
if (embedded) document.body.classList.add("embedded");

const $ = (id) => document.getElementById(id);

const campaignIdInput = $("campaign-id");
const timelineEl = $("timeline");
const summaryEl = $("timeline-summary");
const dialog = $("event-dialog");
const form = $("event-form");
const formError = $("form-error");
const toast = $("toast");

let events = [];

function campaignId() {
    const value = Number(campaignIdInput.value);
    if (!Number.isInteger(value) || value < 1) throw new Error("Campaign ID invalide");
    return value;
}

function gameMinuteFromParts() { return gameMinuteFromDateInputs("event"); }

function partsFromGameMinute(gameMinute) { return datePartsFromGameMinute(gameMinute); }

function formatGameMinute(gameMinute) { return formatGameDate(gameMinute); }

function refreshComputedMinute() {
    try { $("computed-game-date").textContent = formatGameDate(gameMinuteFromParts()); }
    catch { $("computed-game-date").textContent = "—"; }
}

async function api(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 204) return null;
    let data = null;
    try { data = await response.json(); } catch { /* empty/non-json */ }
    if (!response.ok) {
        const detail = data?.detail;
        throw new Error(typeof detail === "string" ? detail : `HTTP ${response.status}`);
    }
    return data;
}

function showToast(message) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    window.setTimeout(() => toast.classList.add("hidden"), 2200);
}

function buildFilterQuery() {
    const params = new URLSearchParams();
    const from = optionalGameMinuteFromDateInputs("filter-from");
    const to = optionalGameMinuteFromDateInputs("filter-to");
    if (from != null) params.set("from_game_minute", from);
    if (to != null) params.set("to_game_minute", to);
    for (const [elementId, queryKey] of [["filter-event-type","event_type"],["filter-target-type","target_type"],["filter-target-id","target_id"]]) {
        const value = $(elementId).value.trim();
        if (value !== "") params.set(queryKey, value);
    }
    return params.toString();
}

async function loadTimeline() {
    try {
        const id = campaignId();
        const query = buildFilterQuery();
        events = await api(`/api/campaigns/${id}/world-events${query ? `?${query}` : ""}`);
        renderTimeline();
    } catch (error) {
        timelineEl.innerHTML = `<p class="empty">${escapeHtml(error.message)}</p>`;
        summaryEl.textContent = "Impossible de charger la timeline.";
    }
}

function renderTimeline() {
    timelineEl.replaceChildren();
    summaryEl.textContent = `${events.length} événement${events.length === 1 ? "" : "s"} · ordre chronologique`;
    if (events.length === 0) {
        timelineEl.innerHTML = '<p class="empty">Aucun événement pour ces filtres.</p>';
        return;
    }

    let currentDate = null;
    for (const event of events) {
        const parts = partsFromGameMinute(event.game_minute);
        const dateKey = `${parts.year}-${parts.month}-${parts.day}`;
        if (dateKey !== currentDate) {
            currentDate = dateKey;
            const heading = document.createElement("div");
            heading.className = "timeline-day";
            heading.textContent = `A${parts.year} · M${parts.month} · J${parts.day}`;
            timelineEl.appendChild(heading);
        }

        const row = document.createElement("div");
        row.className = "timeline-event";
        const target = event.target_type && event.target_id != null
            ? `${event.target_type} #${event.target_id}`
            : event.expedition_id != null
                ? `Expédition #${event.expedition_id}`
                : "Global";
        row.innerHTML = `
            <div class="event-time">${String(parts.hour).padStart(2, "0")}:${String(parts.minute).padStart(2, "0")}</div>
            <div class="event-dot"></div>
            <article class="event-card" data-event-id="${event.id}">
                <div class="event-header">
                    <span class="event-type">${escapeHtml(event.event_type)}</span>
                    <span class="event-target">${escapeHtml(target)}</span>
                </div>
                ${event.dm_note ? `<p class="event-note">${escapeHtml(event.dm_note)}</p>` : ""}
                <p class="event-payload">${escapeHtml(JSON.stringify(event.payload))}</p>
            </article>`;
        row.querySelector(".event-card").addEventListener("click", () => openEditDialog(event));
        timelineEl.appendChild(row);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function resetForm() {
    form.reset();
    $("event-id").value = "";
    setDateInputs("event", 0);
    $("payload").value = "{}";
    $("delete-event-btn").classList.add("hidden");
    $("dialog-title").textContent = "Nouvel événement";
    formError.textContent = "";
    refreshComputedMinute();
}

function openCreateDialog() {
    resetForm();
    dialog.showModal();
}

function openEditDialog(event) {
    resetForm();
    const parts = partsFromGameMinute(event.game_minute);
    $("event-id").value = event.id;
    setDateInputs("event", event.game_minute);
    $("event-type").value = event.event_type;
    $("expedition-id").value = event.expedition_id ?? "";
    $("target-type").value = event.target_type ?? "";
    $("target-id").value = event.target_id ?? "";
    $("payload").value = JSON.stringify(event.payload, null, 2);
    $("dm-note").value = event.dm_note ?? "";
    $("dialog-title").textContent = `Modifier événement #${event.id}`;
    $("delete-event-btn").classList.remove("hidden");
    refreshComputedMinute();
    dialog.showModal();
}

function nullableNumber(id) {
    const value = $(id).value.trim();
    return value === "" ? null : Number(value);
}

function formPayload() {
    let payload;
    try {
        payload = JSON.parse($("payload").value || "{}");
    } catch {
        throw new Error("Payload JSON invalide");
    }
    if (payload === null || Array.isArray(payload) || typeof payload !== "object") {
        throw new Error("Payload doit être un objet JSON");
    }
    return {
        game_minute: gameMinuteFromParts(),
        event_type: $("event-type").value.trim(),
        expedition_id: nullableNumber("expedition-id"),
        target_type: $("target-type").value.trim() || null,
        target_id: nullableNumber("target-id"),
        payload,
        dm_note: $("dm-note").value.trim() || null,
    };
}

async function saveEvent(event) {
    event.preventDefault();
    formError.textContent = "";
    try {
        const body = formPayload();
        const eventId = $("event-id").value;
        if (eventId) {
            await api(`/api/world-events/${eventId}`, {
                method: "PATCH",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body),
            });
            showToast("Événement modifié");
        } else {
            await api(`/api/campaigns/${campaignId()}/world-events`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(body),
            });
            showToast("Événement créé");
        }
        dialog.close();
        await loadTimeline();
    } catch (error) {
        formError.textContent = error.message;
    }
}

async function deleteCurrentEvent() {
    const id = $("event-id").value;
    if (!id) return;
    if (!window.confirm(`Supprimer définitivement l'événement #${id} ?`)) return;
    try {
        await api(`/api/world-events/${id}`, {method: "DELETE"});
        dialog.close();
        showToast("Événement supprimé");
        await loadTimeline();
    } catch (error) {
        formError.textContent = error.message;
    }
}

async function inspectWorldState() {
    try {
        const minute = gameMinuteFromDateInputs("inspect-time");
        const state = await api(`/api/campaigns/${campaignId()}/world-state?game_minute=${minute}`);
        $("world-state").textContent = JSON.stringify(state, null, 2);
    } catch (error) {
        $("world-state").textContent = `Erreur: ${error.message}`;
    }
}

for (const id of ["event-year", "event-month", "event-day", "event-hour", "event-minute"]) {
    $(id).addEventListener("input", refreshComputedMinute);
}
$("load-btn").addEventListener("click", loadTimeline);
$("apply-filters-btn").addEventListener("click", loadTimeline);
$("clear-filters-btn").addEventListener("click", () => {
    clearDateInputs("filter-from"); clearDateInputs("filter-to"); for (const id of ["filter-event-type", "filter-target-type", "filter-target-id"]) $(id).value = "";
    loadTimeline();
});
$("new-event-btn").addEventListener("click", openCreateDialog);
$("close-dialog-btn").addEventListener("click", () => dialog.close());
$("cancel-event-btn").addEventListener("click", () => dialog.close());
$("delete-event-btn").addEventListener("click", deleteCurrentEvent);
$("inspect-btn").addEventListener("click", inspectWorldState);
form.addEventListener("submit", saveEvent);

const urlCampaign = new URLSearchParams(window.location.search).get("campaign_id");
if (urlCampaign) {
    campaignIdInput.value = urlCampaign;
    loadTimeline();
}
