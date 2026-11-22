import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Bookmark,
  CheckCircle2,
  EyeOff,
  CalendarPlus,
  Loader2,
  Clock,
  Radar,
  ClipboardCheck,
  ChevronDown,
  ChevronUp,
  CheckSquare,
  Square,
} from 'lucide-react';
import { getAnnouncements, getExportIcsUrl } from '../api';
import type { AnnouncementItem, StatsResponse, UserAnnouncementStatus } from '../types';
import { AnnouncementCard } from './AnnouncementCard';

interface SavedApplicationsPageProps {
  stats: StatsResponse | null;
  viewedIds: Set<number>;
  onGoToRadar: () => void;
  onSelectAnnouncement: (id: number) => void;
  onUpdateState: (id: number, status: UserAnnouncementStatus, notes: string) => Promise<void>;
  refreshKey: number;
}

type SavedSubTab = 'saved' | 'applied' | 'dismissed';

const DOC_CHECKLIST_ITEMS = [
  'e-Devlet Mezuniyet Belgesi',
  'KPSS Sonuç Belgesi',
  'SGK Hizmet Dökümü',
  'Adli Sicil Kaydı',
  'Vesikalık / Ehliyet',
];

function getChecklistStorageKey(id: number) {
  return `kpss_radar_doc_checklist_${id}`;
}

function loadChecklistForId(id: number): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(getChecklistStorageKey(id));
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

