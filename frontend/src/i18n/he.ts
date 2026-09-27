import type { ApiErrorKind } from '@/api/client';
import type { CostInfo, LocationContext, ParkingStatus, Reason } from '@/api/types';

export const API_ERROR_TEXT: Record<ApiErrorKind, string> = {
  network: 'אין חיבור לשרת. הניתוח מתבצע בענן – בדקו את החיבור לאינטרנט ונסו שוב.',
  timeout: 'השרת לא הגיב בזמן. נסו שוב.',
  server: 'אירעה שגיאה בעיבוד הסריקה. נסו שוב.',
  unavailable: 'זיהוי השלטים אינו זמין כרגע. נסו שוב בעוד רגע.',
};

export const STATUS_HEADLINE: Record<ParkingStatus, string> = {
  green: 'מותר לחנות',
  orange: 'מותר לחנות בתנאים',
  red: 'אסור לחנות כאן',
  unknown: 'לא ניתן לקבוע',
};

const CITY_LABELS: Record<string, string> = {
  'Tel Aviv': 'תל אביב-יפו',
  Givatayim: 'גבעתיים',
};

const FIELD_LABELS: Record<string, string> = {
  hours: 'שעות',
  days: 'ימים',
  price: 'תעריף',
  zone: 'אזור',
  duration: 'משך חניה',
};

export function cityLabel(city: string): string {
  return CITY_LABELS[city] ?? city;
}

/** "תל אביב-יפו, אזור 2", or a note when the location is unknown or imprecise. */
export function locationText(location: LocationContext | null): string {
  if (!location) return 'מיקום לא זמין';
  if (!location.city) return location.city_certain ? 'מחוץ לאזורי הכיסוי' : 'מיקום לא מדויק';
  const place = location.city_name_he ?? cityLabel(location.city);
  const zone = location.zone ? `, אזור ${location.zone}` : '';
  const precise = location.city_certain && (location.zone == null || location.zone_certain);
  return precise ? `${place}${zone}` : `${place}${zone} (לא ודאי)`;
}

function permittedBy(reason: Reason): string {
  switch (reason.permitted_by) {
    case 'disabled_permit':
      return 'פטור בזכות תו נכה';
    case 'resident_permit':
      return `פטור בזכות תו תושב ${cityLabel(reason.params.city ?? '')} אזור ${reason.params.zone ?? ''}`;
    case 'commercial_vehicle':
      return 'מותר לרכב מסחרי';
    default:
      return '';
  }
}

function withPermit(base: string, reason: Reason): string {
  return reason.permitted_by ? `${base} – ${permittedBy(reason)}` : base;
}

export function reasonText(reason: Reason): string {
  switch (reason.code) {
    case 'no_restriction':
      return 'אין הגבלת חניה בשעה זו';
    case 'red_white_curb':
      return 'אבן שפה אדומה-לבנה: אסור לעצור בכל זמן';
    case 'no_stopping':
      return 'אסור לעצור';
    case 'no_parking':
      return 'אסור לחנות';
    case 'disabled_only':
      return reason.permitted_by ? 'חניית נכים – מותר לך עם תו נכה' : 'חניה לבעלי תו נכה בלבד';
    case 'loading_zone':
      return reason.permitted_by ? 'אזור פריקה וטעינה – מותר לרכב מסחרי' : 'אזור פריקה וטעינה לרכב מסחרי בלבד';
    case 'residents_only':
      return withPermit('חניה לבעלי תו אזור בלבד', reason);
    case 'paid':
      return withPermit('חניה בתשלום', reason);
    case 'time_limited':
      return withPermit('חניה מוגבלת בזמן', reason);
    case 'sign_illegible':
      return 'השלט אינו קריא. צלמו שוב מקרוב ובתאורה טובה.';
    case 'low_confidence':
      return 'לא הצלחנו לקרוא את השלט בוודאות. צלמו שוב.';
    case 'partial_sign': {
      const fields = (reason.params.fields ?? '').split(',').filter(Boolean);
      return `חלקים מהשלט לא נקראו: ${fields.map((f) => FIELD_LABELS[f] ?? f).join(', ')}`;
    }
    case 'nothing_detected':
      return 'לא זוהו שלט או סימון אבן שפה.';
    case 'paid_hours_unknown':
      return 'אבן שפה כחולה-לבנה, אך שעות החניה בתשלום לא זוהו בשלט.';
    case 'unsupported_condition':
      return `השלט כולל תנאי שהאפליקציה עדיין לא יודעת לפרש: ${reason.params.conditions ?? ''}. בדקו את השלט בעצמכם.`;
    case 'paid_rate_unknown':
      return 'התעריף לשעה לא זוהה בשלט.';
    case 'max_duration_unknown':
      return 'משך החניה המרבי לא זוהה בשלט.';
    case 'location_uncertain':
      return `לא ניתן לאמת את מיקומכם, ולכן לא ניתן לקבוע אם תו אזור ${reason.params.zone ?? ''} תקף כאן. הפעילו שירותי מיקום ונסו שוב.`;
    case 'zone_mismatch':
      return `בשלט זוהה אזור ${reason.params.sign_zone ?? ''}, אך לפי המיקום אתם באזור ${reason.params.gps_zone ?? ''}. ייתכן שהשלט נקרא לא נכון – בדקו אותו בעצמכם.`;
    case 'local_zone_unknown':
      return 'השלט מתייחס לתושבי האזור, אך לא ניתן לקבוע באיזה אזור אתם נמצאים. נסו שוב כשהמיקום מדויק יותר.';
  }
}

export function costText(cost: CostInfo): string {
  switch (cost.type) {
    case 'free':
      return 'חינם';
    case 'exempt':
      return 'פטור מתשלום';
    case 'paid':
      return cost.price_per_hour == null ? 'בתשלום (תעריף לא ידוע)' : `בתשלום · ₪${cost.price_per_hour.toFixed(2)} לשעה`;
    case 'unknown':
      return 'לא ידוע';
  }
}

// Starts with a Hebrew word on purpose: a paragraph that opens with Latin text
// ("ParkSense") gets an LTR base direction and scrambles the Hebrew clause order.
export const DISCLAIMER =
  'אפליקציית ParkSense היא כלי עזר מבוסס בינה מלאכותית בלבד. האחריות הבלעדית לבדיקת השילוט בפועל ולציות לחוקי התעבורה חלה על הנהג.';
