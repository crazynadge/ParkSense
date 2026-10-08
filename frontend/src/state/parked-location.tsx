import * as SecureStore from 'expo-secure-store';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Platform } from 'react-native';

import type { GpsFix } from '@/api/types';

// A saved spot older than this is almost certainly not where the car is now.
export const PARKED_MAX_AGE_MS = 24 * 60 * 60 * 1000;

const STORAGE_KEY = 'parksense.parked-location.v1';
// Keychain item never syncs to iCloud or migrates to another device.
const SECURE_OPTIONS: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
};

export type ParkedLocation = GpsFix & { savedAt: number };

// SecureStore has no web implementation; on web (development only) keep it in memory.
let webMemory: string | null = null;
const storage = {
  get: () => (Platform.OS === 'web' ? Promise.resolve(webMemory) : SecureStore.getItemAsync(STORAGE_KEY, SECURE_OPTIONS)),
  set: (value: string) =>
    Platform.OS === 'web'
      ? Promise.resolve(void (webMemory = value))
      : SecureStore.setItemAsync(STORAGE_KEY, value, SECURE_OPTIONS),
  remove: () =>
    Platform.OS === 'web' ? Promise.resolve(void (webMemory = null)) : SecureStore.deleteItemAsync(STORAGE_KEY, SECURE_OPTIONS),
};

function isValid(value: unknown): value is ParkedLocation {
  const v = value as ParkedLocation;
  return (
    typeof v?.latitude === 'number' &&
    typeof v?.longitude === 'number' &&
    typeof v?.savedAt === 'number' &&
    Date.now() - v.savedAt <= PARKED_MAX_AGE_MS
  );
}

type ParkedLocationState = {
  /** The saved car position, or null if none is saved or it has expired. */
  parked: ParkedLocation | null;
  loaded: boolean;
  save: (fix: GpsFix) => Promise<void>;
  clear: () => Promise<void>;
};

const ParkedLocationContext = createContext<ParkedLocationState | null>(null);

export function ParkedLocationProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useState<ParkedLocation | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    storage
      .get()
      .then((raw) => {
        const value = raw ? JSON.parse(raw) : null;
        if (isValid(value)) setStored(value);
        else if (raw) return storage.remove(); // expired or malformed
      })
      .catch((error) => {
        if (__DEV__) console.warn('Could not read parked location', error);
      })
      .finally(() => setLoaded(true));
  }, []);

  const save = useCallback(async (fix: GpsFix) => {
    const value: ParkedLocation = {
      latitude: fix.latitude,
      longitude: fix.longitude,
      accuracy_m: fix.accuracy_m,
      savedAt: Date.now(),
    };
    await storage.set(JSON.stringify(value));
    setStored(value);
  }, []);

  const clear = useCallback(async () => {
    await storage.remove();
    setStored(null);
  }, []);

  // Re-checked on every render so an expired spot stops being used without a restart.
  const parked = stored && isValid(stored) ? stored : null;
  const value = useMemo(() => ({ parked, loaded, save, clear }), [parked, loaded, save, clear]);
  return <ParkedLocationContext.Provider value={value}>{children}</ParkedLocationContext.Provider>;
}

export function useParkedLocation(): ParkedLocationState {
  const state = useContext(ParkedLocationContext);
  if (!state) throw new Error('useParkedLocation must be used inside ParkedLocationProvider');
  return state;
}
