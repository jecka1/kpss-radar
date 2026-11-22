import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ExternalLink,
  FileText,
  Building2,
  MapPin,
  Users,
  CalendarClock,
  Save,
  Copy,
  Check,
  Send,
  Loader2,
  Search,
  Sparkles,
} from 'lucide-react';
import { getAnnouncementDetail } from '../api';
import type {
  AnnouncementDetail,
  ReasonStatus,
  UserAnnouncementStatus,
  UserProfile,
} from '../types';
import {
  CATEGORY_LABELS,
  EDUCATION_LABELS,
  deduplicateAnnouncementLinks,
  formatTurkishDate,
} from '../constants';

interface DetailDrawerProps {
  announcementId: number | null;
  profile: UserProfile | null;
  searchQuery?: string;
  onClose: () => void;
  onUpdateState: (id: number, status: UserAnnouncementStatus, notes: string) => Promise<void>;
}

const USER_STATUS_OPTIONS: { value: UserAnnouncementStatus; label: string; activeClass: string }[] = [
  {
    value: 'none',
    label: 'Takip Etme',
    activeClass: 'bg-slate-800 dark:bg-slate-700 text-white border-slate-800 dark:border-slate-600',
  },
  {
    value: 'saved',
    label: 'Kaydet',
    activeClass: 'bg-indigo-600 text-white border-indigo-600',
  },
  {
    value: 'applied',
    label: 'Başvurdum',
    activeClass: 'bg-emerald-600 text-white border-emerald-600',
  },
  {
    value: 'dismissed',
    label: 'Gizle',
    activeClass: 'bg-slate-600 text-white border-slate-600',
  },
];

function getReasonIcon(status: ReasonStatus) {
  switch (status) {
    case 'pass':
      return <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />;
    case 'warn':
      return <AlertTriangle className="w-4 h-4 text-amber-500 dark:text-amber-400 shrink-0 mt-0.5" />;
    case 'fail':
      return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />;
    default:
      return <HelpCircle className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />;
  }
}

function getReasonRowClass(status: ReasonStatus) {
  switch (status) {
    case 'pass':
      return 'bg-emerald-50/70 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/70 text-emerald-950 dark:text-emerald-200';
    case 'warn':
      return 'bg-amber-50/70 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800/70 text-amber-950 dark:text-amber-200';
    case 'fail':
      return 'bg-red-50/70 dark:bg-red-950/40 border-red-200 dark:border-red-800/70 text-red-950 dark:text-red-200';
    default:
      return 'bg-slate-50 dark:bg-slate-800/70 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200';
  }
}

function toTurkishPattern(term: string): string {
  return term
    .split('')
    .map((ch) => {
      if (ch === 'i' || ch === 'İ' || ch === 'ı' || ch === 'I') return '[iİıI]';
      if (ch === 'ğ' || ch === 'Ğ') return '[ğĞ]';
      if (ch === 'ü' || ch === 'Ü') return '[üÜ]';
      if (ch === 'ş' || ch === 'Ş') return '[şŞ]';
      if (ch === 'ö' || ch === 'Ö') return '[öÖ]';
      if (ch === 'ç' || ch === 'Ç') return '[çÇ]';
      return ch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    })
    .join('');
}

