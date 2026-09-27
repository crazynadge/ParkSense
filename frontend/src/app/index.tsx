import { Link, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PrimaryButton } from '@/components/PrimaryButton';
import { DISCLAIMER } from '@/i18n/he';
import { colors } from '@/theme/colors';

export default function HomeScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>ParkSense</Text>
        <Text style={styles.tagline}>מותר לחנות כאן עכשיו? לכמה זמן ובאיזה מחיר?</Text>
      </View>

      <View style={styles.main}>
        <PrimaryButton label="סרוק שלט" size="large" onPress={() => router.push('/scan')} />
        <Text style={styles.hint}>צלמו את שלט החניה ואת אבן השפה ליד הרכב.</Text>
      </View>

      <View style={styles.footer}>
        <Link href="/profile" style={styles.link}>
          פרופיל נהג
        </Link>
        <Text style={styles.disclaimer}>{DISCLAIMER}</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 24,
    backgroundColor: colors.background,
  },
  header: {
    paddingTop: 48,
    gap: 8,
  },
  title: {
    // Latin text would otherwise align to the left in an RTL layout.
    alignSelf: 'flex-start',
    fontSize: 34,
    fontWeight: '800',
    color: colors.text,
  },
  tagline: {
    fontSize: 17,
    lineHeight: 24,
    color: colors.textMuted,
  },
  main: {
    flex: 1,
    justifyContent: 'center',
    gap: 16,
  },
  hint: {
    textAlign: 'center',
    color: colors.textMuted,
  },
  footer: {
    paddingBottom: 16,
    gap: 16,
    alignItems: 'center',
  },
  link: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: '600',
  },
  disclaimer: {
    fontSize: 12,
    lineHeight: 17,
    textAlign: 'center',
    color: colors.textMuted,
  },
});
