import { useCameraPermissions } from 'expo-camera';
import { useIsFocused, useRouter } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Image, Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError, scanSign } from '@/api/client';
import { PrimaryButton } from '@/components/PrimaryButton';
import { LocationPill } from '@/components/LocationPill';
import { SignCamera } from '@/components/SignCamera';
import { useScanLocation } from '@/hooks/useScanLocation';
import { API_ERROR_TEXT } from '@/i18n/he';
import { DEMO_PROFILE } from '@/state/profile';
import { useScanResult } from '@/state/scan-result';
import { colors } from '@/theme/colors';
import { prepareForUpload, type PreparedImage } from '@/utils/image';

export default function ScanScreen() {
  const router = useRouter();
  const isFocused = useIsFocused();
  const [permission, requestPermission] = useCameraPermissions();
  const { setDecision } = useScanResult();
  const [processingUri, setProcessingUri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Start locating as soon as the camera is up, so a fix is ready at the shutter.
  const location = useScanLocation(isFocused && permission?.granted === true);

  async function handleCapture(photo: PreparedImage) {
    setProcessingUri(photo.uri);
    setError(null);
    try {
      // Resize and location lookup run in parallel; a scan without GPS still works,
      // it just cannot verify resident permits.
      const [image, fix] = await Promise.all([prepareForUpload(photo), location.getFix(3_000)]);
      const decision = await scanSign({
        imageUri: image.uri,
        currentTime: new Date().toISOString(),
        profile: DEMO_PROFILE,
        location: fix,
      });
      setDecision(decision);
      router.push('/result');
    } catch (e) {
      if (__DEV__) console.warn('scan failed', e);
      setError(e instanceof ApiError ? API_ERROR_TEXT[e.kind] : 'עיבוד התמונה נכשל. נסו לצלם שוב.');
    } finally {
      setProcessingUri(null);
    }
  }

  if (!permission) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.centered}>
        <Text style={styles.permissionTitle}>נדרשת גישה למצלמה</Text>
        <Text style={styles.permissionBody}>
          כדי לבדוק אם מותר לחנות, צלמו את שלט החניה ואת אבן השפה. התמונה נשלחת לניתוח בלבד ואינה נשמרת.
        </Text>
        {permission.canAskAgain ? (
          <PrimaryButton label="אפשר גישה למצלמה" onPress={requestPermission} />
        ) : (
          <>
            <Text style={styles.permissionBody}>הגישה למצלמה נחסמה. ניתן לאפשר אותה בהגדרות המכשיר.</Text>
            <PrimaryButton label="פתח הגדרות" onPress={() => Linking.openSettings()} />
          </>
        )}
      </View>
    );
  }

  return (
    <View style={styles.cameraScreen}>
      {/* Only one camera preview may be active; release it while another screen is on top. */}
      {isFocused && (
        <SignCamera
          onCapture={handleCapture}
          onError={setError}
          disabled={processingUri !== null}
          accessory={<LocationPill location={location} />}
        />
      )}

      {processingUri && (
        <View style={StyleSheet.absoluteFill}>
          <Image source={{ uri: processingUri }} style={StyleSheet.absoluteFill} resizeMode="cover" />
          <View style={styles.processingOverlay}>
            <ActivityIndicator size="large" color="#FFFFFF" />
            <Text style={styles.processingText}>מנתח את השלט…</Text>
          </View>
        </View>
      )}

      {error && (
        <Pressable
          accessibilityRole="alert"
          accessibilityHint="הקישו כדי לסגור"
          onPress={() => setError(null)}
          style={styles.errorBanner}
        >
          <Text style={styles.errorText}>{error}</Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    padding: 24,
    gap: 16,
    justifyContent: 'center',
  },
  permissionTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
  },
  permissionBody: {
    fontSize: 16,
    lineHeight: 23,
    color: colors.textMuted,
  },
  cameraScreen: {
    flex: 1,
    backgroundColor: '#000000',
  },
  processingOverlay: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  processingText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  errorBanner: {
    position: 'absolute',
    top: 16,
    left: 16,
    right: 16,
    padding: 14,
    borderRadius: 12,
    backgroundColor: colors.status.red,
  },
  errorText: {
    color: '#FFFFFF',
    fontSize: 15,
    lineHeight: 21,
  },
});
