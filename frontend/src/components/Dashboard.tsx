import React, { useEffect, useMemo, useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  Sparkles,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  X,
  RefreshCw,
  SlidersHorizontal,
  LayoutList,
  Rows3,
} from 'lucide-react';
import type {
  AnnouncementItem,
  AnnouncementQueryParams,
  StatsResponse,
  UserAnnouncementStatus,
  UserProfile,
} from '../types';
import { CATEGORY_LIST, SOURCE_OPTIONS, TURKEY_CITIES } from '../constants';
import { AnnouncementCard } from './AnnouncementCard';
import { OnboardingBanner } from './OnboardingModal';

interface DashboardProps {
  profile: UserProfile | null;
  stats: StatsResponse | null;
  announcements: AnnouncementItem[];
  total: number;
  loading: boolean;
  error: string | null;
  filters: AnnouncementQueryParams;
  viewedIds: Set<number>;
  searchInputRef?: React.RefObject<HTMLInputElement | null>;
  onChangeFilters: (next: Partial<AnnouncementQueryParams>) => void;
  onResetFilters: () => void;
  onSelectAnnouncement: (id: number) => void;
  onUpdateState: (id: number, status: UserAnnouncementStatus, notes: string) => Promise<void>;
  onOpenOnboarding: () => void;
  onUseSampleProfile: () => Promise<void>;
  savingSample: boolean;
  onRetry: () => void;
}

const MATCH_TABS: {
  id: NonNullable<AnnouncementQueryParams['match_status']>;
  label: string;
}[] = [
  { id: 'eligible_or_review', label: 'Önerilen' },
  { id: 'eligible', label: 'Tam Uygun' },
  { id: 'review', label: 'İnceleme' },
  { id: 'all', label: 'Tümü' },
  { id: 'ineligible', label: 'Elenenler' },
];

const VIEW_MODE_KEY = 'kpss_radar_view_mode';

