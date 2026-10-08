import { useIsFocused, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { analyzeParking, ApiError } from '@/api/client';
import { PrimaryButton } from '@/components/PrimaryButton';
import { useScanLocation } from '@/hooks/useScanLocation';
import { API_ERROR_TEXT } from '@/i18n/he';
import { SIGN_SCENARIOS } from '@/mocks/sign-scenarios';
import { DEMO_PROFILE } from '@/state/profile';
import { useScanResult } from '@/state/scan-result';
import { colors } from '@/theme/colors';

// Development only: sends hand-written sign data straight to the rule engine,
// bypassing the camera and Vision, to exercise every result state.
export default function DevScenariosScreen() {
  const router = useRouter();
  const { setDecision } = useScanResult();
  const [scenarioId, setScenarioId] = useState(SIGN_SCENARIOS[0].id);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const location = useScanLocation(useIsFocused());

  async function analyze() {
    const scenario = SIGN_SCENARIOS.find((s) => s.id === scenarioId) ?? SIGN_SCENARIOS[0];
    setLoading(true);
    setError(null);
    try {
      const decision = await analyzeParking({
        sign_data: scenario.signData,
        current_time: new Date().toISOString(),
        profile: DEMO_PROFILE,
        location: await location.getFix(3_000),
      });
      setDecision(decision);
      router.push('/result');
    } catch (e) {
      if (__DEV__) console.warn('analyze-parking failed', e);
      setError(API_ERROR_TEXT[e instanceof ApiError ? e.kind : 'server']);
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.scenarios} accessibilityRole="radiogroup">
        <Text style={styles.sectionTitle}>נתוני שלט לדוגמה, ישירות למנוע החוקים</Text>
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

      <PrimaryButton label="נתח" size="large" loading={loading} onPress={analyze} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    gap: 16,
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
