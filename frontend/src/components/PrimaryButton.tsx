import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { colors } from '@/theme/colors';

type Props = {
  label: string;
  onPress: () => void;
  size?: 'regular' | 'large';
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  loading?: boolean;
};

export function PrimaryButton({ label, onPress, size = 'regular', variant = 'primary', disabled, loading }: Props) {
  const large = size === 'large';
  const secondary = variant === 'secondary';
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive, busy: loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        large && styles.large,
        secondary
          ? styles.secondary
          : { backgroundColor: pressed ? colors.primaryPressed : colors.primary },
        inactive && styles.inactive,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={secondary ? colors.primary : '#FFFFFF'} />
      ) : (
        <Text style={[styles.label, large && styles.largeLabel, secondary && styles.secondaryLabel]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 24,
    alignItems: 'center',
  },
  large: {
    paddingVertical: 22,
    borderRadius: 20,
  },
  secondary: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  inactive: {
    opacity: 0.6,
  },
  label: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  largeLabel: {
    fontSize: 22,
    fontWeight: '700',
  },
  secondaryLabel: {
    color: colors.primary,
  },
});
