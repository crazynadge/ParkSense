import { StyleSheet, Text, View } from 'react-native';

import type { LocationStatus } from '@/hooks/useDeviceLocation';
import type { ScanLocation } from '@/hooks/useScanLocation';
import { formatAgo } from '@/utils/time';

const LABELS: Record<LocationStatus, string> = {
  idle: 'מיקום',
  locating: 'מאתר מיקום…',
  ready: 'מיקום',
  denied: 'מיקום כבוי',
  unavailable: 'אין מיקום',
};

function label({ source, status, accuracy, savedAt }: ScanLocation): string {
  if (source === 'parked' && savedAt != null) return `מיקום הרכב · ${formatAgo(savedAt)}`;
  if (status === 'ready' && accuracy != null) return `מיקום ±${Math.round(accuracy)} מ׳`;
  return LABELS[status];
}

/** Which location the scan will be judged by, shown over the camera. */
export function LocationPill({ location }: { location: ScanLocation }) {
  const ok = location.status === 'ready';
  const text = label(location);
  return (
    <View style={styles.pill} accessible accessibilityLabel={text}>
      <View style={[styles.dot, location.source === 'parked' ? styles.dotParked : ok ? styles.dotOk : styles.dotOff]} />
      <Text style={styles.text} numberOfLines={1}>
        {text}
      </Text>
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
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotOk: {
    backgroundColor: '#4ADE80',
  },
  dotParked: {
    backgroundColor: '#60A5FA',
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
