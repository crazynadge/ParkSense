import * as Location from 'expo-location';
import { Platform } from 'react-native';

import type { GpsFix } from '@/api/types';

// receivedAt is our own clock, not the position's timestamp: a phone whose clock is
// off would otherwise reject every fix as stale (or accept old ones as fresh).
export type Fix = GpsFix & { receivedAt: number };

type Coords = { latitude: number; longitude: number; accuracy: number | null };

export function toFix(coords: Coords): Fix {
  return {
    latitude: coords.latitude,
    longitude: coords.longitude,
    accuracy_m: coords.accuracy ?? null,
    receivedAt: Date.now(),
  };
}

export function stripTime({ receivedAt: _, ...gps }: Fix): GpsFix {
  return gps;
}

export type Unsubscribe = () => void;

export async function watchPosition(onFix: (fix: Fix) => void): Promise<Unsubscribe> {
  if (Platform.OS === 'web') {
    // expo-location's web watchPositionAsync overwrites its internal watch id with the
    // browser's, so updates never reach the callback. Use the browser API directly.
    const id = navigator.geolocation.watchPosition(
      (position) => onFix(toFix(position.coords)),
      (error) => {
        if (__DEV__) console.warn('geolocation.watchPosition error', error.message);
      },
      { enableHighAccuracy: true, maximumAge: 5_000 },
    );
    return () => navigator.geolocation.clearWatch(id);
  }
  const subscription = await Location.watchPositionAsync(
    { accuracy: Location.Accuracy.High, timeInterval: 2_000, distanceInterval: 3 },
    (position) => onFix(toFix(position.coords)),
    (error) => {
      if (__DEV__) console.warn('watchPositionAsync error', error);
    },
  );
  return () => subscription.remove();
}

export type CaptureError = 'denied' | 'unavailable' | 'no_fix';

export class LocationCaptureError extends Error {
  constructor(readonly kind: CaptureError) {
    super(kind);
    this.name = 'LocationCaptureError';
  }
}

/**
 * The most accurate fix obtainable within `timeoutMs`, returning early once accuracy
 * reaches `targetAccuracyM`. Used to pin the car's position when the driver gets out.
 */
export async function captureAccurateFix(
  { targetAccuracyM = 15, timeoutMs = 12_000 } = {},
  onProgress?: (fix: Fix) => void,
): Promise<Fix> {
  const permission = await Location.requestForegroundPermissionsAsync();
  if (!permission.granted) throw new LocationCaptureError('denied');
  if (!(await Location.hasServicesEnabledAsync())) throw new LocationCaptureError('unavailable');

  let best: Fix | null = null;
  let settled = false;
  let stop: Unsubscribe | null = null;

  return new Promise<Fix>((resolve, reject) => {
    const settle = (outcome: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      stop?.();
      outcome();
    };
    const finish = () => settle(() => (best ? resolve(best) : reject(new LocationCaptureError('no_fix'))));
    const timer = setTimeout(finish, timeoutMs);

    watchPosition((fix) => {
      if (settled) return;
      if (!best || (fix.accuracy_m ?? Infinity) <= (best.accuracy_m ?? Infinity)) {
        best = fix;
        onProgress?.(fix);
      }
      if ((fix.accuracy_m ?? Infinity) <= targetAccuracyM) finish();
    }).then(
      // The subscription can arrive after we already settled: release it immediately.
      (unsubscribe) => (settled ? unsubscribe() : (stop = unsubscribe)),
      (error) => settle(() => reject(error)),
    );
  });
}