export const DetailDrawer: React.FC<DetailDrawerProps> = ({
  announcementId,
  profile,
  searchQuery = '',
  onClose,
  onUpdateState,
}) => {
  const [detail, setDetail] = useState<AnnouncementDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<UserAnnouncementStatus>('none');
  const [notes, setNotes] = useState('');
  const [savingState, setSavingState] = useState(false);
  const [savedFeedback, setSavedFeedback] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [drawerSearch, setDrawerSearch] = useState('');

  const rawTextBoxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (announcementId === null) {
      setDetail(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setSavedFeedback(false);
    setDrawerSearch(searchQuery.trim());

    getAnnouncementDetail(announcementId)
      .then((data) => {
        if (cancelled) return;
        setDetail(data);
        setSelectedStatus(data.user_state?.status ?? 'none');
        setNotes(data.user_state?.notes ?? '');
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'İlan detayı yüklenemedi.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [announcementId, searchQuery]);

  // Build profile terms to highlight
  const profileTerms = useMemo(() => {
    if (!profile) return [];
    const terms: string[] = [];
    for (const dept of profile.departments ?? []) {
      if (dept.trim().length >= 3) terms.push(dept.trim());
    }
    for (const code of profile.qualification_codes ?? []) {
      if (code.trim().length >= 3) terms.push(code.trim());
    }
    for (const [k, val] of Object.entries(profile.scores ?? {})) {
      if (typeof val === 'number' && val > 0) {
        terms.push(k);
      }
    }
    return Array.from(new Set(terms));
  }, [profile]);

  const highlightedRawText = useMemo(() => {
    const text = detail?.raw_text ?? '';
    if (!text) return { nodes: null as React.ReactNode, searchMatchCount: 0, profileMatchCount: 0 };

    const cleanSearch = drawerSearch.trim();
    const allTerms: { term: string; kind: 'search' | 'profile' }[] = [];
    if (cleanSearch.length >= 2) {
      allTerms.push({ term: cleanSearch, kind: 'search' });
    }
    for (const pt of profileTerms) {
      allTerms.push({ term: pt, kind: 'profile' });
    }

    if (allTerms.length === 0) {
      return { nodes: text, searchMatchCount: 0, profileMatchCount: 0 };
    }

    // Sort longest first so specific terms match before shorter tokens
    allTerms.sort((a, b) => b.term.length - a.term.length);
    const combinedPattern = allTerms.map((t) => toTurkishPattern(t.term)).join('|');
    const regex = new RegExp(`(${combinedPattern})`, 'gi');

    const searchRegex =
      cleanSearch.length >= 2 ? new RegExp(`^${toTurkishPattern(cleanSearch)}$`, 'i') : null;

    const parts = text.split(regex);
    let searchMatchCount = 0;
    let profileMatchCount = 0;

    const nodes = parts.map((part, idx) => {
      if (!part) return null;
      if (idx % 2 === 1) {
        const isSearchHit = searchRegex ? searchRegex.test(part) : false;
        if (isSearchHit) {
          searchMatchCount += 1;
          return (
            <mark
              key={idx}
              className="px-0.5 rounded bg-amber-300 dark:bg-amber-500/80 text-slate-950 font-semibold"
            >
              {part}
            </mark>
          );
        }
        profileMatchCount += 1;
        return (
          <mark
            key={idx}
            data-profile-match="true"
            className="px-0.5 rounded bg-emerald-200 dark:bg-emerald-700/70 text-emerald-950 dark:text-emerald-100 font-semibold"
          >
            {part}
          </mark>
        );
      }
      return part;
    });

    return { nodes, searchMatchCount, profileMatchCount };
  }, [detail?.raw_text, drawerSearch, profileTerms]);

  if (announcementId === null) return null;

  const handleSaveUserState = async () => {
    if (!detail) return;
    setSavingState(true);
    setSavedFeedback(false);
    try {
      await onUpdateState(detail.id, selectedStatus, notes);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              user_state: { status: selectedStatus, notes },
            }
          : prev
      );
      setSavedFeedback(true);
      setTimeout(() => setSavedFeedback(false), 2500);
    } finally {
      setSavingState(false);
    }
  };

  const handleStatusQuickSelect = async (nextStatus: UserAnnouncementStatus) => {
    setSelectedStatus(nextStatus);
    if (!detail) return;
    setSavingState(true);
    try {
      await onUpdateState(detail.id, nextStatus, notes);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              user_state: { status: nextStatus, notes },
            }
          : prev
      );
      setSavedFeedback(true);
      setTimeout(() => setSavedFeedback(false), 2000);
    } finally {
      setSavingState(false);
    }
  };

  const handleCopyRawText = async () => {
    if (!detail?.raw_text) return;
    try {
      await navigator.clipboard.writeText(detail.raw_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    } catch {
      // clipboard unavailable
    }
  };

  const handleJumpToProfileMatch = () => {
    const container = rawTextBoxRef.current;
    if (!container) return;
    const firstMark = container.querySelector('[data-profile-match="true"]');
    if (firstMark) {
      firstMark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/55 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative z-10 w-full max-w-3xl bg-white dark:bg-slate-900 h-full shadow-2xl border-l border-slate-200 dark:border-slate-800 flex flex-col">
        {/* Sticky Header */}
        <div className="px-5 sm:px-6 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 flex items-center justify-between gap-4 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            {detail && (
              <span
                className={`px-3 py-1 rounded-full text-xs font-bold shrink-0 ${
                  detail.match.match_status === 'eligible'
                    ? 'bg-emerald-600 text-white'
                    : detail.match.match_status === 'review'
                    ? 'bg-amber-500 text-white'
                    : 'bg-slate-500 text-white'
                }`}
              >
                %{detail.match.match_score} Uyum •{' '}
                {detail.match.match_status === 'eligible'
                  ? 'Tam Uygun'
                  : detail.match.match_status === 'review'
                  ? 'İnceleme Gerekli'
                  : 'Uygun Değil'}
              </span>
            )}
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 truncate">
              İlan #{announcementId}
            </span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/70 dark:hover:bg-slate-800 transition-colors"
            aria-label="Detayı kapat"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5">
          {loading && (
            <div className="py-20 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-emerald-600" />
              <p className="text-sm font-medium">İlan detayları ve tam metin yükleniyor...</p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
              {error}
            </div>
          )}

          {detail && !loading && (
            <>
              {/* Title & Institution */}
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                  <Building2 className="w-4 h-4 shrink-0" />
                  <span>{detail.institution || 'Kamu Kurumu'}</span>
                </div>
                <h2 className="text-lg sm:text-2xl font-extrabold text-slate-900 dark:text-slate-100 leading-snug">
                  {detail.title}
                </h2>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-medium">
                    {CATEGORY_LABELS[detail.category] ?? detail.category}
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-medium">
                    <MapPin className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                    {detail.city ||
                      (detail.cities.length > 0 ? detail.cities.join(', ') : 'Belirtilmemiş')}
                  </span>
                  {detail.quota_count !== null && detail.quota_count > 0 && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-semibold border border-emerald-200 dark:border-emerald-800">
                      <Users className="w-3.5 h-3.5" />
                      {detail.quota_count} Kontenjan
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 font-medium border border-amber-200 dark:border-amber-800">
                    <CalendarClock className="w-3.5 h-3.5" />
                    Son Başvuru:{' '}
                    {detail.deadline_date
                      ? formatTurkishDate(detail.deadline_date)
                      : 'Metinde kontrol edin'}
                    {detail.days_remaining !== null && detail.days_remaining >= 0 && (
                      <strong className="ml-1">({detail.days_remaining} gün)</strong>
                    )}
                  </span>
                  {detail.extracted.application_channel && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-semibold border border-blue-200 dark:border-blue-800">
                      <Send className="w-3.5 h-3.5" />
                      {detail.extracted.application_channel}
                    </span>
                  )}
                </div>
              </div>

              {/* Compact 2-Column Criterion-by-criterion Match Report */}
              <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 p-4 space-y-2.5 shadow-sm">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
                    Kriter Bazlı Uygunluk Raporu
                  </h3>
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                    Güven: %{Math.round((detail.extracted.confidence ?? 0) * 100)}
                  </span>
                </div>
                <p className="text-xs sm:text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {detail.match.headline}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {detail.match.reasons.map((reason, idx) => (
                    <div
                      key={idx}
                      className={`p-2.5 rounded-xl border flex items-start gap-2 text-xs ${getReasonRowClass(
                        reason.status
                      )}`}
                    >
                      {getReasonIcon(reason.status)}
                      <div className="min-w-0">
                        <div className="font-bold text-[11px] uppercase tracking-wide opacity-80">
                          {reason.label}
                        </div>
                        <div className="mt-0.5 leading-snug">{reason.message}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Official Source Links & PDFs */}
              {(() => {
                const { uniqueSources, primaryPdfUrl } = deduplicateAnnouncementLinks(
                  detail.sources
                );
                return (
                  <section className="flex flex-wrap items-center gap-2">
                    {uniqueSources.map((src, idx) => (
                      <a
                        key={`${src.source_name}-${idx}`}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
                      >
                        <span>{src.source_label} İlanına Git</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    ))}
                    {primaryPdfUrl && (
                      <a
                        href={primaryPdfUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition-colors"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Resmi PDF Aç</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </section>
                );
              })()}

              {/* Extracted Details Summary */}
              <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 p-4 space-y-2.5">
                <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
                  Çıkarılan İlan Özeti & Şartlar
                </h3>
                {detail.summary && (
                  <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {detail.summary}
                  </p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs pt-1">
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 block">
                      KPSS Türü / Taban Puan
                    </span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {detail.extracted.requires_kpss === false
                        ? 'KPSS Şartı Yok'
                        : detail.extracted.kpss_types.length > 0
                        ? `${detail.extracted.kpss_types.join(', ')}${
                            detail.extracted.min_score !== null
                              ? ` (En az ${detail.extracted.min_score})`
                              : ''
                          }`
                        : detail.extracted.min_score !== null
                        ? `En az ${detail.extracted.min_score} puan`
                        : 'Belirtilmemiş / Kılavuzda'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 block">Eğitim Düzeyi</span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {detail.extracted.education_levels.length > 0
                        ? detail.extracted.education_levels
                            .map((e) => EDUCATION_LABELS[e] ?? e)
                            .join(', ')
                        : 'Metinde kontrol edin'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 block">
                      Bölüm / Nitelik Kodları
                    </span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {detail.extracted.qualification_codes.length > 0
                        ? `Kodlar: ${detail.extracted.qualification_codes.join(', ')}`
                        : detail.extracted.departments.length > 0
                        ? detail.extracted.departments.join(', ')
                        : detail.extracted.accepts_any_department
                        ? 'Herhangi bir bölüm kabul ediliyor'
                        : 'Detay metinde'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-500 dark:text-slate-400 block">
                      Yaş Şartı & Yayın Tarihi
                    </span>
                    <span className="font-semibold text-slate-900 dark:text-slate-100 mt-0.5 block">
                      {detail.extracted.max_age !== null
                        ? `Üst yaş: ${detail.extracted.max_age}`
                        : 'Yaş sınırı yok/belirsiz'}{' '}
                      • Yayın: {formatTurkishDate(detail.publish_date)}
                    </span>
                  </div>
                </div>
              </section>

              {/* Full Original Raw Text with Personal Highlighting & In-Drawer Search */}
              <section className="space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-xs font-bold text-slate-900 dark:text-slate-100 uppercase tracking-wide">
                    Orijinal İlan Tam Metni
                  </h3>

                  <div className="flex flex-wrap items-center gap-2">
                    {highlightedRawText.profileMatchCount > 0 && (
                      <button
                        type="button"
                        onClick={handleJumpToProfileMatch}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 transition-colors"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>
                          Profilimle Eşleşenlere Atla ({highlightedRawText.profileMatchCount})
                        </span>
                      </button>
                    )}

                    {detail.raw_text && (
                      <button
                        type="button"
                        onClick={handleCopyRawText}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition-colors"
                      >
                        {copiedText ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Kopyalandı</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Kopyala</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {detail.raw_text && (
                  <div className="flex items-center gap-2">
                    <div className="relative flex-1">
                      <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <input
                        type="text"
                        value={drawerSearch}
                        onChange={(e) => setDrawerSearch(e.target.value)}
                        placeholder="Metinde ara (örn. KPSS, puan, bölüm, belge)..."
                        className="w-full h-9 pl-8 pr-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none"
                      />
                      {drawerSearch && (
                        <button
                          type="button"
                          onClick={() => setDrawerSearch('')}
                          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                          aria-label="Metin aramasını temizle"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                    {drawerSearch.trim().length >= 2 && (
                      <span className="px-2.5 py-1 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-300 text-xs font-bold shrink-0">
                        {highlightedRawText.searchMatchCount} eşleşme
                      </span>
                    )}
                  </div>
                )}

                <div
                  ref={rawTextBoxRef}
                  className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/60 p-4 sm:p-5 text-xs sm:text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed font-normal max-h-[420px] overflow-y-auto"
                >
                  {detail.raw_text
                    ? highlightedRawText.nodes
                    : 'Bu ilan için tam metin henüz çıkarılamadı. Yukarıdaki resmi kaynak veya PDF bağlantısından ilan metnini inceleyebilirsiniz.'}
                </div>
              </section>
            </>
          )}
        </div>

        {/* Sticky Footer Action Bar */}
        {detail && !loading && (
          <div className="shrink-0 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 sm:px-6 py-3 space-y-2.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="grid grid-cols-4 gap-1.5 flex-1 min-w-[240px]">
                {USER_STATUS_OPTIONS.map((opt) => {
                  const active = selectedStatus === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      disabled={savingState}
                      onClick={() => handleStatusQuickSelect(opt.value)}
                      className={`px-2 py-1.5 rounded-xl text-[11px] sm:text-xs font-semibold border transition-all text-center ${
                        active
                          ? opt.activeClass
                          : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      {opt.label}
                    </button>
                  );
                })}
              </div>

              {savedFeedback && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  <Check className="w-3.5 h-3.5" />
                  Kaydedildi
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void handleSaveUserState();
                  }
                }}
                placeholder="Kişisel başvuru notu ekleyin (örn. evraklar hazır)..."
                className="flex-1 h-9 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={handleSaveUserState}
                disabled={savingState}
                className="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-colors disabled:opacity-60 shrink-0"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Notu Kaydet</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
