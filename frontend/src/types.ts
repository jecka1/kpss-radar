export type EducationLevel = 'lisans' | 'onlisans' | 'ortaogretim' | 'ilkogretim';

export type MatchStatus = 'eligible' | 'review' | 'ineligible';

export type UserAnnouncementStatus = 'none' | 'saved' | 'applied' | 'dismissed';

export type ReasonStatus = 'pass' | 'warn' | 'fail' | 'unknown';

export type KpssScoreKey =
  | 'P3'
  | 'P93'
  | 'P94'
  | 'P1'
  | 'P2'
  | 'P10'
  | 'P121'
  | 'EKPSS'
  | 'YDS';

export type KpssScores = Record<KpssScoreKey, number | null>;

export interface UserProfile {
  is_configured: boolean;
  full_name: string;
  kpss_year: number;
  education_level: EducationLevel;
  scores: KpssScores;
  departments: string[];
  qualification_codes: string[];
  birth_year: number | null;
  gender: string;
  military_status: string;
  driver_licenses: string[];
  certificates: string[];
  preferred_cities: string[];
  all_cities: boolean;
  preferred_categories: string[];
  include_no_kpss: boolean;
  scan_interval_minutes: number;
  telegram_bot_token: string;
  telegram_chat_id: string;
  webhook_url: string;
}

export interface ExtractedCriteria {
  kpss_types: string[];
  min_score: number | null;
  requires_kpss: boolean | null;
  education_levels: EducationLevel[] | string[];
  departments: string[];
  accepts_any_department: boolean;
  qualification_codes: string[];
  max_age: number | null;
  application_channel: string | null;
  has_pdf: boolean;
  missing_fields: string[];
  confidence: number;
}

export interface AnnouncementSource {
  source_name: string;
  source_label: string;
  url: string;
  pdf_url: string | null;
  scraped_at: string | null;
}

export interface MatchReason {
  field: 'education' | 'kpss_score' | 'department' | 'age' | 'city' | 'category' | string;
  label: string;
  status: ReasonStatus;
  message: string;
}

export interface MatchResult {
  match_status: MatchStatus;
  match_score: number;
  headline: string;
  reasons: MatchReason[];
}

export interface UserAnnouncementState {
  status: UserAnnouncementStatus;
  notes: string;
}

export interface AnnouncementItem {
  id: number;
  title: string;
  institution: string;
  category: string;
  city: string | null;
  cities: string[];
  publish_date: string | null;
  deadline_date: string | null;
  days_remaining: number | null;
  quota_count: number | null;
  summary: string;
  extracted: ExtractedCriteria;
  sources: AnnouncementSource[];
  match: MatchResult;
  user_state: UserAnnouncementState;
  first_seen_at: string | null;
  is_new: boolean;
}

export interface AnnouncementDetail extends AnnouncementItem {
  raw_text: string;
}

export interface AnnouncementListResponse {
  total: number;
  page: number;
  page_size: number;
  items: AnnouncementItem[];
}

export interface AnnouncementQueryParams {
  match_status?: 'all' | 'eligible' | 'review' | 'eligible_or_review' | 'ineligible';
  category?: string;
  source?: string;
  city?: string;
  user_status?: 'all' | 'saved' | 'applied' | 'dismissed' | 'active';
  deadline_soon?: boolean;
  q?: string;
  sort?: 'match_score' | 'deadline' | 'newest';
  page?: number;
  page_size?: number;
}

export interface SourceHealth {
  source_name: string;
  source_label: string;
  url: string;
  status: 'success' | 'error' | 'running' | 'idle' | string;
  items_found: number;
  items_new: number;
  last_run_at: string | null;
  error_message: string | null;
}

export interface StatsResponse {
  total_active: number;
  eligible_count: number;
  review_count: number;
  ineligible_count: number;
  deadline_soon_count: number;
  new_today_count: number;
  saved_count: number;
  applied_count: number;
  dismissed_count?: number;
  is_scanning: boolean;
  last_scan_at: string | null;
  categories: Record<string, number>;
  sources: SourceHealth[];
}

export interface ScrapeTriggerResponse {
  started: boolean;
  message: string;
}

export interface ScrapeRunInfo {
  id?: number;
  source_name: string;
  source_label?: string;
  status: string;
  items_found: number;
  items_new: number;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
}

export interface ScrapeStatusResponse {
  is_scanning: boolean;
  current_source: string | null;
  last_scan_at: string | null;
  runs: ScrapeRunInfo[];
}

export interface NitelikKodu {
  code: string;
  level: EducationLevel | string;
  title: string;
  departments: string[];
}

export interface CustomSource {
  id: number;
  name: string;
  url: string;
  keywords: string[];
  created_at?: string | null;
  last_checked_at?: string | null;
  items_found?: number;
}

export interface CustomSourceCreate {
  name: string;
  url: string;
  keywords: string[];
}

export interface NotificationTestResponse {
  sent: boolean;
  channel: string;
  error: string | null;
}

export interface InstitutionItem {
  name: string;
  url: string;
  city: string;
  status: string;
  found: number;
}

export interface InstitutionGroup {
  group_key: string;
  group_label: string;
  source_name: string;
  count: number;
  items: InstitutionItem[];
}

export interface InstitutionsCatalogResponse {
  total: number;
  groups: InstitutionGroup[];
}

export type ActiveTab = 'radar' | 'saved' | 'profile' | 'sources';
