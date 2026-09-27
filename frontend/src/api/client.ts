import Constants from 'expo-constants';
import { Platform } from 'react-native';

import type { AnalyzeParkingRequest, GpsFix, ParkingDecision, UserProfile } from './types';

const JSON_TIMEOUT_MS = 10_000;
// Uploads include the photo, so allow more time on a weak cellular connection.
const UPLOAD_TIMEOUT_MS = 20_000;

/**
 * EXPO_PUBLIC_API_URL wins. Otherwise use the dev machine's LAN address (the host
 * Metro is served from), so a physical phone running Expo Go can reach the backend.
 */
function resolveBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) return fromEnv.replace(/\/$/, '');
  const devHost = Constants.expoConfig?.hostUri?.split(':')[0];
  return `http://${devHost ?? 'localhost'}:8000`;
}

export const API_BASE_URL = resolveBaseUrl();

export type ApiErrorKind = 'network' | 'timeout' | 'server' | 'unavailable';

export class ApiError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function post<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, method: 'POST', signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError('timeout', `Request timed out after ${timeoutMs} ms`);
    }
    throw new ApiError('network', error instanceof Error ? error.message : String(error));
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    // 503: the Vision provider is down or overloaded; the photo itself was fine.
    const kind = response.status === 503 ? 'unavailable' : 'server';
    throw new ApiError(kind, `HTTP ${response.status}: ${await response.text()}`, response.status);
  }
  return (await response.json()) as T;
}

/** Rule engine only, with already-extracted sign data (development scenarios). */
export function analyzeParking(request: AnalyzeParkingRequest): Promise<ParkingDecision> {
  return post<ParkingDecision>(
    '/api/v1/analyze-parking',
    { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) },
    JSON_TIMEOUT_MS,
  );
}

export type ScanRequest = {
  imageUri: string; // JPEG
  currentTime: string; // ISO 8601
  profile: UserProfile;
  location: GpsFix | null;
};

/** Full pipeline: photo -> Vision extraction -> rule engine. */
export async function scanSign({ imageUri, currentTime, profile, location }: ScanRequest): Promise<ParkingDecision> {
  const form = new FormData();
  if (Platform.OS === 'web') {
    // On web the image URI is a blob:/data: URL; upload the bytes with an explicit type.
    const bytes = await (await fetch(imageUri)).blob();
    form.append('image', new Blob([bytes], { type: 'image/jpeg' }), 'sign.jpg');
  } else {
    // React Native's FormData streams the file from disk given { uri, name, type }.
    form.append('image', { uri: imageUri, name: 'sign.jpg', type: 'image/jpeg' } as unknown as Blob);
  }
  form.append('current_time', currentTime);
  form.append('profile', JSON.stringify(profile));
  if (location) {
    form.append('latitude', String(location.latitude));
    form.append('longitude', String(location.longitude));
    if (location.accuracy_m != null) form.append('accuracy_m', String(location.accuracy_m));
  }

  // No Content-Type header: fetch sets multipart/form-data with the boundary itself.
  return post<ParkingDecision>('/api/v1/scan', { body: form }, UPLOAD_TIMEOUT_MS);
}
