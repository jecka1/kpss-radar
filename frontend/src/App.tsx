import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getAnnouncements,
  getProfile,
  getScrapeStatus,
  getStats,
  triggerScrape,
  updateAnnouncementState,
  updateProfile,
} from './api';
import type {
  ActiveTab,
  AnnouncementItem,
  AnnouncementQueryParams,
  StatsResponse,
  UserAnnouncementStatus,
  UserProfile,
} from './types';
import { SAMPLE_PROFILE } from './constants';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { SavedApplicationsPage } from './components/SavedApplicationsPage';
import { ProfilePage } from './components/ProfilePage';
import { SourcesPage } from './components/SourcesPage';
import { DetailDrawer } from './components/DetailDrawer';
import { OnboardingModal } from './components/OnboardingModal';

const THEME_STORAGE_KEY = 'kpss_radar_theme';
const VIEWED_IDS_STORAGE_KEY = 'kpss_radar_viewed_ids';
const BROWSER_NOTIF_STORAGE_KEY = 'kpss_radar_browser_notif';

const DEFAULT_FILTERS: AnnouncementQueryParams = {
  match_status: 'eligible_or_review',
  category: 'all',
  source: 'all',
  city: 'all',
  user_status: 'active',
  deadline_soon: false,
  q: '',
  sort: 'match_score',
  page: 1,
  page_size: 30,
};

