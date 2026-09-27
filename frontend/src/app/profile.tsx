import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/theme/colors';

// Placeholder: vehicle type, resident permits and disabled permit will be edited here.
export default function ProfileScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>כאן יוגדרו סוג הרכב, תווי חניה לתושבים ותו נכה.</Text>
      <Text style={styles.text}>
        כרגע הסריקות משתמשות בפרופיל לדוגמה: רכב פרטי, ללא תווים. העיר ואזור החניה נקבעים לפי מיקום
        המכשיר.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    gap: 12,
  },
  text: {
    color: colors.textMuted,
    fontSize: 16,
    lineHeight: 22,
  },
});
