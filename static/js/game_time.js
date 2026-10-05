export const GAME_MONTHS_PER_YEAR = 12;
export const GAME_DAYS_PER_MONTH = 30;
export const GAME_MINUTES_PER_DAY = 1440;
export const GAME_MINUTES_PER_MONTH = GAME_DAYS_PER_MONTH * GAME_MINUTES_PER_DAY;
export const GAME_MINUTES_PER_YEAR = GAME_MONTHS_PER_YEAR * GAME_MINUTES_PER_MONTH;

export function datePartsFromGameMinute(total) {
  total = Math.max(0, Math.floor(Number(total) || 0));
  const year = Math.floor(total / GAME_MINUTES_PER_YEAR);
  total %= GAME_MINUTES_PER_YEAR;
  const month = Math.floor(total / GAME_MINUTES_PER_MONTH) + 1;
  total %= GAME_MINUTES_PER_MONTH;
  const day = Math.floor(total / GAME_MINUTES_PER_DAY) + 1;
  total %= GAME_MINUTES_PER_DAY;
  const hour = Math.floor(total / 60);
  const minute = total % 60;
  return { year, month, day, hour, minute };
}

export function gameMinuteFromDateParts({ year, month, day, hour, minute }) {
  for (const [name, value] of Object.entries({ year, month, day, hour, minute })) {
    if (!Number.isInteger(value)) throw new Error(`${name} invalide`);
  }
  if (year < 0) throw new Error('Année invalide');
  if (month < 1 || month > GAME_MONTHS_PER_YEAR) throw new Error('Mois invalide (1–12)');
  if (day < 1 || day > GAME_DAYS_PER_MONTH) throw new Error('Jour invalide (1–30)');
  if (hour < 0 || hour > 23) throw new Error('Heure invalide (0–23)');
  if (minute < 0 || minute > 59) throw new Error('Minute invalide (0–59)');
  return year * GAME_MINUTES_PER_YEAR
    + (month - 1) * GAME_MINUTES_PER_MONTH
    + (day - 1) * GAME_MINUTES_PER_DAY
    + hour * 60
    + minute;
}

export function formatGameDate(total) {
  const p = datePartsFromGameMinute(total);
  return `A${p.year} · M${p.month} · J${p.day} · ${String(p.hour).padStart(2, '0')}:${String(p.minute).padStart(2, '0')}`;
}

export function setDateInputs(prefix, total, root = document) {
  const p = datePartsFromGameMinute(total);
  for (const key of ['year', 'month', 'day', 'hour', 'minute']) {
    const el = root.getElementById?.(`${prefix}-${key}`) || root.querySelector?.(`#${prefix}-${key}`);
    if (el) el.value = String(p[key]);
  }
}

export function gameMinuteFromDateInputs(prefix, root = document) {
  const read = key => {
    const el = root.getElementById?.(`${prefix}-${key}`) || root.querySelector?.(`#${prefix}-${key}`);
    return Number(el?.value);
  };
  return gameMinuteFromDateParts({
    year: read('year'), month: read('month'), day: read('day'), hour: read('hour'), minute: read('minute'),
  });
}

export function optionalGameMinuteFromDateInputs(prefix, root = document) {
  const ids = ['year', 'month', 'day', 'hour', 'minute'].map(key => `${prefix}-${key}`);
  const els = ids.map(id => root.getElementById?.(id) || root.querySelector?.(`#${id}`));
  if (els.every(el => !el || String(el.value).trim() === '')) return null;
  return gameMinuteFromDateInputs(prefix, root);
}

export function clearDateInputs(prefix, root = document) {
  for (const key of ['year', 'month', 'day', 'hour', 'minute']) {
    const el = root.getElementById?.(`${prefix}-${key}`) || root.querySelector?.(`#${prefix}-${key}`);
    if (el) el.value = '';
  }
}

export function formatDurationMinutes(total) {
  total = Math.max(0, Math.floor(Number(total) || 0));
  const days = Math.floor(total / GAME_MINUTES_PER_DAY);
  total %= GAME_MINUTES_PER_DAY;
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  const parts = [];
  if (days) parts.push(`${days}j`);
  if (hours) parts.push(`${hours}h`);
  if (minutes || !parts.length) parts.push(`${minutes}min`);
  return parts.join(' ');
}
