/**
 * Display helpers. The API always returns UTC timestamps; the browser's
 * Intl API converts them to the viewer's own timezone for display.
 */

const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
});

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

export const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

export function formatDateTime(iso) {
  if (!iso) return '—';
  return dateTimeFormat.format(new Date(iso));
}

export function relativeTime(iso) {
  if (!iso) return '';
  const diffMs = new Date(iso).getTime() - Date.now();
  const abs = Math.abs(diffMs);
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (abs < hour) return relative.format(Math.round(diffMs / minute), 'minute');
  if (abs < day) return relative.format(Math.round(diffMs / hour), 'hour');
  return relative.format(Math.round(diffMs / day), 'day');
}

/** How long after `fromIso` the time `toIso` is, e.g. "9 h 7 min" or "2 days". */
export function durationBetween(fromIso, toIso) {
  const minutes = Math.max(0, Math.round((new Date(toIso) - new Date(fromIso)) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h ${minutes % 60} min`;
  return `${Math.round(hours / 24)} days`;
}

export function hoursUntil(iso) {
  return (new Date(iso).getTime() - Date.now()) / (60 * 60 * 1000);
}

export function formatBytes(bytes) {
  if (bytes == null) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatMarks(marks) {
  if (marks == null) return '—';
  return Number.isInteger(marks) ? String(marks) : marks.toFixed(1).replace(/\.0$/, '');
}

/** ISO (UTC) -> value for <input type="datetime-local"> in the viewer's timezone. */
export function toLocalInputValue(iso) {
  const date = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** <input type="datetime-local"> value (viewer's timezone) -> ISO UTC string for the API. */
export function fromLocalInputValue(value) {
  return new Date(value).toISOString();
}

/** Stable accent colour per course code, so a course looks the same everywhere. */
export function courseTone(code = '') {
  let hash = 0;
  for (const char of code) hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  return `tone-${hash % 6}`;
}