const DocumentChecklistPanel: React.FC<{ announcementId: number }> = ({ announcementId }) => {
  const [expanded, setExpanded] = useState(false);
  const [checks, setChecks] = useState<Record<string, boolean>>(() =>
    loadChecklistForId(announcementId)
  );

  const completedCount = DOC_CHECKLIST_ITEMS.filter((doc) => checks[doc]).length;

  const toggleDoc = (doc: string) => {
    setChecks((prev) => {
      const next = { ...prev, [doc]: !prev[doc] };
      try {
        localStorage.setItem(getChecklistStorageKey(announcementId), JSON.stringify(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  return (
    <div className="ml-2 sm:ml-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((p) => !p)}
        className="w-full px-3.5 py-2 flex items-center justify-between gap-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors"
      >
        <span className="inline-flex items-center gap-1.5">
          <ClipboardCheck className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
          <span>Evrak Hazırlık Kontrol Listesi</span>
          <span
            className={`px-1.5 py-0.5 rounded-md text-[10px] font-bold ${
              completedCount === DOC_CHECKLIST_ITEMS.length
                ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'
            }`}
          >
            {completedCount}/{DOC_CHECKLIST_ITEMS.length}
          </span>
        </span>
        {expanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        )}
      </button>

      {expanded && (
        <div className="px-3.5 pb-3 pt-1 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2">
          {DOC_CHECKLIST_ITEMS.map((doc) => {
            const done = Boolean(checks[doc]);
            return (
              <button
                key={doc}
                type="button"
                onClick={() => toggleDoc(doc)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                  done
                    ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800 line-through'
                    : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                }`}
              >
                {done ? (
                  <CheckSquare className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                ) : (
                  <Square className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                )}
                <span>{doc}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const SavedApplicationsPage: React.FC<SavedApplicationsPageProps> = ({
  stats,
  viewedIds,
  onGoToRadar,
  onSelectAnnouncement,
  onUpdateState,
  refreshKey,
}) => {
  const [subTab, setSubTab] = useState<SavedSubTab>('saved');
  const [items, setItems] = useState<AnnouncementItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getAnnouncements({
        match_status: 'all',
        user_status: subTab,
        sort: 'deadline',
        page: 1,
        page_size: 100,
      });
      setItems(res.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kayıtlı ilanlar yüklenemedi.');
    } finally {
      setLoading(false);
    }
  }, [subTab]);

  useEffect(() => {
    void loadList();
  }, [loadList, refreshKey]);

  const handleStateChange = async (
    id: number,
    status: UserAnnouncementStatus,
    notes: string
  ) => {
    await onUpdateState(id, status, notes);
    await loadList();
  };

  const deadlineGroups = useMemo(() => {
    let urgent = 0;
    let thisWeek = 0;
    let laterOrUnknown = 0;
    for (const item of items) {
      if (item.days_remaining !== null && item.days_remaining >= 0 && item.days_remaining <= 5) {
        urgent += 1;
      } else if (
        item.days_remaining !== null &&
        item.days_remaining > 5 &&
        item.days_remaining <= 10
      ) {
        thisWeek += 1;
      } else {
        laterOrUnknown += 1;
      }
    }
    return { urgent, thisWeek, laterOrUnknown };
  }, [items]);

  const canExportIcs = (stats?.saved_count ?? 0) + (stats?.eligible_count ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
            Kayıtlar & Başvuru Takip Panosu
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Başvurmayı planladığınız veya başvurduğunuz ilanları takip edin, evrak hazırlığını
            işaretleyin ve son tarihleri takviminize aktarın.
          </p>
        </div>

        <div className="flex flex-col items-start sm:items-end gap-1 shrink-0">
          {canExportIcs ? (
            <a
              href={getExportIcsUrl()}
              download="kpss-radar-takvim.ics"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold shadow-sm transition-colors"
            >
              <CalendarPlus className="w-4 h-4" />
              <span>Takvime Aktar (.ics)</span>
            </a>
          ) : (
            <button
              type="button"
              disabled
              title="Takvime aktarmak için önce en az bir ilan kaydedin veya profilinizi eşleştirin"
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 text-sm font-bold cursor-not-allowed"
            >
              <CalendarPlus className="w-4 h-4" />
              <span>Takvime Aktar (.ics)</span>
            </button>
          )}
          {!canExportIcs && (
            <span className="text-[11px] text-slate-500 dark:text-slate-400">
              Önce kayıtlı veya uygun bir ilan bulunmalıdır
            </span>
          )}
        </div>
      </div>

      {/* Sub-tabs with live counts */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-3">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSubTab('saved')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              subTab === 'saved'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <Bookmark className="w-4 h-4" />
            <span>Başvuracağım / Kayıtlı</span>
            <span
              className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                subTab === 'saved'
                  ? 'bg-white/20 text-white'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
              }`}
            >
              {stats?.saved_count ?? (subTab === 'saved' ? items.length : 0)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setSubTab('applied')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              subTab === 'applied'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Başvurduklarım</span>
            <span
              className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                subTab === 'applied'
                  ? 'bg-white/20 text-white'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
              }`}
            >
              {stats?.applied_count ?? (subTab === 'applied' ? items.length : 0)}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setSubTab('dismissed')}
            className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all ${
              subTab === 'dismissed'
                ? 'bg-slate-800 dark:bg-slate-600 text-white shadow-sm'
                : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <EyeOff className="w-4 h-4" />
            <span>Gizlediklerim</span>
            <span
              className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold ${
                subTab === 'dismissed'
                  ? 'bg-white/20 text-white'
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200'
              }`}
            >
              {stats?.dismissed_count ?? (subTab === 'dismissed' ? items.length : 0)}
            </span>
          </button>
        </div>

        {/* Deadline grouping summary on saved tab */}
        {subTab === 'saved' && items.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {deadlineGroups.urgent > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 font-bold">
                <Clock className="w-3.5 h-3.5" />
                Acil (≤5 gün): {deadlineGroups.urgent}
              </span>
            )}
            {deadlineGroups.thisWeek > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-semibold">
                Yaklaşan (6–10 gün): {deadlineGroups.thisWeek}
              </span>
            )}
            {deadlineGroups.laterOrUnknown > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-medium">
                İleri / Belirsiz: {deadlineGroups.laterOrUnknown}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      {loading && (
        <div className="py-16 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400 gap-2">
          <Loader2 className="w-7 h-7 animate-spin text-indigo-600" />
          <span className="text-sm font-medium">İlanlar yükleniyor...</span>
        </div>
      )}

      {error && !loading && (
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 p-10 text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto">
            {subTab === 'saved' ? (
              <Bookmark className="w-6 h-6" />
            ) : subTab === 'applied' ? (
              <CheckCircle2 className="w-6 h-6" />
            ) : (
              <EyeOff className="w-6 h-6" />
            )}
          </div>
          <p className="text-base font-bold text-slate-800 dark:text-slate-100">
            {subTab === 'saved'
              ? 'Henüz kaydettiğiniz bir ilan yok'
              : subTab === 'applied'
              ? 'Henüz başvurduğunuz olarak işaretlenmiş ilan yok'
              : 'Gizlenen ilan bulunmuyor'}
          </p>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            İlan Radarı ekranından uygun ilanları inceleyip Kaydet veya Başvurdum butonlarıyla
            buraya ekleyebilirsiniz.
          </p>
          <div className="pt-1">
            <button
              type="button"
              onClick={onGoToRadar}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs sm:text-sm font-bold transition-colors"
            >
              <Radar className="w-4 h-4" />
              <span>İlan Radarına Git</span>
            </button>
          </div>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="space-y-1.5">
              <AnnouncementCard
                item={item}
                onSelect={onSelectAnnouncement}
                onUpdateState={handleStateChange}
                isViewed={viewedIds.has(item.id)}
              />
              {item.user_state?.notes && (
                <div className="ml-2 sm:ml-4 px-3.5 py-2 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/70 text-xs text-indigo-950 dark:text-indigo-200">
                  <strong>Kişisel Notunuz:</strong> {item.user_state.notes}
                </div>
              )}
              {subTab === 'saved' && <DocumentChecklistPanel announcementId={item.id} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