function loadInitialTheme(): 'light' | 'dark' {
  try {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {
    // ignore storage errors
  }
  return 'light';
}

function loadInitialViewedIds(): number[] {
  try {
    const raw = localStorage.getItem(VIEWED_IDS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'number') : [];
  } catch {
    return [];
  }
}

export const App: React.FC = () => {
  const [theme, setTheme] = useState<'light' | 'dark'>(loadInitialTheme);
  const [viewedIdsList, setViewedIdsList] = useState<number[]>(loadInitialViewedIds);
  const viewedIdsSet = useMemo(() => new Set(viewedIdsList), [viewedIdsList]);

  const [activeTab, setActiveTab] = useState<ActiveTab>('radar');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);

  const [filters, setFilters] = useState<AnnouncementQueryParams>(DEFAULT_FILTERS);
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [totalAnnouncements, setTotalAnnouncements] = useState(0);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [isScanning, setIsScanning] = useState(false);
  const [currentSource, setCurrentSource] = useState<string | null>(null);
  const preScanEligibleRef = useRef<number | null>(null);

  const [selectedAnnouncementId, setSelectedAnnouncementId] = useState<number | null>(null);
  const [onboardingOpen, setOnboardingOpen] = useState(false);
  const [savingSample, setSavingSample] = useState(false);
  const [savedRefreshKey, setSavedRefreshKey] = useState(0);

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement | null>(null);

  // Apply theme class to <html>
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      // ignore
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage((prev) => (prev === msg ? null : prev));
    }, 3500);
  }, []);

  const loadStatsAndProfile = useCallback(async () => {
    try {
      const [prof, st] = await Promise.all([getProfile(), getStats()]);
      setProfile(prof);
      setStats(st);
      setIsScanning(Boolean(st.is_scanning));
      return st;
    } catch {
      return null;
    }
  }, []);

  const loadAnnouncements = useCallback(async (params: AnnouncementQueryParams) => {
    setLoadingList(true);
    setListError(null);
    try {
      const res = await getAnnouncements(params);
      setAnnouncements(res.items);
      setTotalAnnouncements(res.total);
    } catch (err) {
      setListError(
        err instanceof Error
          ? `Veriler alınamadı: ${err.message}`
          : 'Sunucuya bağlanılamadı. Backend servisinin çalıştığından emin olun.'
      );
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [activeTab]);

  useEffect(() => {
    void loadStatsAndProfile();
  }, [loadStatsAndProfile]);

  useEffect(() => {
    void loadAnnouncements(filters);
  }, [filters, loadAnnouncements]);

  // Global keyboard shortcuts: '/' focuses search, 'Esc' closes drawer/modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (selectedAnnouncementId !== null) {
          setSelectedAnnouncementId(null);
          return;
        }
        if (onboardingOpen) {
          setOnboardingOpen(false);
          return;
        }
      }

      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = e.target as HTMLElement | null;
        const tag = target?.tagName?.toUpperCase();
        const isEditable =
          tag === 'INPUT' ||
          tag === 'TEXTAREA' ||
          tag === 'SELECT' ||
          Boolean(target?.isContentEditable);
        if (isEditable) return;

        e.preventDefault();
        if (activeTab !== 'radar') {
          setActiveTab('radar');
        }
        setTimeout(() => {
          searchInputRef.current?.focus();
        }, 20);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, selectedAnnouncementId, onboardingOpen]);

  // Poll scrape status while scanning is active
  useEffect(() => {
    if (!isScanning) return;

    if (preScanEligibleRef.current === null && stats) {
      preScanEligibleRef.current = stats.eligible_count;
    }

    let active = true;
    const interval = setInterval(async () => {
      try {
        const status = await getScrapeStatus();
        if (!active) return;
        setCurrentSource(status.current_source);
        if (!status.is_scanning) {
          setIsScanning(false);
          setCurrentSource(null);
          const prevEligible = preScanEligibleRef.current;
          preScanEligibleRef.current = null;
          const [nextStats] = await Promise.all([
            loadStatsAndProfile(),
            loadAnnouncements(filters),
          ]);
          showToast('Tüm kaynakların taraması tamamlandı ve ilanlar güncellendi.');

          // Browser desktop notification if enabled & eligible count increased
          try {
            const notifEnabled = localStorage.getItem(BROWSER_NOTIF_STORAGE_KEY) === 'true';
            if (
              notifEnabled &&
              typeof Notification !== 'undefined' &&
              Notification.permission === 'granted' &&
              nextStats &&
              prevEligible !== null &&
              nextStats.eligible_count > prevEligible
            ) {
              const diff = nextStats.eligible_count - prevEligible;
              new Notification('KPSS Radar — Yeni Uygun İlan!', {
                body: `Profilinize tam uygun ${diff} yeni kamu alım ilanı bulundu (Toplam: ${nextStats.eligible_count}).`,
              });
            }
          } catch {
            // ignore Notification errors
          }
        }
      } catch {
        // retry next tick
      }
    }, 1500);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [isScanning, stats, filters, loadAnnouncements, loadStatsAndProfile, showToast]);

  const handleSelectAnnouncement = useCallback((id: number) => {
    setSelectedAnnouncementId(id);
    setViewedIdsList((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id].slice(-500);
      try {
        localStorage.setItem(VIEWED_IDS_STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const handleChangeFilters = useCallback((next: Partial<AnnouncementQueryParams>) => {
    setFilters((prev) => ({ ...prev, ...next }));
  }, []);

  const handleResetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  const handleTriggerScan = useCallback(
    async (source = 'all') => {
      try {
        preScanEligibleRef.current = stats?.eligible_count ?? 0;
        setIsScanning(true);
        const res = await triggerScrape(source);
        if (res.started) {
          showToast(res.message || 'Kaynak taraması başlatıldı...');
        } else {
          showToast(res.message || 'Tarama zaten devam ediyor.');
        }
      } catch (err) {
        setIsScanning(false);
        preScanEligibleRef.current = null;
        showToast(err instanceof Error ? err.message : 'Tarama başlatılamadı.');
      }
    },
    [stats?.eligible_count, showToast]
  );

  const handleSaveProfile = useCallback(
    async (nextProfile: UserProfile) => {
      const updated = await updateProfile(nextProfile);
      setProfile(updated);
      await Promise.all([loadStatsAndProfile(), loadAnnouncements(filters)]);
      setSavedRefreshKey((k) => k + 1);
      showToast('Profil güncellendi ve uygunluk skorları yenilendi.');
    },
    [filters, loadAnnouncements, loadStatsAndProfile, showToast]
  );

  const handleUseSampleProfile = useCallback(async () => {
    setSavingSample(true);
    try {
      await handleSaveProfile({ ...SAMPLE_PROFILE, is_configured: true });
    } finally {
      setSavingSample(false);
    }
  }, [handleSaveProfile]);

  const handleUpdateAnnouncementState = useCallback(
    async (id: number, status: UserAnnouncementStatus, notes: string) => {
      await updateAnnouncementState(id, { status, notes });

      // Optimistically update local state
      setAnnouncements((prev) => {
        if (status === 'dismissed' && filters.user_status === 'active') {
          return prev.filter((item) => item.id !== id);
        }
        return prev.map((item) =>
          item.id === id ? { ...item, user_state: { status, notes } } : item
        );
      });

      setSavedRefreshKey((k) => k + 1);
      void loadStatsAndProfile();

      const labelMap: Record<UserAnnouncementStatus, string> = {
        saved: 'İlan kaydedildi.',
        applied: 'Başvuruldu olarak işaretlendi.',
        dismissed: 'İlan gizlendi.',
        none: 'Takip durumu sıfırlandı.',
      };
      showToast(labelMap[status]);
    },
    [filters.user_status, loadStatsAndProfile, showToast]
  );

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        profile={profile}
        stats={stats}
        isScanning={isScanning}
        currentSource={currentSource}
        onTriggerScan={() => void handleTriggerScan('all')}
        onOpenOnboarding={() => setOnboardingOpen(true)}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
        {activeTab === 'radar' && (
          <Dashboard
            profile={profile}
            stats={stats}
            announcements={announcements}
            total={totalAnnouncements}
            loading={loadingList}
            error={listError}
            filters={filters}
            viewedIds={viewedIdsSet}
            searchInputRef={searchInputRef}
            onChangeFilters={handleChangeFilters}
            onResetFilters={handleResetFilters}
            onSelectAnnouncement={handleSelectAnnouncement}
            onUpdateState={handleUpdateAnnouncementState}
            onOpenOnboarding={() => setOnboardingOpen(true)}
            onUseSampleProfile={handleUseSampleProfile}
            savingSample={savingSample}
            onRetry={() => {
              void loadStatsAndProfile();
              void loadAnnouncements(filters);
            }}
          />
        )}

        {activeTab === 'saved' && (
          <SavedApplicationsPage
            stats={stats}
            viewedIds={viewedIdsSet}
            onGoToRadar={() => setActiveTab('radar')}
            onSelectAnnouncement={handleSelectAnnouncement}
            onUpdateState={handleUpdateAnnouncementState}
            refreshKey={savedRefreshKey}
          />
        )}

        {activeTab === 'profile' && (
          <ProfilePage profile={profile} onSaveProfile={handleSaveProfile} />
        )}

        {activeTab === 'sources' && (
          <SourcesPage
            profile={profile}
            stats={stats}
            isScanning={isScanning}
            currentSource={currentSource}
            onTriggerSourceScan={handleTriggerScan}
            onSaveProfile={handleSaveProfile}
            onSelectAnnouncement={handleSelectAnnouncement}
            onAnnouncementImported={() => {
              void loadStatsAndProfile();
              void loadAnnouncements(filters);
              showToast('İlan başarıyla analiz edildi ve listeye eklendi.');
            }}
          />
        )}
      </main>

      {/* Slide-over Detail Drawer */}
      <DetailDrawer
        announcementId={selectedAnnouncementId}
        profile={profile}
        searchQuery={filters.q ?? ''}
        onClose={() => setSelectedAnnouncementId(null)}
        onUpdateState={handleUpdateAnnouncementState}
      />

      {/* Quick Start Onboarding Modal */}
      <OnboardingModal
        isOpen={onboardingOpen}
        initialProfile={profile}
        onClose={() => setOnboardingOpen(false)}
        onSaveProfile={handleSaveProfile}
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 max-w-sm bg-slate-900 dark:bg-slate-800 text-white px-4 py-3 rounded-xl shadow-xl border border-slate-700 text-xs sm:text-sm font-semibold">
          {toastMessage}
        </div>
      )}
    </div>
  );
};

export default App;
