import * as Location from 'expo-location';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';

import type { GpsFix } from '@/api/types';

// A fix older than this may be from before the driver parked.
const MAX_FIX_AGE_MS = 60_000;

export type LocationStatus = 'idle' | 'locating' | 'ready' | 'denied' | 'unavailable';

// receivedAt is our own clock, not the position's timestamp: a phone whose clock is
// off would otherwise reject every fix as stale (or accept old ones as fresh).
type Fix = GpsFix & { receivedAt: number };

type Coords = { latitude: number; longitude: number; accuracy: number | null };

function toFix(coords: Coords): Fix {
  return {
    latitude: coords.latitude,
    longitude: coords.longitude,
    accuracy_m: coords.accuracy ?? null,
    receivedAt: Date.now(),
  };
}

function isFresh(fix: Fix | null): fix is Fix {
  return fix !== null && Date.now() - fix.receivedAt <= MAX_FIX_AGE_MS;
}

type Unsubscribe = () => void;

async function watchPosition(onFix: (fix: Fix) => void): Promise<Unsubscribe> {
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

/**
 * Tracks the device location while `active` (e.g. while the camera screen is focused),
 * so a fix is usually ready by the time the shutter is pressed.
 */
export function useDeviceLocation(active: boolean) {
  const [status, setStatusState] = useState<LocationStatus>('idle');
  const statusRef = useRef<LocationStatus>('idle');
  const setStatus = useCallback((next: LocationStatus | ((prev: LocationStatus) => LocationStatus)) => {
    statusRef.current = typeof next === 'function' ? next(statusRef.current) : next;
    setStatusState(statusRef.current);
  }, []);
  const [fix, setFix] = useState<Fix | null>(null);
  const latest = useRef<Fix | null>(null);
  const waiters = useRef<((fix: Fix) => void)[]>([]);

  const publish = useCallback((next: Fix) => {
    // Keep the more accurate of two fresh fixes.
    const current = latest.current;
    const moreAccurate = (current?.accuracy_m ?? Infinity) < (next.accuracy_m ?? Infinity);
    if (isFresh(current) && moreAccurate && next.receivedAt - current.receivedAt < 10_000) {
      return;
    }
    latest.current = next;
    setFix(next);
    setStatus('ready');
    waiters.current.splice(0).forEach((resolve) => resolve(next));
  }, [setStatus]);

  useEffect(() => {
    if (!active) return;
    let unsubscribe: Unsubscribe | null = null;
    let cancelled = false;

    (async () => {
      setStatus((s) => (s === 'ready' ? s : 'locating'));
      const permission = await Location.requestForegroundPermissionsAsync();
      if (cancelled) return;
      if (!permission.granted) {
        setStatus('denied');
        return;
      }
      if (!(await Location.hasServicesEnabledAsync())) {
        if (!cancelled) setStatus('unavailable');
        return;
      }
      // expo-location filters by maxAge itself, using the position's own timestamp.
      const lastKnown = await Location.getLastKnownPositionAsync({ maxAge: MAX_FIX_AGE_MS, requiredAccuracy: 100 });
      if (cancelled) return;
      if (lastKnown) publish(toFix(lastKnown.coords));
      unsubscribe = await watchPosition(publish);
      if (cancelled) unsubscribe();
    })().catch((error) => {
      if (__DEV__) console.warn('location failed', error);
      if (!cancelled) setStatus('unavailable');
    });

    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, [active, publish, setStatus]);

  /** The latest fresh fix; waits up to `timeoutMs` for one if needed. Null if none arrives. */
  const getFix = useCallback(async (timeoutMs: number): Promise<GpsFix | null> => {
    const strip = ({ receivedAt: _, ...gps }: Fix): GpsFix => gps;
    if (isFresh(latest.current)) return strip(latest.current);
    // No point waiting when location is off: scan without it.
    if (statusRef.current === 'denied' || statusRef.current === 'unavailable') return null;
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        waiters.current = waiters.current.filter((w) => w !== onFix);
        resolve(null);
      }, timeoutMs);
      const onFix = (next: Fix) => {
        clearTimeout(timer);
        resolve(strip(next));
      };
      waiters.current.push(onFix);
    });
  }, []);

  return { status, accuracy: fix?.accuracy_m ?? null, getFix };
}
