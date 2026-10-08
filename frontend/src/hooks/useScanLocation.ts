import { useCallback } from 'react';

import type { GpsFix } from '@/api/types';
import { useDeviceLocation, type LocationStatus } from '@/hooks/useDeviceLocation';
import { useParkedLocation } from '@/state/parked-location';

export type ScanLocation = {
  source: 'parked' | 'live';
  status: LocationStatus;
  accuracy: number | null;
  savedAt: number | null;
  getFix: (timeoutMs: number) => Promise<GpsFix | null>;
};

/**
 * The location a scan is judged by. A saved "חניתי כאן" spot always wins: the photo is
 * often taken down the street, possibly in a different zone, from where the car is.
 * Live GPS is only tracked when no car position is saved.
 */
export function useScanLocation(active: boolean): ScanLocation {
  const { parked } = useParkedLocation();
  const live = useDeviceLocation(active && !parked);

  const getParkedFix = useCallback(
    async (): Promise<GpsFix | null> =>
      parked && { latitude: parked.latitude, longitude: parked.longitude, accuracy_m: parked.accuracy_m, source: 'parked' },
    [parked],
  );
  const getLiveFix = useCallback(
    async (timeoutMs: number): Promise<GpsFix | null> => {
      const fix = await live.getFix(timeoutMs);
      return fix && { ...fix, source: 'live' };
    },
    [live],
  );

  if (parked) {
    return { source: 'parked', status: 'ready', accuracy: parked.accuracy_m, savedAt: parked.savedAt, getFix: getParkedFix };
  }
  return { source: 'live', status: live.status, accuracy: live.accuracy, savedAt: null, getFix: getLiveFix };
}
