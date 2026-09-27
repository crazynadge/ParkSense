import type { UserProfile } from '@/api/types';

// Until the profile screen exists: a visitor with a private car and no permits.
// City and zone are no longer assumed: they come from the device's GPS.
export const DEMO_PROFILE: UserProfile = {
  vehicle_type: 'private',
  resident_permits: [],
  has_disabled_permit: false,
};
