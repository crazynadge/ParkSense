import { StyleSheet, Text, View } from 'react-native';

import type { LocationStatus } from '@/hooks/useDeviceLocation';

const LABELS: Record<LocationStatus, string> = {
  idle: 'מיקום',
  locating: 'מאתר מיקום…',
  ready: 'מיקום',
  denied: 'מיקום כבוי',
  unavailable: 'אין מיקום',
};

/** Location status over the camera, so the driver knows whether permits can be verified. */
export function LocationPill({ status, accuracy }: { status: LocationStatus; accuracy: number | null }) {
  const ok = status === 'ready';
  const label = ok && accuracy != null ? `מיקום ±${Math.round(accuracy)} מ׳` : LABELS[status];
  return (
    <View style={[styles.pill, !ok && styles.pillMuted]} accessible accessibilityLabel={label}>
      <View style={[styles.dot, ok ? styles.dotOk : styles.dotOff]} />
      <Text style={styles.text}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderRadius: 16,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
  },
  pillMuted: {
    opacity: 0.85,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotOk: {
    backgroundColor: '#4ADE80',
  },
  dotOff: {
    backgroundColor: '#FBBF24',
  },
  text: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '600',
  },
});
