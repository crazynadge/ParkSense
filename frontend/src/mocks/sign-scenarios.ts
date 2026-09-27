import type { ParkingSignData } from '@/api/types';

// Development-only stand-ins for the Vision AI output, until the camera and
// extraction pipeline exist. Each one exercises a different engine path.

export type SignScenario = {
  id: string;
  label: string;
  signData: ParkingSignData;
};

const SUN_THU = ['sun', 'mon', 'tue', 'wed', 'thu'] as const;

export const SIGN_SCENARIOS: SignScenario[] = [
  {
    id: 'tel-aviv-blue-white',
    label: 'כחול-לבן בתל אביב, פטור לאזור 2',
    signData: {
      sign_detected: true,
      is_legible: true,
      confidence: 0.95,
      curb_marking: 'blue_white',
      rules: [
        {
          rule_type: 'paid',
          windows: [
            { days: [...SUN_THU], start: '08:00', end: '19:00' },
            { days: ['fri'], start: '08:00', end: '13:00' },
          ],
          price_per_hour: 6.3,
          exempt_resident_zones: [{ zone: '2' }],
        },
        {
          rule_type: 'residents_only',
          windows: [{ days: [...SUN_THU], start: '19:00', end: '07:00' }],
          exempt_resident_zones: [{ zone: '2' }],
        },
      ],
    },
  },
  {
    id: 'time-limited',
    label: 'חניה מוגבלת לשעתיים (08:00–18:00)',
    signData: {
      sign_detected: true,
      is_legible: true,
      confidence: 0.92,
      curb_marking: 'gray',
      rules: [
        {
          rule_type: 'time_limited',
          windows: [{ start: '08:00', end: '18:00' }],
          max_duration_minutes: 120,
        },
      ],
    },
  },
  {
    id: 'red-white',
    label: 'אבן שפה אדומה-לבנה',
    signData: {
      sign_detected: false,
      confidence: 0.9,
      curb_marking: 'red_white',
    },
  },
  {
    id: 'illegible',
    label: 'שלט לא קריא',
    signData: {
      sign_detected: true,
      is_legible: false,
      confidence: 0.3,
      curb_marking: 'blue_white',
    },
  },
];
