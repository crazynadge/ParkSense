import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { analyzeParking, ApiError, type ApiErrorKind } from '@/api/client';
import { PrimaryButton } from '@/components/PrimaryButton';
import { SIGN_SCENARIOS } from '@/mocks/sign-scenarios';
import { DEMO_CITY, DEMO_PROFILE } from '@/state/profile';
import { useScanResult } from '@/state/scan-result';
import { colors } from '@/theme/colors';

const ERROR_MESSAGES: Record<ApiErrorKind, string> = {
  network: 'אין חיבור לשרת. הניתוח מתבצע בענן – בדקו את החיבור לאינטרנט ונסו שוב.',
  timeout: 'השרת לא הגיב בזמן. נסו שוב.',
  server: 'אירעה שגיאה בעיבוד הסריקה. נסו שוב.',
};

export default function ScanScreen() {
  const router = useRouter();
  const { setDecision } = useScanResult();
  const [scenarioId, setScenarioId] = useState(SIGN_SCENARIOS[0].id);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    const scenario = SIGN_SCENARIOS.find((s) => s.id === scenarioId) ?? SIGN_SCENARIOS[0];
    setLoading(true);
    setError(null);
    try {
      const decision = await analyzeParking({
        sign_data: scenario.signData,
        current_time: new Date().toISOString(),
        profile: DEMO_PROFILE,
        city: DEMO_CITY,
      });
      setDecision(decision);
      router.push('/result');
    } catch (e) {
      if (__DEV__) console.warn('analyze-parking failed', e);
      setError(ERROR_MESSAGES[e instanceof ApiError ? e.kind : 'server']);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Placeholder: the camera module replaces this frame in a later phase. */}
      <View style={styles.frame}>
        <Text style={styles.frameText}>תצוגת מצלמה</Text>
      </View>
      <Text style={styles.guidance}>ודאו שהשלט מואר וממורכז במסגרת.</Text>

      <View style={styles.scenarios} accessibilityRole="radiogroup">
        <Text style={styles.sectionTitle}>תרחיש לדוגמה (פיתוח)</Text>
        {SIGN_SCENARIOS.map((scenario) => {
          const selected = scenario.id === scenarioId;
          return (
            <Pressable
              key={scenario.id}
              accessibilityRole="radio"
              accessibilityState={{ checked: selected }}
              onPress={() => setScenarioId(scenario.id)}
              style={[styles.scenario, selected && styles.scenarioSelected]}
            >
              <Text style={[styles.scenarioText, selected && styles.scenarioTextSelected]}>{scenario.label}</Text>
            </Pressable>
          );
        })}
      </View>

      {error && <Text style={styles.error}>{error}</Text>}

      <PrimaryButton label="צלם ונתח" size="large" loading={loading} onPress={analyze} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    gap: 16,
  },
  frame: {
    height: 220,
    borderRadius: 20,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  frameText: {
    color: colors.textMuted,
  },
  guidance: {
    textAlign: 'center',
    color: colors.textMuted,
  },
  scenarios: {
    gap: 8,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.textMuted,
  },
  scenario: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  scenarioSelected: {
    borderColor: colors.primary,
    borderWidth: 2,
  },
  scenarioText: {
    fontSize: 15,
    color: colors.text,
  },
  scenarioTextSelected: {
    fontWeight: '600',
    color: colors.primary,
  },
  error: {
    color: colors.errorText,
    fontSize: 15,
    lineHeight: 21,
  },
});
