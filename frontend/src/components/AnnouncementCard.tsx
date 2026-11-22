import React from 'react';
import {
  Bookmark,
  CheckCircle2,
  EyeOff,
  ExternalLink,
  FileText,
  MapPin,
  Users,
  CalendarClock,
  Building2,
  AlertTriangle,
  XCircle,
  ChevronRight,
  Send,
  Check,
} from 'lucide-react';
import type { AnnouncementItem, UserAnnouncementStatus } from '../types';
import {
  CATEGORY_LABELS,
  EDUCATION_LABELS,
  deduplicateAnnouncementLinks,
  formatTurkishDate,
} from '../constants';

interface AnnouncementCardProps {
  item: AnnouncementItem;
  onSelect: (id: number) => void;
  onUpdateState: (id: number, status: UserAnnouncementStatus, notes: string) => Promise<void>;
  showIneligibleReasons?: boolean;
  compact?: boolean;
  isViewed?: boolean;
}

function getDeadlineBadge(daysRemaining: number | null, deadlineDate: string | null) {
  if (daysRemaining === null) {
    return {
      text: deadlineDate ? formatTurkishDate(deadlineDate) : 'Tarih detayda',
      className:
        'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700',
      urgent: false,
    };
  }
  if (daysRemaining < 0) {
    return {
      text: 'Süresi doldu',
      className:
        'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700',
      urgent: false,
    };
  }
  if (daysRemaining === 0) {
    return {
      text: 'BUGÜN SON GÜN!',
      className: 'bg-red-600 text-white border-red-700 animate-pulse',
      urgent: true,
    };
  }
  if (daysRemaining <= 3) {
    return {
      text: `Son ${daysRemaining} gün!`,
      className:
        'bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border-red-300 dark:border-red-800 font-bold',
      urgent: true,
    };
  }
  if (daysRemaining <= 5) {
    return {
      text: `${daysRemaining} gün kaldı`,
      className:
        'bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800 font-semibold',
      urgent: true,
    };
  }
  return {
    text: `${daysRemaining} gün kaldı`,
    className:
      'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    urgent: false,
  };
}

