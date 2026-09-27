// The backend returns ISO timestamps already in Israel local time
// (e.g. "2026-09-28T19:00:00+03:00"). We format the wall-clock parts directly
// rather than going through Date/Intl, so the device's timezone never matters.

const WEEKDAYS_HE = ['יום א׳', 'יום ב׳', 'יום ג׳', 'יום ד׳', 'יום ה׳', 'יום ו׳', 'שבת'];

type WallClock = { year: number; month: number; day: number; hhmm: string };

function parseWallClock(iso: string): WallClock {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/.exec(iso);
  if (!match) throw new Error(`Unexpected timestamp: ${iso}`);
  return { year: +match[1], month: +match[2], day: +match[3], hhmm: match[4] };
}

function dayNumber({ year, month, day }: WallClock): number {
  return Date.UTC(year, month - 1, day) / 86_400_000;
}

/** "19:00", "מחר 07:00", or "יום ב׳ 5.10 08:00", relative to `reference`. */
export function formatLocalTime(iso: string, reference: string): string {
  const target = parseWallClock(iso);
  const diff = dayNumber(target) - dayNumber(parseWallClock(reference));
  if (diff === 0) return target.hhmm;
  if (diff === 1) return `מחר ${target.hhmm}`;
  const weekday = WEEKDAYS_HE[new Date(dayNumber(target) * 86_400_000).getUTCDay()];
  return `${weekday} ${target.day}.${target.month} ${target.hhmm}`;
}

function formatDays(days: number): string {
  return days === 1 ? 'יום' : days === 2 ? 'יומיים' : `${days} ימים`;
}

function formatHours(hours: number): string {
  return hours === 1 ? 'שעה' : hours === 2 ? 'שעתיים' : `${hours} שעות`;
}

/** Hebrew "and": hyphenated before a digit ("ו-30 דקות"), attached before a word ("ודקה"). */
function and(first: string, second: string): string {
  return `${first} ${/^\d/.test(second) ? 'ו-' : 'ו'}${second}`;
}

/** Minutes precision below a day; days and hours from a day up. */
export function formatDuration(totalMinutes: number): string {
  if (totalMinutes >= 24 * 60) {
    const days = Math.floor(totalMinutes / (24 * 60));
    const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
    return hours === 0 ? formatDays(days) : and(formatDays(days), formatHours(hours));
  }
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const hoursText = formatHours(hours);
  const minutesText = minutes === 1 ? 'דקה' : `${minutes} דקות`;
  if (hours === 0) return minutesText;
  if (minutes === 0) return hoursText;
  return and(hoursText, minutesText);
}
