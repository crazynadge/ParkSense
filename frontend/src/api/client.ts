import Constants from 'expo-constants';

import type { AnalyzeParkingRequest, ParkingDecision } from './types';

const REQUEST_TIMEOUT_MS = 10_000;

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

export type ApiErrorKind = 'network' | 'timeout' | 'server';

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

export async function analyzeParking(request: AnalyzeParkingRequest): Promise<ParkingDecision> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/v1/analyze-parking`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError('timeout', `Request timed out after ${REQUEST_TIMEOUT_MS} ms`);
    }
    throw new ApiError('network', error instanceof Error ? error.message : String(error));
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    throw new ApiError('server', `HTTP ${response.status}: ${await response.text()}`, response.status);
  }
  return (await response.json()) as ParkingDecision;
}