export const AnnouncementCard: React.FC<AnnouncementCardProps> = ({
  item,
  onSelect,
  onUpdateState,
  showIneligibleReasons = false,
  compact = false,
  isViewed = false,
}) => {
  const { match, extracted, user_state } = item;

  const statusConfig =
    match.match_status === 'eligible'
      ? {
          label: 'Tam Uygun',
          borderClass: 'border-l-4 border-l-emerald-500',
          badgeClass:
            'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
          scoreBg: 'bg-emerald-600 text-white',
          headlineBg:
            'bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-900 dark:text-emerald-200 border-emerald-200/70 dark:border-emerald-800/60',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />,
        }
      : match.match_status === 'review'
      ? {
          label: 'İnceleme Gerekli',
          borderClass: 'border-l-4 border-l-amber-500',
          badgeClass:
            'bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800',
          scoreBg: 'bg-amber-500 text-white',
          headlineBg:
            'bg-amber-50/70 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 border-amber-200/70 dark:border-amber-800/60',
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />,
        }
      : {
          label: 'Uygun Değil',
          borderClass: 'border-l-4 border-l-slate-300 dark:border-l-slate-700',
          badgeClass:
            'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700',
          scoreBg: 'bg-slate-400 dark:bg-slate-600 text-white',
          headlineBg:
            'bg-slate-50 dark:bg-slate-800/70 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
          icon: <XCircle className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400 shrink-0" />,
        };

  const deadlineInfo = getDeadlineBadge(item.days_remaining, item.deadline_date);
  const categoryLabel = CATEGORY_LABELS[item.category] ?? item.category;
  const cityText =
    item.city || (item.cities && item.cities.length > 0 ? item.cities.join(', ') : 'Belirtilmemiş');

  // Collect extracted criteria chips
  const chips: { label: string; tone: string }[] = [];
  if (extracted.requires_kpss === false) {
    chips.push({
      label: "KPSS'siz",
      tone: 'bg-sky-50 dark:bg-sky-950/50 text-sky-700 dark:text-sky-300 border-sky-200 dark:border-sky-800',
    });
  } else if (extracted.kpss_types.length > 0) {
    const scoreReasonText = match.reasons
      .filter((r) => r.field === 'kpss_score')
      .map((r) => r.message)
      .join(' ');
    const commonOrder = ['P3', 'P93', 'P94', 'P1', 'P2', 'P10', 'P121', 'EKPSS'];
    const prioritizedTypes = [...extracted.kpss_types].sort((a, b) => {
      const aMatched = new RegExp(`\\b${a}\\b`).test(scoreReasonText) ? 0 : 1;
      const bMatched = new RegExp(`\\b${b}\\b`).test(scoreReasonText) ? 0 : 1;
      if (aMatched !== bMatched) return aMatched - bMatched;
      const aCommon = commonOrder.indexOf(a);
      const bCommon = commonOrder.indexOf(b);
      const aRank = aCommon === -1 ? 99 : aCommon;
      const bRank = bCommon === -1 ? 99 : bCommon;
      return aRank - bRank;
    });
    const shownTypes = prioritizedTypes.slice(0, 3);
    const remainingCount = prioritizedTypes.length - shownTypes.length;
    const typeStr = shownTypes.join('/') + (remainingCount > 0 ? ` +${remainingCount}` : '');
    const scoreStr = extracted.min_score !== null ? ` ≥ ${extracted.min_score}` : '';
    chips.push({
      label: `KPSS ${typeStr}${scoreStr}`,
      tone: 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
    });
  } else if (extracted.min_score !== null) {
    chips.push({
      label: `KPSS ≥ ${extracted.min_score}`,
      tone: 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
    });
  }

  if (extracted.education_levels && extracted.education_levels.length > 0) {
    const eduText = extracted.education_levels
      .slice(0, 3)
      .map((e) => EDUCATION_LABELS[e] ?? e)
      .join(' / ');
    chips.push({
      label: eduText,
      tone: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    });
  }

  if (extracted.max_age !== null) {
    chips.push({
      label: `Max ${extracted.max_age} Yaş`,
      tone: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700',
    });
  }

  if (extracted.qualification_codes && extracted.qualification_codes.length > 0) {
    chips.push({
      label: `Kod: ${extracted.qualification_codes.slice(0, 3).join(', ')}`,
      tone: 'bg-violet-50 dark:bg-violet-950/50 text-violet-700 dark:text-violet-300 border-violet-200 dark:border-violet-800',
    });
  } else if (extracted.accepts_any_department) {
    chips.push({
      label: 'Herhangi Bir Bölüm',
      tone: 'bg-teal-50 dark:bg-teal-950/50 text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-800',
    });
  }

  const { uniqueSources, primaryPdfUrl } = deduplicateAnnouncementLinks(item.sources);
  const failReasons = match.reasons.filter((r) => r.status === 'fail');

  const handleActionClick = (e: React.MouseEvent, nextStatus: UserAnnouncementStatus) => {
    e.stopPropagation();
    const targetStatus = user_state.status === nextStatus ? 'none' : nextStatus;
    void onUpdateState(item.id, targetStatus, user_state.notes ?? '');
  };

  if (compact) {
    return (
      <article
        onClick={() => onSelect(item.id)}
        className={`group bg-white dark:bg-slate-900 rounded-xl border border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer px-3.5 py-2.5 ${statusConfig.borderClass}`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div
              className={`w-11 h-9 rounded-lg flex items-center justify-center text-xs font-extrabold shrink-0 ${statusConfig.scoreBg}`}
              title={`Uygunluk Skoru: %${match.match_score} (${statusConfig.label})`}
            >
              %{match.match_score}
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                <span className="truncate max-w-[200px] sm:max-w-[260px]">
                  {item.institution || 'Kamu Kurumu'}
                </span>
                <span>•</span>
                <span className="truncate">{cityText}</span>
                {item.is_new && (
                  <span className="px-1.5 py-0.2 rounded bg-sky-600 text-white text-[10px] font-bold uppercase">
                    Yeni
                  </span>
                )}
                {isViewed && (
                  <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-emerald-700 dark:text-emerald-400">
                    <Check className="w-3 h-3" />
                    İncelendi
                  </span>
                )}
              </div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-700 dark:group-hover:text-indigo-400 truncate mt-0.5">
                {item.title}
              </h3>
            </div>
          </div>

          <div
            className="flex flex-wrap items-center gap-1.5 shrink-0 justify-between sm:justify-end"
            onClick={(e) => e.stopPropagation()}
          >
            {chips.slice(0, 2).map((chip, idx) => (
              <span
                key={idx}
                className={`hidden md:inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium border ${chip.tone}`}
              >
                {chip.label}
              </span>
            ))}

            <span
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] border ${deadlineInfo.className}`}
            >
              <CalendarClock className="w-3 h-3 shrink-0" />
              <span>{deadlineInfo.text}</span>
            </span>

            <button
              type="button"
              onClick={(e) => handleActionClick(e, 'saved')}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold border transition-colors ${
                user_state.status === 'saved'
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
              }`}
              title="İlanı kaydet"
            >
              <Bookmark className="w-3 h-3" />
              <span className="hidden sm:inline">
                {user_state.status === 'saved' ? 'Kayıtlı' : 'Kaydet'}
              </span>
            </button>

            <button
              type="button"
              onClick={() => onSelect(item.id)}
              className="inline-flex items-center gap-0.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white"
            >
              <span>Detay</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article
      onClick={() => onSelect(item.id)}
      className={`group bg-white dark:bg-slate-900 rounded-2xl border border-slate-200/90 dark:border-slate-800 shadow-sm hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer p-4 sm:p-5 ${statusConfig.borderClass}`}
    >
      <div className="flex flex-col md:flex-row gap-4">
        {/* Left Score Column */}
        <div className="flex md:flex-col items-center md:items-center justify-between md:justify-start gap-2 md:w-20 shrink-0">
          <div
            className={`w-14 h-14 rounded-2xl flex flex-col items-center justify-center shadow-sm ${statusConfig.scoreBg}`}
            title={`Uygunluk Skoru: %${match.match_score}`}
          >
            <span className="text-lg font-extrabold leading-none">%{match.match_score}</span>
            <span className="text-[10px] font-medium opacity-90 mt-0.5">Uyum</span>
          </div>

          <div className="flex md:flex-col items-center gap-1.5">
            {item.is_new && (
              <span className="px-2 py-0.5 rounded-full bg-sky-600 text-white text-[10px] font-bold tracking-wide uppercase">
                Yeni
              </span>
            )}
            {isViewed && (
              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-semibold border border-slate-200 dark:border-slate-700">
                <Check className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" />
                İncelendi
              </span>
            )}
            <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500 text-center">
              {item.publish_date ? formatTurkishDate(item.publish_date) : ''}
            </span>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-2.5">
          {/* Top Meta Row */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${statusConfig.badgeClass}`}
              >
                {statusConfig.icon}
                <span>{statusConfig.label}</span>
              </span>

              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                {categoryLabel}
              </span>

              {extracted.application_channel && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                  <Send className="w-3 h-3" />
                  {extracted.application_channel}
                </span>
              )}
            </div>

            {/* Deadline Countdown Pill */}
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border ${deadlineInfo.className}`}
              title={
                item.deadline_date
                  ? `Son Başvuru: ${formatTurkishDate(item.deadline_date)}`
                  : 'Son başvuru tarihi ilan metninde'
              }
            >
              <CalendarClock className="w-3.5 h-3.5 shrink-0" />
              <span>{deadlineInfo.text}</span>
              {item.deadline_date && item.days_remaining !== null && (
                <span className="hidden sm:inline opacity-75 font-normal">
                  ({formatTurkishDate(item.deadline_date)})
                </span>
              )}
            </div>
          </div>

          {/* Institution & Title */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              <Building2 className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="truncate">{item.institution || 'Kamu Kurumu'}</span>
            </div>
            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-indigo-700 dark:group-hover:text-indigo-400 transition-colors mt-0.5 leading-snug">
              {item.title}
            </h3>
          </div>

          {/* City & Quota Row */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-300">
            <span className="inline-flex items-center gap-1 font-medium">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              {cityText}
            </span>
            {item.quota_count !== null && item.quota_count > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 font-semibold border border-emerald-200/70 dark:border-emerald-800">
                <Users className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                {item.quota_count} Kişi
              </span>
            )}
          </div>

          {/* Extracted Criteria Chips */}
          {chips.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              {chips.map((chip, idx) => (
                <span
                  key={idx}
                  className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium border ${chip.tone}`}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          )}

          {/* Match Headline */}
          {match.headline && (
            <div
              className={`px-3 py-2 rounded-xl border text-xs font-medium flex items-start gap-2 ${statusConfig.headlineBg}`}
            >
              {statusConfig.icon}
              <span>{match.headline}</span>
            </div>
          )}

          {/* Explicit Ineligible Reasons if viewing Elenenler */}
          {showIneligibleReasons && failReasons.length > 0 && (
            <div className="px-3 py-2 rounded-xl bg-red-50/70 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-800 dark:text-red-300 space-y-1">
              <div className="font-semibold">Elenme Nedenleri:</div>
              {failReasons.map((r, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <XCircle className="w-3.5 h-3.5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
                  <span>
                    <strong>{r.label}:</strong> {r.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Bottom Row: Multi-Source Links + Quick Actions */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5">
            {/* Sources & PDF */}
            <div
              className="flex flex-wrap items-center gap-1.5"
              onClick={(e) => e.stopPropagation()}
            >
              {uniqueSources.map((src, idx) => (
                <a
                  key={`${src.source_name}-${idx}`}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium transition-colors"
                  title={`${src.source_label} kaynağında aç`}
                >
                  <span>{src.source_label}</span>
                  <ExternalLink className="w-3 h-3 text-slate-500 dark:text-slate-400" />
                </a>
              ))}
              {primaryPdfUrl && (
                <a
                  href={primaryPdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 text-xs font-semibold transition-colors"
                  title="Resmi PDF Kılavuzunu / İlanını Aç"
                >
                  <FileText className="w-3 h-3" />
                  <span>Resmi PDF</span>
                </a>
              )}
            </div>

            {/* Quick Action Buttons */}
            <div
              className="flex flex-wrap items-center gap-1.5"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={(e) => handleActionClick(e, 'saved')}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                  user_state.status === 'saved'
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                }`}
                title="İlanı kaydet"
              >
                <Bookmark className="w-3.5 h-3.5" />
                <span>{user_state.status === 'saved' ? 'Kayıtlı' : 'Kaydet'}</span>
              </button>

              <button
                type="button"
                onClick={(e) => handleActionClick(e, 'applied')}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                  user_state.status === 'applied'
                    ? 'bg-emerald-600 text-white border-emerald-600'
                    : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                }`}
                title="Başvurdum olarak işaretle"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{user_state.status === 'applied' ? 'Başvuruldu' : 'Başvurdum'}</span>
              </button>

              <button
                type="button"
                onClick={(e) => handleActionClick(e, 'dismissed')}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  user_state.status === 'dismissed'
                    ? 'bg-slate-700 text-white border-slate-700'
                    : 'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700'
                }`}
                title={user_state.status === 'dismissed' ? 'Geri al' : 'Gizle'}
              >
                <EyeOff className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">
                  {user_state.status === 'dismissed' ? 'Geri Al' : 'Gizle'}
                </span>
              </button>

              <button
                type="button"
                onClick={() => onSelect(item.id)}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white transition-colors"
              >
                <span>Detay</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
};
