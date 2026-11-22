import React, { useState } from 'react';
import {
  Radar,
  BookmarkCheck,
  UserCheck,
  Radio,
  RefreshCw,
  Menu,
  X,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  Sun,
  Moon,
} from 'lucide-react';
import type { ActiveTab, StatsResponse, UserProfile } from '../types';
import { EDUCATION_LABELS, formatRelativeDateTime } from '../constants';

interface SidebarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  profile: UserProfile | null;
  stats: StatsResponse | null;
  isScanning: boolean;
  currentSource: string | null;
  onTriggerScan: () => void;
  onOpenOnboarding: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

const SOURCE_DISPLAY_NAMES: Record<string, string> = {
  sbb_kamuilan: 'SBB Kamu İlan',
  memurlar_net: 'Memurlar.net',
  resmi_gazete: 'Resmî Gazete',
  osym: 'ÖSYM',
  isinolsa: 'İşin Olsa Kamu',
  bakanliklar_kurumlar: 'Bakanlıklar & Kamu Kurumları',
  kurullar_kitler: "Yargı, Üst Kurullar & KİT'ler",
  belediyeler: 'Büyükşehir Belediyeleri',
  il_belediyeleri: 'İl Belediyeleri (44)',
  universiteler: 'Üniversiteler (PDB)',
};

