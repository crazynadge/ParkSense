import { CameraView } from 'expo-camera';
import { useRef, useState, type ReactNode } from 'react';
import { Platform, Pressable, StyleSheet, Text, View } from 'react-native';

import type { PreparedImage } from '@/utils/image';

type Props = {
  onCapture: (photo: PreparedImage) => void;
  onError: (message: string) => void;
  disabled?: boolean;
  /** Shown beside the shutter, e.g. a location status indicator. */
  accessory?: ReactNode;
};

/** Camera preview with a framing guide, torch toggle and shutter. */
export function SignCamera({ onCapture, onError, disabled, accessory }: Props) {
  const cameraRef = useRef<CameraView>(null);
  const [ready, setReady] = useState(false);
  const [torch, setTorch] = useState(false);
  const [capturing, setCapturing] = useState(false);

  async function capture() {
    if (!cameraRef.current || !ready || capturing || disabled) return;
    setCapturing(true);
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.8 });
      onCapture({ uri: photo.uri, width: photo.width, height: photo.height });
    } catch (e) {
      if (__DEV__) console.warn('takePictureAsync failed', e);
      onError('הצילום נכשל. נסו שוב.');
    } finally {
      setCapturing(false);
    }
  }

  return (
    <View style={styles.container}>
      <CameraView
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        facing="back"
        enableTorch={torch}
        onCameraReady={() => setReady(true)}
        onMountError={(e) => {
          if (__DEV__) console.warn('Camera mount error', e.message);
          onError('לא ניתן להפעיל את המצלמה במכשיר זה.');
        }}
      />

      <FrameGuide />

      <View style={styles.controls}>
        <View style={styles.slot}>
          {/* Browsers expose no torch control. */}
          {Platform.OS !== 'web' && (
            <Pressable
              accessibilityRole="switch"
              accessibilityLabel="פנס"
              accessibilityState={{ checked: torch }}
              onPress={() => setTorch((on) => !on)}
              style={[styles.torch, torch && styles.torchOn]}
            >
              <Text style={[styles.torchText, torch && styles.torchTextOn]}>פנס</Text>
            </Pressable>
          )}
        </View>
        <View style={styles.slot}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="צלם"
            accessibilityState={{ disabled: !ready || capturing || disabled }}
            disabled={!ready || capturing || disabled}
            onPress={capture}
            style={({ pressed }) => [styles.shutter, (pressed || capturing) && styles.shutterPressed, !ready && styles.shutterInactive]}
          >
            <View style={styles.shutterInner} />
          </Pressable>
        </View>
        <View style={styles.slot}>{accessory}</View>
      </View>
    </View>
  );
}

function FrameGuide() {
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <View style={[styles.dim, styles.guidanceArea]}>
        <Text style={styles.guidance}>מרכזו את השלט ואת אבן השפה בתוך המסגרת</Text>
        <Text style={styles.guidanceSub}>ודאו שהשלט מואר וקריא</Text>
      </View>
      <View style={styles.frameRow}>
        <View style={styles.dim} />
        <View style={styles.frame} />
        <View style={styles.dim} />
      </View>
      <View style={[styles.dim, styles.bottomDim]} />
    </View>
  );
}

const DIM = 'rgba(0, 0, 0, 0.55)';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000000',
  },
  dim: {
    flex: 1,
    backgroundColor: DIM,
  },
  guidanceArea: {
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingBottom: 16,
    gap: 4,
  },
  guidance: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '600',
    textAlign: 'center',
  },
  guidanceSub: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 14,
    textAlign: 'center',
  },
  frameRow: {
    flexDirection: 'row',
  },
  frame: {
    width: '78%',
    aspectRatio: 3 / 4,
    borderWidth: 3,
    borderColor: '#FFFFFF',
    borderRadius: 18,
  },
  bottomDim: {
    flex: 1.4, // leaves room for the controls
  },
  controls: {
    position: 'absolute',
    bottom: 28,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
  },
  slot: {
    flex: 1,
    alignItems: 'center',
  },
  torch: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.7)',
  },
  torchOn: {
    backgroundColor: '#FFFFFF',
  },
  torchText: {
    color: '#FFFFFF',
    fontWeight: '600',
  },
  torchTextOn: {
    color: '#000000',
  },
  shutter: {
    width: 76,
    height: 76,
    borderRadius: 38,
    borderWidth: 4,
    borderColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  shutterPressed: {
    transform: [{ scale: 0.92 }],
  },
  shutterInactive: {
    opacity: 0.4,
  },
  shutterInner: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#FFFFFF',
  },
});
