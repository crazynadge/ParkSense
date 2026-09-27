import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Platform } from 'react-native';

import { ScanResultProvider } from '@/state/scan-result';
import { colors } from '@/theme/colors';

// Native RTL is forced via the expo-localization plugin in app.json. On web,
// react-native-web takes layout direction from the document instead.
if (Platform.OS === 'web' && typeof document !== 'undefined') {
  document.documentElement.dir = 'rtl';
  document.documentElement.lang = 'he';
}

export default function RootLayout() {
  return (
    <ScanResultProvider>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.surface },
          headerTintColor: colors.text,
          headerBackButtonDisplayMode: 'minimal',
          contentStyle: { backgroundColor: colors.background },
        }}
      >
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="scan" options={{ title: 'סריקת שלט' }} />
        <Stack.Screen name="result" options={{ title: 'תוצאה' }} />
        <Stack.Screen name="profile" options={{ title: 'פרופיל נהג' }} />
        <Stack.Screen name="dev-scenarios" options={{ title: 'תרחישים לדוגמה' }} />
      </Stack>
    </ScanResultProvider>
  );
}
