import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { PrimaryButton } from '@/components/PrimaryButton';
import { captureAccurateFix, LocationCaptureError } from '@/location/position';
import { useParkedLocation } from '@/state/parked-location';
import { colors } from '@/theme/colors';
import { formatAgo } from '@/utils/time';

const CAPTURE_ERRORS: Record<string, string> = {
  denied: 'אין הרשאת מיקום. אפשרו גישה למיקום בהגדרות המכשיר.',
  unavailable: 'שירותי המיקום כבויים במכשיר.',
  no_fix: 'לא התקבל מיקום. נסו שוב במקום פתוח יותר.',
};

/** "חניתי כאן": pin the car's position before walking to the sign. */
export function ParkedCard() {
  const { parked, loaded, save, clear } = useParkedLocation();
  const [capturing, setCapturing] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function capture() {
    setCapturing(true);
    setProgress(null);
    setError(null);
    try {
      const fix = await captureAccurateFix({}, (f) => setProgress(f.accuracy_m));
      await save(fix);
    } catch (e) {
      if (__DEV__) console.warn('parked capture failed', e);
      setError(e instanceof LocationCaptureError ? CAPTURE_ERRORS[e.kind] : 'שמירת המיקום נכשלה. נסו שוב.');
    } finally {
      setCapturing(false);
    }
  }

  if (!loaded) return null;

  return (
    <View style={styles.card}>
      {parked ? (
        <>
          <Text style={styles.title}>מיקום הרכב נשמר</Text>
          <Text style={styles.detail}>
            {formatAgo(parked.savedAt)}
            {parked.accuracy_m != null ? ` · דיוק ±${Math.round(parked.accuracy_m)} מ׳` : ''}
          </Text>
          <Text style={styles.detail}>הסריקות ייבדקו לפי מיקום הרכב, לא לפי המקום שבו מצלמים.</Text>
          <View style={styles.actions}>
            <View style={styles.action}>
              <PrimaryButton label="עדכון מיקום" variant="secondary" loading={capturing} onPress={capture} />
            </View>
            <View style={styles.action}>
              <PrimaryButton label="מחיקה" variant="secondary" disabled={capturing} onPress={() => clear()} />
            </View>
          </View>
        </>
      ) : (
        <>
          <PrimaryButton label="חניתי כאן" variant="secondary" loading={capturing} onPress={capture} />
          <Text style={styles.detail}>
            {capturing
              ? `מאתר את מיקום הרכב…${progress != null ? ` ±${Math.round(progress)} מ׳` : ''}`
              : 'שמרו את מיקום הרכב לפני שאתם הולכים לצלם את השלט.'}
          </Text>
        </>
      )}
      {error && <Text style={styles.error}>{error}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    padding: 16,
    gap: 8,
  },
  title: {
    fontSize: 17,
    fontWeight: '700',
    color: colors.text,
  },
  detail: {
    fontSize: 14,
    lineHeight: 20,
    color: colors.textMuted,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 4,
  },
  action: {
    flex: 1,
  },
  error: {
    fontSize: 14,
    lineHeight: 20,
    color: colors.errorText,
  },
});
