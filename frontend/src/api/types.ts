// Mirrors backend/app/schemas. Keep in sync until types are generated from OpenAPI.

export type Weekday = 'sun' | 'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat';
export type CurbMarking = 'blue_white' | 'red_white' | 'gray' | 'none' | 'unknown';
export type RuleType =
  | 'no_stopping'
  | 'no_parking'
  | 'paid'
  | 'time_limited'
  | 'residents_only'
  | 'loading_zone'
  | 'disabled_only';

export type ResidentZone = { city?: string | null; zone: string };

export type TimeWindow = {
  days?: Weekday[];
  start?: string | null; // "HH:MM"
  end?: string | null;
};

export type ParkingRule = {
  rule_type: RuleType;
  windows?: TimeWindow[];
  max_duration_minutes?: number | null;
  price_per_hour?: number | null;
  exempt_resident_zones?: ResidentZone[];
  exempt_disabled?: boolean | null;
  raw_text?: string | null;
};

export type ParkingSignData = {
  schema_version?: string;
  sign_detected: boolean;
  is_legible?: boolean;
  confidence: number;
  curb_marking?: CurbMarking;
  rules?: ParkingRule[];
  unreadable_fields?: string[];
};

export type VehicleType = 'private' | 'commercial' | 'motorcycle';

export type UserProfile = {
  vehicle_type: VehicleType;
  resident_permits: { city: string; zone: string }[];
  has_disabled_permit: boolean;
};

export type AnalyzeParkingRequest = {
  sign_data: ParkingSignData;
  current_time: string; // ISO 8601
  profile: UserProfile;
  city?: string | null;
};

export type ParkingStatus = 'green' | 'orange' | 'red' | 'unknown';
export type CostType = 'free' | 'paid' | 'exempt' | 'unknown';

export type ReasonCode =
  | 'no_restriction'
  | 'red_white_curb'
  | 'no_stopping'
  | 'no_parking'
  | 'disabled_only'
  | 'loading_zone'
  | 'residents_only'
  | 'paid'
  | 'time_limited'
  | 'sign_illegible'
  | 'low_confidence'
  | 'partial_sign'
  | 'nothing_detected'
  | 'paid_hours_unknown'
  | 'paid_rate_unknown'
  | 'max_duration_unknown'
  | 'resident_city_unknown';

export type PermittedBy = 'disabled_permit' | 'resident_permit' | 'commercial_vehicle';

export type Reason = {
  code: ReasonCode;
  message: string; // English, debugging only
  permitted_by: PermittedBy | null;
  params: Record<string, string>;
};

export type CostInfo = {
  type: CostType;
  price_per_hour: number | null;
  currency: string;
};

export type UpcomingChange = {
  at: string;
  status: ParkingStatus;
  reasons: Reason[];
};

export type ParkingDecision = {
  status: ParkingStatus;
  summary: string;
  evaluated_at: string; // ISO 8601 in Israel local time
  allowed_until: string | null;
  max_stay_minutes: number | null;
  cost: CostInfo;
  next_change: UpcomingChange | null;
  reasons: Reason[];
  warnings: Reason[];
};