function buildProfileSummary(profile: UserProfile | null): {
  title: string;
  subtitle: string;
  configured: boolean;
} {
  if (!profile || !profile.is_configured) {
    return {
      title: 'Profil Ayarlanmadı',
      subtitle: 'Puan ve bölümünüzü ekleyerek uygunluk analizi başlatın',
      configured: false,
    };
  }

  const eduLabel = EDUCATION_LABELS[profile.education_level] ?? profile.education_level;
  const primaryOrder: (keyof UserProfile['scores'])[] = [
    'P3',
    'P93',
    'P94',
    'P1',
    'P2',
    'P10',
    'P121',
    'EKPSS',
    'YDS',
  ];
  const topScoreKey = primaryOrder.find(
    (key) => typeof profile.scores[key] === 'number' && profile.scores[key] !== null
  );
  const scorePart = topScoreKey ? `${topScoreKey}: ${profile.scores[topScoreKey]}` : 'Puansız';
  const deptPart =
    profile.departments.length > 0 ? profile.departments[0] : 'Bölüm belirtilmedi';

  return {
    title: profile.full_name && profile.full_name !== 'Aday' ? profile.full_name : 'Aday Profili',
    subtitle: `${eduLabel} • ${scorePart} • ${deptPart}`,
    configured: true,
  };
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  profile,
  stats,
  isScanning,
  currentSource,
  onTriggerScan,
  onOpenOnboarding,
  theme,
  onToggleTheme,
}) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  const summary = buildProfileSummary(profile);
  const savedTotal = (stats?.saved_count ?? 0) + (stats?.applied_count ?? 0);
  const radarCount = stats
    ? stats.eligible_count + stats.review_count
    : 0;

  const currentSourceLabel = currentSource
    ? SOURCE_DISPLAY_NAMES[currentSource] ?? currentSource
    : null;

  const navItems: {
    id: ActiveTab;
    label: string;
    icon: React.ReactNode;
    badge?: number;
    badgeTone?: string;
    warnDot?: boolean;
  }[] = [
    {
      id: 'radar',
      label: 'İlan Radarı',
      icon: <Radar className="w-5 h-5" />,
      badge: radarCount > 0 ? radarCount : undefined,
      badgeTone: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
    },
    {
      id: 'saved',
      label: 'Kayıtlar & Başvurular',
      icon: <BookmarkCheck className="w-5 h-5 shrink-0" />,
      badge: savedTotal > 0 ? savedTotal : undefined,
      badgeTone: 'bg-indigo-500/20 text-indigo-200 border border-indigo-500/30',
    },
    {
      id: 'profile',
      label: 'Aday Profilim',
      icon: <UserCheck className="w-5 h-5" />,
      warnDot: !summary.configured,
    },
    {
      id: 'sources',
      label: 'Kaynaklar & Bildirimler',
      icon: <Radio className="w-5 h-5" />,
    },
  ];

  const handleNavClick = (tab: ActiveTab) => {
    onSelectTab(tab);
    setMobileOpen(false);
  };

  const sidebarContent = (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 select-none">
      {/* Brand Header */}
      <div className="px-5 pt-6 pb-5 border-b border-slate-800/80">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-950/50">
              <Radar className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold tracking-tight text-white">KPSS Radar</h1>
              </div>
              <p className="text-[11px] font-medium text-slate-400">
                Kamu Alım & Uygunluk Motoru
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={onToggleTheme}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              title={theme === 'dark' ? 'Açık Temaya Geç' : 'Karanlık Temaya Geç'}
              aria-label={theme === 'dark' ? 'Açık Temaya Geç' : 'Karanlık Temaya Geç'}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
            </button>
            <button
              type="button"
              onClick={() => setMobileOpen(false)}
              className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
              aria-label="Menüyü kapat"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="mt-3.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-[11px] font-medium">
          <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
          <span>Sıfır-Kaçırma Garantili Takip</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto scrollbar-dark">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleNavClick(item.id)}
              className={`w-full flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? 'bg-slate-800/95 text-white shadow-sm ring-1 ring-slate-700/80'
                  : 'text-slate-300 hover:text-white hover:bg-slate-900'
              }`}
            >
              <span className="flex items-center gap-3 min-w-0">
                <span className={isActive ? 'text-emerald-400' : 'text-slate-400'}>
                  {item.icon}
                </span>
                <span className="truncate">{item.label}</span>
              </span>
              {item.badge !== undefined && (
                <span
                  className={`px-2 py-0.5 text-xs font-semibold rounded-full shrink-0 ${item.badgeTone}`}
                >
                  {item.badge}
                </span>
              )}
              {item.warnDot && (
                <span
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-300 shrink-0"
                  title="Profiliniz henüz yapılandırılmadı"
                >
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Profile Summary & Scan Trigger */}
      <div className="p-4 border-t border-slate-800/80 space-y-3 bg-slate-950/90">
        {/* Live Profile Summary Card */}
        <div
          onClick={() => {
            if (!summary.configured) {
              onOpenOnboarding();
            } else {
              handleNavClick('profile');
            }
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              if (!summary.configured) {
                onOpenOnboarding();
              } else {
                handleNavClick('profile');
              }
            }
          }}
          className={`p-3 rounded-xl border transition-colors cursor-pointer ${
            summary.configured
              ? 'bg-slate-900/90 border-slate-800 hover:border-slate-700'
              : 'bg-amber-950/40 border-amber-500/40 hover:border-amber-400/60'
          }`}
        >
          <div className="flex items-center justify-between gap-2 mb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Aktif Profil
            </span>
            {summary.configured ? (
              <span className="text-[11px] font-medium text-emerald-400">Düzenle</span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-300">
                <Sparkles className="w-3 h-3" />
                30 sn Kur
              </span>
            )}
          </div>
          <p className="text-xs font-semibold text-white truncate">{summary.title}</p>
          <p className="text-xs text-slate-300 mt-0.5 line-clamp-2 leading-relaxed">
            {summary.subtitle}
          </p>
        </div>

        {/* Trigger Scan Button */}
        <div>
          <button
            type="button"
            onClick={onTriggerScan}
            disabled={isScanning}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all shadow-sm ${
              isScanning
                ? 'bg-emerald-600/30 text-emerald-200 border border-emerald-500/40 cursor-wait'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white active:scale-[0.99]'
            }`}
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
            <span>{isScanning ? 'Kaynaklar Taranıyor...' : 'Şimdi Tüm Kaynakları Tara'}</span>
          </button>

          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400 px-1">
            {isScanning ? (
              <span className="text-emerald-300 font-medium truncate">
                {currentSourceLabel
                  ? `Taranıyor: ${currentSourceLabel}`
                  : 'Resmi portallar kontrol ediliyor...'}
              </span>
            ) : (
              <>
                <span>Son tarama:</span>
                <span className="text-slate-300 font-medium">
                  {formatRelativeDateTime(stats?.last_scan_at)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile Top Header */}
      <header className="lg:hidden sticky top-0 z-30 bg-slate-950 text-white border-b border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Radar className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="font-bold text-sm tracking-tight">KPSS Radar</span>
            {isScanning && (
              <span className="ml-2 inline-flex items-center gap-1 text-[11px] text-emerald-300">
                <RefreshCw className="w-3 h-3 animate-spin" />
                {currentSourceLabel ?? 'Taranıyor'}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleTheme}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100"
            title={theme === 'dark' ? 'Açık Temaya Geç' : 'Karanlık Temaya Geç'}
            aria-label={theme === 'dark' ? 'Açık Temaya Geç' : 'Karanlık Temaya Geç'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={onTriggerScan}
            disabled={isScanning}
            className="p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white"
            title="Şimdi Tüm Kaynakları Tara"
          >
            <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100"
            aria-label="Menüyü aç"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Slide-out Sidebar */}
      <aside
        className={`lg:hidden fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-200 ease-out ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Desktop Fixed Sidebar */}
      <aside className="hidden lg:block lg:w-72 lg:shrink-0 lg:sticky lg:top-0 lg:h-screen border-r border-slate-800">
        {sidebarContent}
      </aside>
    </>
  );
};
