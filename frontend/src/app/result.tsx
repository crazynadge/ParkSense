import { Redirect, useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import type { ParkingDecision, ParkingStatus } from '@/api/types';
import { PrimaryButton } from '@/components/PrimaryButton';
import { costText, DISCLAIMER, reasonText, STATUS_HEADLINE } from '@/i18n/he';
import { useScanResult } from '@/state/scan-result';
import { colors } from '@/theme/colors';
import { formatDuration, formatLocalTime } from '@/utils/time';

const STATUS_SYMBOL: Record<ParkingStatus, string> = {
  green: '✓',
  orange: '!',
  red: '✕',
  unknown: '?',
};

export default function ResultScreen() {
  const router = useRouter();
  const { decision } = useScanResult();

  if (!decision) return <Redirect href="/" />;

  const isUnknown = decision.status === 'unknown';

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View
        style={[styles.banner, { backgroundColor: colors.status[decision.status] }]}
        accessible
        accessibilityRole="header"
        accessibilityLabel={STATUS_HEADLINE[decision.status]}
      >
        <Text style={styles.symbol}>{STATUS_SYMBOL[decision.status]}</Text>
        <Text style={styles.headline}>{STATUS_HEADLINE[decision.status]}</Text>
        {decision.reasons.map((reason, i) => (
          <Text key={i} style={styles.bannerReason}>
            {reasonText(reason)}
          </Text>
        ))}
      </View>

      {!isUnknown && <Details decision={decision} />}

      {decision.warnings.length > 0 && (
        <View style={styles.warnings}>
          <Text style={styles.warningsTitle}>שימו לב</Text>
          {decision.warnings.map((warning, i) => (
            <Text key={i} style={styles.warningText}>
              {reasonText(warning)}
            </Text>
          ))}
        </View>
      )}

      <View style={styles.actions}>
        <PrimaryButton label={isUnknown ? 'צלם שוב' : 'סריקה נוספת'} onPress={() => router.back()} />
        <PrimaryButton label="למסך הבית" variant="secondary" onPress={() => router.dismissAll()} />
      </View>

      <Text style={styles.footnote}>נבדק בשעה {formatLocalTime(decision.evaluated_at, decision.evaluated_at)}</Text>
      <Text style={styles.footnote}>{DISCLAIMER}</Text>
    </ScrollView>
  );
}

function Details({ decision }: { decision: ParkingDecision }) {
  const { allowed_until, max_stay_minutes, next_change, evaluated_at, status } = decision;
  const isRed = status === 'red';
  if (isRed && !next_change) return null;
  return (
    <View style={styles.card}>
      {!isRed && (
        <Row
          label="עד מתי"
          value={allowed_until ? formatLocalTime(allowed_until, evaluated_at) : 'ללא הגבלה בימים הקרובים'}
        />
      )}
      {max_stay_minutes != null && <Row label="זמן חניה מרבי" value={formatDuration(max_stay_minutes)} />}
      {!isRed && <Row label="עלות" value={costText(decision.cost)} last={!next_change} />}
      {next_change && (
        <Row
          label="שינוי הבא"
          value={`${formatLocalTime(next_change.at, evaluated_at)} · ${STATUS_HEADLINE[next_change.status]}`}
          detail={next_change.reasons.map(reasonText).join('\n')}
          last
        />
      )}
    </View>
  );
}

function Row({ label, value, detail, last }: { label: string; value: string; detail?: string; last?: boolean }) {
  return (
    <View style={[styles.row, !last && styles.rowDivider]}>
      <Text style={styles.rowLabel}>{label}</Text>
      <View style={styles.rowValueColumn}>
        <Text style={styles.rowValue}>{value}</Text>
        {detail ? <Text style={styles.rowDetail}>{detail}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    gap: 16,
  },
  banner: {
    borderRadius: 24,
    paddingVertical: 28,
    paddingHorizontal: 20,
    alignItems: 'center',
    gap: 6,
  },
  symbol: {
    fontSize: 44,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  headline: {
    fontSize: 28,
    fontWeight: '800',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  bannerReason: {
    fontSize: 16,
    lineHeight: 22,
    color: '#FFFFFF',
    textAlign: 'center',
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 16,
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 14,
    gap: 12,
  },
  rowDivider: {
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  rowLabel: {
    fontSize: 15,
    color: colors.textMuted,
  },
  rowValueColumn: {
    flexShrink: 1,
    alignItems: 'flex-end',
    gap: 4,
  },
  rowValue: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.text,
  },
  rowDetail: {
    fontSize: 13,
    color: colors.textMuted,
  },
  warnings: {
    backgroundColor: colors.warningBackground,
    borderRadius: 16,
    padding: 16,
    gap: 6,
  },
  warningsTitle: {
    fontWeight: '700',
    color: colors.warningText,
  },
  warningText: {
    color: colors.warningText,
    lineHeight: 20,
  },
  actions: {
    gap: 10,
  },
  footnote: {
    fontSize: 12,
    lineHeight: 17,
    textAlign: 'center',
    color: colors.textMuted,
  },
});