export const Dashboard: React.FC<DashboardProps> = ({
  profile,
  stats,
  announcements,
  total,
  loading,
  error,
  filters,
  viewedIds,
  searchInputRef,
  onChangeFilters,
  onResetFilters,
  onSelectAnnouncement,
  onUpdateState,
  onOpenOnboarding,
  onUseSampleProfile,
  savingSample,
  onRetry,
}) => {
  const [searchInput, setSearchInput] = useState(filters.q ?? '');
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [onlyUnviewed, setOnlyUnviewed] = useState(false);
  const [compactView, setCompactView] = useState<boolean>(() => {
    try {
      return localStorage.getItem(VIEW_MODE_KEY) === 'compact';
    } catch {
      return false;
    }
  });

  useEffect(() => {
    setSearchInput(filters.q ?? '');
  }, [filters.q]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if ((filters.q ?? '') !== searchInput) {
        onChangeFilters({ q: searchInput, page: 1 });
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput, filters.q, onChangeFilters]);

  const handleSetCompactView = (nextCompact: boolean) => {
    setCompactView(nextCompact);
    try {
      localStorage.setItem(VIEW_MODE_KEY, nextCompact ? 'compact' : 'detailed');
    } catch {
      // ignore
    }
  };

  const displayedAnnouncements = useMemo(() => {
    if (!onlyUnviewed) return announcements;
    return announcements.filter((item) => !viewedIds.has(item.id));
  }, [announcements, onlyUnviewed, viewedIds]);

  const currentPage = filters.page ?? 1;
  const pageSize = filters.page_size ?? 30;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const activeMatchTab = filters.match_status ?? 'eligible_or_review';

  const activeSelectFilterCount =
    (filters.category && filters.category !== 'all' ? 1 : 0) +
    (filters.source && filters.source !== 'all' ? 1 : 0) +
    (filters.city && filters.city !== 'all' ? 1 : 0) +
    (filters.deadline_soon ? 1 : 0) +
    (onlyUnviewed ? 1 : 0);

  const hasCustomFilter =
    activeSelectFilterCount > 0 || Boolean(filters.q && filters.q.trim());

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Onboarding Banner if profile not configured */}
      {profile && !profile.is_configured && (
        <OnboardingBanner
          onOpenWizard={onOpenOnboarding}
          onUseSampleProfile={onUseSampleProfile}
          savingSample={savingSample}
        />
      )}

      {/* Top KPI Strip: horizontal scroll on mobile, balanced grid on md+ */}
      <section className="flex overflow-x-auto snap-x gap-2.5 pb-1 md:pb-0 md:grid md:grid-cols-3 xl:grid-cols-5 md:gap-3.5">
        <button
          type="button"
          onClick={() =>
            onChangeFilters({ match_status: 'eligible', deadline_soon: false, page: 1 })
          }
          className={`min-w-[162px] sm:min-w-[180px] md:min-w-0 shrink-0 snap-start flex flex-col justify-between text-left p-3.5 sm:p-4 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow transition-all ${
            activeMatchTab === 'eligible'
              ? 'border-emerald-500 ring-2 ring-emerald-500/20'
              : 'border-slate-200 dark:border-slate-800 hover:border-emerald-300 dark:hover:border-emerald-700'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Size Tam Uygun
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 shrink-0">
              <CheckCircle2 className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-emerald-700 dark:text-emerald-400">
            {stats?.eligible_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
            Filtrelemek için tıklayın
          </div>
        </button>

        <button
          type="button"
          onClick={() =>
            onChangeFilters({ match_status: 'review', deadline_soon: false, page: 1 })
          }
          className={`min-w-[175px] sm:min-w-[190px] md:min-w-0 shrink-0 snap-start flex flex-col justify-between text-left p-3.5 sm:p-4 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow transition-all ${
            activeMatchTab === 'review'
              ? 'border-amber-500 ring-2 ring-amber-500/20'
              : 'border-slate-200 dark:border-slate-800 hover:border-amber-300 dark:hover:border-amber-700'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              İncelemeniz Gereken
            </span>
            <span className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 shrink-0">
              <AlertTriangle className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-amber-600 dark:text-amber-400">
            {stats?.review_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-medium text-amber-700 dark:text-amber-400 leading-tight">
            Kaçırma riskini sıfırlamak için kontrol edin
          </div>
        </button>

        <button
          type="button"
          onClick={() =>
            onChangeFilters({
              deadline_soon: !filters.deadline_soon,
              match_status: 'all',
              page: 1,
            })
          }
          className={`min-w-[155px] sm:min-w-[170px] md:min-w-0 shrink-0 snap-start flex flex-col justify-between text-left p-3.5 sm:p-4 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow transition-all ${
            filters.deadline_soon
              ? 'border-red-500 ring-2 ring-red-500/20'
              : 'border-slate-200 dark:border-slate-800 hover:border-red-300 dark:hover:border-red-700'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Son 5 Gün (Acil)
            </span>
            <span className="p-1.5 rounded-lg bg-red-50 dark:bg-red-950/60 text-red-600 dark:text-red-400 shrink-0">
              <Clock className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-red-600 dark:text-red-400">
            {stats?.deadline_soon_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-medium text-red-600 dark:text-red-400">
            {filters.deadline_soon ? 'Acil filtresi aktif' : 'Acil ilanları göster'}
          </div>
        </button>

        <button
          type="button"
          onClick={() =>
            onChangeFilters({ match_status: 'all', deadline_soon: false, page: 1 })
          }
          className={`min-w-[155px] sm:min-w-[170px] md:min-w-0 shrink-0 snap-start flex flex-col justify-between text-left p-3.5 sm:p-4 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm hover:shadow transition-all ${
            activeMatchTab === 'all' && !filters.deadline_soon
              ? 'border-slate-900 dark:border-slate-400 ring-2 ring-slate-900/15 dark:ring-slate-400/20'
              : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Toplam Aktif İlan
            </span>
            <span className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 shrink-0">
              <Layers className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100">
            {stats?.total_active ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-medium text-slate-500 dark:text-slate-400">
            Tüm aktif kamu alımları
          </div>
        </button>

        <div className="min-w-[155px] sm:min-w-[170px] md:min-w-0 shrink-0 snap-start flex flex-col justify-between text-left p-3.5 sm:p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
              Yeni İlanlar
            </span>
            <span className="p-1.5 rounded-lg bg-sky-50 dark:bg-sky-950/60 text-sky-600 dark:text-sky-400 shrink-0">
              <Sparkles className="w-4 h-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-sky-700 dark:text-sky-400">
            {stats?.new_today_count ?? 0}
          </div>
          <div className="mt-1 text-[11px] font-medium text-slate-500 dark:text-slate-400">
            Son 3 günde yayımlanan
          </div>
        </div>
      </section>

      {/* Smart Tabs + Filter Bar */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-3.5 sm:p-4 space-y-3">
        {/* Smart Tabs (Single line on desktop) */}
        <div className="flex flex-wrap md:flex-nowrap items-center gap-1.5 border-b border-slate-100 dark:border-slate-800 pb-3 overflow-x-auto">
          {MATCH_TABS.map((tab) => {
            const isActive = activeMatchTab === tab.id;
            let countBadge: number | undefined;
            if (stats) {
              if (tab.id === 'eligible_or_review') {
                countBadge = stats.eligible_count + stats.review_count;
              } else if (tab.id === 'eligible') countBadge = stats.eligible_count;
              else if (tab.id === 'review') countBadge = stats.review_count;
              else if (tab.id === 'all') countBadge = stats.total_active;
              else if (tab.id === 'ineligible') countBadge = stats.ineligible_count;
            }

            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onChangeFilters({ match_status: tab.id, page: 1 })}
                className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap shrink-0 transition-all ${
                  isActive
                    ? 'bg-slate-900 dark:bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <span>{tab.label}</span>
                {countBadge !== undefined && (
                  <span
                    className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : 'bg-slate-200/80 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
                    }`}
                  >
                    {countBadge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Search + Mobile Filter Toggle + Desktop Selects */}
        <div className="flex flex-col xl:flex-row gap-2.5 items-stretch xl:items-center">
          {/* Search + Mobile Toggle Row */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="relative flex-1 min-w-0">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Kurum, unvan, bölüm, 4001... ( / )"
                className="w-full h-10 pl-9 pr-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/80 focus:bg-white dark:focus:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchInput('');
                    onChangeFilters({ q: '', page: 1 });
                  }}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                  aria-label="Aramayı temizle"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => setMobileFiltersOpen((prev) => !prev)}
              className="md:hidden h-10 inline-flex items-center gap-1.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-200 shrink-0"
            >
              <SlidersHorizontal className="w-4 h-4" />
              <span>Filtreler</span>
              {activeSelectFilterCount > 0 && (
                <span className="px-1.5 py-0.5 rounded-full bg-indigo-600 text-white text-[10px]">
                  {activeSelectFilterCount}
                </span>
              )}
            </button>
          </div>

          {/* Selects Grid — collapsible on mobile, always visible on md+ */}
          <div
            className={`${
              mobileFiltersOpen ? 'grid' : 'hidden'
            } md:grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 xl:flex xl:flex-nowrap gap-2.5 shrink-0`}
          >
            {/* Category */}
            <select
              value={filters.category ?? 'all'}
              onChange={(e) => onChangeFilters({ category: e.target.value, page: 1 })}
              aria-label="Kategori filtresi"
              className="w-full min-w-0 xl:w-40 h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-slate-700 dark:text-slate-200 font-medium focus:border-indigo-500 focus:outline-none"
            >
              <option value="all">Tüm Kategoriler</option>
              {CATEGORY_LIST.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>

            {/* Source */}
            <select
              value={filters.source ?? 'all'}
              onChange={(e) => onChangeFilters({ source: e.target.value, page: 1 })}
              aria-label="Kaynak filtresi"
              className="w-full min-w-0 xl:w-40 h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-slate-700 dark:text-slate-200 font-medium focus:border-indigo-500 focus:outline-none"
            >
              {SOURCE_OPTIONS.map((src) => (
                <option key={src.value} value={src.value}>
                  {src.label}
                </option>
              ))}
            </select>

            {/* City */}
            <select
              value={filters.city ?? 'all'}
              onChange={(e) => onChangeFilters({ city: e.target.value, page: 1 })}
              aria-label="Şehir filtresi"
              className="w-full min-w-0 xl:w-36 h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-slate-700 dark:text-slate-200 font-medium focus:border-indigo-500 focus:outline-none"
            >
              <option value="all">Tüm Şehirler</option>
              <option value="Türkiye Geneli">Türkiye Geneli</option>
              {TURKEY_CITIES.map((city) => (
                <option key={city} value={city}>
                  {city}
                </option>
              ))}
            </select>

            {/* Sort */}
            <select
              value={filters.sort ?? 'match_score'}
              onChange={(e) =>
                onChangeFilters({
                  sort: e.target.value as AnnouncementQueryParams['sort'],
                  page: 1,
                })
              }
              aria-label="Sıralama"
              className="w-full min-w-0 xl:w-44 h-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 text-sm text-slate-700 dark:text-slate-200 font-medium focus:border-indigo-500 focus:outline-none"
            >
              <option value="match_score">Sırala: Uygunluk</option>
              <option value="deadline">Sırala: Son Başvuru</option>
              <option value="newest">Sırala: En Yeni</option>
            </select>
          </div>
        </div>

        {/* Secondary Toggle Row */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1">
          <div className="flex flex-wrap items-center gap-2">
            <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200 select-none">
              <input
                type="checkbox"
                checked={Boolean(filters.deadline_soon)}
                onChange={(e) =>
                  onChangeFilters({ deadline_soon: e.target.checked, page: 1 })
                }
                className="rounded text-red-600 focus:ring-red-500"
              />
              <span>Sadece Son 5 Gün</span>
            </label>

            <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-200 select-none">
              <input
                type="checkbox"
                checked={onlyUnviewed}
                onChange={(e) => setOnlyUnviewed(e.target.checked)}
                className="rounded text-indigo-600 focus:ring-indigo-500"
              />
              <span>Sadece İncelemediklerim</span>
            </label>

            {hasCustomFilter && (
              <button
                type="button"
                onClick={() => {
                  setOnlyUnviewed(false);
                  onResetFilters();
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Sıfırla</span>
              </button>
            )}
          </div>

          <div className="flex items-center gap-3 ml-auto">
            <div className="text-xs font-medium text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5" />
              <span>
                <strong className="text-slate-900 dark:text-slate-100">
                  {onlyUnviewed ? displayedAnnouncements.length : total}
                </strong>{' '}
                ilan
              </span>
            </div>

            {/* Compact / Detailed View Switcher */}
            <div className="inline-flex p-0.5 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
              <button
                type="button"
                onClick={() => handleSetCompactView(false)}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold transition-colors ${
                  !compactView
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
                title="Detaylı Kart Görünümü"
              >
                <Rows3 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Detaylı</span>
              </button>
              <button
                type="button"
                onClick={() => handleSetCompactView(true)}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold transition-colors ${
                  compactView
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
                }`}
                title="Kompakt Liste Görünümü"
              >
                <LayoutList className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Kompakt</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Error State */}
      {error && (
        <div className="rounded-2xl border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/40 p-6 text-center space-y-3">
          <p className="text-sm font-semibold text-red-800 dark:text-red-300">{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Tekrar Dene</span>
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !error && (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 animate-pulse space-y-3"
            >
              <div className="flex gap-4">
                <div className="w-14 h-14 rounded-2xl bg-slate-200 dark:bg-slate-800 shrink-0" />
                <div className="flex-1 space-y-2.5">
                  <div className="h-4 w-48 bg-slate-200 dark:bg-slate-800 rounded" />
                  <div className="h-5 w-3/4 bg-slate-200 dark:bg-slate-800 rounded" />
                  <div className="flex gap-2">
                    <div className="h-5 w-24 bg-slate-100 dark:bg-slate-800 rounded" />
                    <div className="h-5 w-20 bg-slate-100 dark:bg-slate-800 rounded" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && displayedAnnouncements.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-10 text-center space-y-3">
          <p className="text-base font-bold text-slate-800 dark:text-slate-100">
            Seçili filtrelere uygun ilan bulunamadı
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            Filtreleri genişletebilir, &quot;Tümü&quot; sekmesine geçebilir veya sol menüden
            kaynakları yeniden taratabilirsiniz.
          </p>
          <div className="pt-2 flex flex-wrap items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => {
                setOnlyUnviewed(false);
                onResetFilters();
              }}
              className="px-4 py-2 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-bold"
            >
              Tüm Filtreleri Sıfırla
            </button>
          </div>
        </div>
      )}

      {/* Announcements List */}
      {!loading && !error && displayedAnnouncements.length > 0 && (
        <div className={compactView ? 'space-y-2' : 'space-y-3.5'}>
          {displayedAnnouncements.map((item) => (
            <AnnouncementCard
              key={item.id}
              item={item}
              onSelect={onSelectAnnouncement}
              onUpdateState={onUpdateState}
              showIneligibleReasons={activeMatchTab === 'ineligible'}
              compact={compactView}
              isViewed={viewedIds.has(item.id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 px-4 py-3">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
            Sayfa <strong className="text-slate-900 dark:text-white">{currentPage}</strong> /{' '}
            {totalPages}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={currentPage <= 1}
              onClick={() => onChangeFilters({ page: currentPage - 1 })}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Önceki</span>
            </button>
            <button
              type="button"
              disabled={currentPage >= totalPages}
              onClick={() => onChangeFilters({ page: currentPage + 1 })}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40"
            >
              <span>Sonraki</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
