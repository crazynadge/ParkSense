import * as Location from 'expo-location';
import { useCallback, useEffect, useRef, useState } from 'react';

import type { GpsFix } from '@/api/types';
import { stripTime, toFix, watchPosition, type Fix, type Unsubscribe } from '@/location/position';

// A fix older than this may be from before the driver parked.
const MAX_FIX_AGE_MS = 60_000;
const LAST_KNOWN_MAX_AGE_MS = 15_000;

export type LocationStatus = 'idle' | 'locating' | 'ready' | 'denied' | 'unavailable';

function isFresh(fix: Fix | null): fix is Fix {
  return fix !== null && Date.now() - fix.receivedAt <= MAX_FIX_AGE_MS;
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

  // The newest fix always wins. A "keep the more accurate one" rule looks tempting but
  // is wrong here: a cached fix from where the car was (accurate) would override a live
  // fix from where the phone is now (less accurate) after walking to the sign.
  const publish = useCallback((next: Fix) => {
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
      // A cached OS fix is only a head start, so keep it very recent: the driver may have
      // walked from the car to the sign since. expo-location applies maxAge itself.
      const lastKnown = await Location.getLastKnownPositionAsync({ maxAge: LAST_KNOWN_MAX_AGE_MS, requiredAccuracy: 100 });
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
    if (isFresh(latest.current)) return stripTime(latest.current);
    // No point waiting when location is off: scan without it.
    if (statusRef.current === 'denied' || statusRef.current === 'unavailable') return null;
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        waiters.current = waiters.current.filter((w) => w !== onFix);
        resolve(null);
      }, timeoutMs);
      const onFix = (next: Fix) => {
        clearTimeout(timer);
        resolve(stripTime(next));
      };
      waiters.current.push(onFix);
    });
  }, []);

  return { status, accuracy: fix?.accuracy_m ?? null, getFix };
}
