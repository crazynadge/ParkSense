import type { UserProfile } from '@/api/types';

// Until the profile screen and GPS exist: a visitor with a private car in Tel Aviv.
export const DEMO_PROFILE: UserProfile = {
  vehicle_type: 'private',
  resident_permits: [],
  has_disabled_permit: false,
};

// Canonical city IDs match what the backend compares against; labels are for display.
export const DEMO_CITY = 'Tel Aviv';
