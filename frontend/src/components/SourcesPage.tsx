import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Radio,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  Plus,
  Trash2,
  Bell,
  BellRing,
  Send,
  Globe,
  Loader2,
  Save,
  Building2,
  Search,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  MapPin,
  X,
  FileUp,
  FileText,
  ShieldAlert,
  CheckSquare,
  Square,
  Sparkles,
} from 'lucide-react';
import {
  createCustomSource,
  deleteCustomSource,
  getCustomSources,
  getInstitutions,
  importAnnouncementPdf,
  importAnnouncementText,
  sendTestNotification,
} from '../api';
import type {
  AnnouncementDetail,
  CustomSource,
  InstitutionItem,
  InstitutionsCatalogResponse,
  StatsResponse,
  UserProfile,
} from '../types';
import { UNIQUE_QUICK_PORTALS, formatRelativeDateTime } from '../constants';

interface SourcesPageProps {
  profile: UserProfile | null;
  stats: StatsResponse | null;
  isScanning: boolean;
  currentSource: string | null;
  onTriggerSourceScan: (sourceName: string) => Promise<void>;
  onSaveProfile: (profile: UserProfile) => Promise<void>;
  onSelectAnnouncement?: (id: number) => void;
  onAnnouncementImported?: (detail: AnnouncementDetail) => void;
}

const PROTECTED_PORTALS = [
  {
    id: 'kariyer_kapisi',
    name: 'Kariyer Kapısı',
    subtitle: 'Cumhurbaşkanlığı İKO — e-Devlet girişli başvurular',
    url: 'https://kariyerkapisi.gov.tr/isealim',
  },
  {
    id: 'iskur_esube',
    name: 'İŞKUR e-Şube',
    subtitle: 'Açık iş ilanları & kamu sürekli işçi / kura başvuruları',
    url: 'https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx',
  },
  {
    id: 'iskur_kurumdisi',
    name: 'İŞKUR Kurumdışı Kamu İşçi',
    subtitle: 'Belediye şirketi & il özel idaresi PDF ilanları',
    url: 'https://www.iskur.gov.tr/ilanlar/kurumdisi-kamu-isci-alim-ilanlari/',
  },
  {
    id: 'sydv_portal',
    name: 'SYDV İlan Portalı',
    subtitle: 'İl/ilçe Sosyal Yardımlaşma ve Dayanışma Vakıfları',
    url: 'https://vakifilan.aile.gov.tr/',
  },
];

const BROWSER_NOTIF_STORAGE_KEY = 'kpss_radar_browser_notif';

function getTodayDateKey(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `kpss_radar_daily_portal_checks_${y}-${m}-${d}`;
}

export const SourcesPage: React.FC<SourcesPageProps> = ({
  profile,
  stats,
  isScanning,
  currentSource,
  onTriggerSourceScan,
  onSaveProfile,
  onSelectAnnouncement,
  onAnnouncementImported,
}) => {
  // Built-in 163-institution catalog (collapsed by default for compact layout)
  const [catalog, setCatalog] = useState<InstitutionsCatalogResponse | null>(null);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [networkExpanded, setNetworkExpanded] = useState(false);
  const [selectedGroupKey, setSelectedGroupKey] = useState<string>('all');
  const [instSearch, setInstSearch] = useState('');

  // Daily 1-click portal checks (persisted per local day)
  const [dailyCheckedPortals, setDailyCheckedPortals] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(getTodayDateKey());
      return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
    } catch {
      return {};
    }
  });

  // Smart PDF / Text Announcement Import
  const [importMode, setImportMode] = useState<'pdf' | 'text'>('pdf');
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [importTitle, setImportTitle] = useState('');
  const [importInstitution, setImportInstitution] = useState('');
  const [importUrl, setImportUrl] = useState('');
  const [importRawText, setImportRawText] = useState('');
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importedResult, setImportedResult] = useState<AnnouncementDetail | null>(null);

  // Optional custom URL watcher
  const [customSources, setCustomSources] = useState<CustomSource[]>([]);
  const [loadingCustom, setLoadingCustom] = useState(true);
  const [customExpanded, setCustomExpanded] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customUrl, setCustomUrl] = useState('');
  const [customKeywords, setCustomKeywords] = useState('KPSS, personel alım, ilan');
  const [addingCustom, setAddingCustom] = useState(false);
  const [customError, setCustomError] = useState<string | null>(null);

  // Notifications & scan interval
  const [scanInterval, setScanInterval] = useState<number>(profile?.scan_interval_minutes ?? 60);
  const [botToken, setBotToken] = useState(profile?.telegram_bot_token ?? '');
  const [chatId, setChatId] = useState(profile?.telegram_chat_id ?? '');
  const [webhookUrl, setWebhookUrl] = useState(profile?.webhook_url ?? '');
  const [savingNotif, setSavingNotif] = useState(false);
  const [notifSavedMsg, setNotifSavedMsg] = useState<string | null>(null);

  // Browser desktop notifications
  const [browserNotifEnabled, setBrowserNotifEnabled] = useState<boolean>(() => {
    try {
      return (
        localStorage.getItem(BROWSER_NOTIF_STORAGE_KEY) === 'true' &&
        typeof Notification !== 'undefined' &&
        Notification.permission === 'granted'
      );
    } catch {
      return false;
    }
  });
  const [browserNotifError, setBrowserNotifError] = useState<string | null>(null);

  const [testingNotif, setTestingNotif] = useState(false);
  const [testResult, setTestResult] = useState<{
    sent: boolean;
    channel: string;
    error: string | null;
  } | null>(null);

  useEffect(() => {
    if (profile) {
      setScanInterval(profile.scan_interval_minutes ?? 60);
      setBotToken(profile.telegram_bot_token ?? '');
      setChatId(profile.telegram_chat_id ?? '');
      setWebhookUrl(profile.webhook_url ?? '');
    }
  }, [profile]);

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true);
    setCatalogError(null);
    try {
      const data = await getInstitutions();
      setCatalog(data);
    } catch (err) {
      setCatalogError(err instanceof Error ? err.message : 'Kurum ağı yüklenemedi.');
    } finally {
      setLoadingCatalog(false);
    }
  }, []);

  useEffect(() => {
    void loadCatalog();
  }, [loadCatalog, stats?.last_scan_at]);

  const loadCustomSources = useCallback(async () => {
    setLoadingCustom(true);
    try {
      const list = await getCustomSources();
      setCustomSources(list);
      if (list.length > 0) {
        setCustomExpanded(true);
      }
    } catch {
      // ignore initial error if backend down
    } finally {
      setLoadingCustom(false);
    }
  }, []);

  useEffect(() => {
    void loadCustomSources();
  }, [loadCustomSources]);

  const filteredInstitutions = useMemo(() => {
    if (!catalog) return [];
    const q = instSearch.trim().toLocaleLowerCase('tr-TR');
    const items: (InstitutionItem & { group_label: string; source_name: string })[] = [];

    for (const grp of catalog.groups) {
      if (selectedGroupKey !== 'all' && grp.group_key !== selectedGroupKey) continue;
      for (const item of grp.items) {
        if (
          q &&
          !item.name.toLocaleLowerCase('tr-TR').includes(q) &&
          !item.city.toLocaleLowerCase('tr-TR').includes(q)
        ) {
          continue;
        }
        items.push({
          ...item,
          group_label: grp.group_label,
          source_name: grp.source_name,
        });
      }
    }
    return items;
  }, [catalog, selectedGroupKey, instSearch]);

  const toggleDailyPortalCheck = (portalId: string) => {
    setDailyCheckedPortals((prev) => {
      const next = { ...prev, [portalId]: !prev[portalId] };
      try {
        localStorage.setItem(getTodayDateKey(), JSON.stringify(next));
      } catch {
        // ignore storage quota
      }
      return next;
    });
  };

  const handleToggleBrowserNotif = async () => {
    setBrowserNotifError(null);
    if (typeof Notification === 'undefined') {
      setBrowserNotifError('Bu tarayıcı masaüstü bildirimlerini desteklemiyor.');
      return;
    }

    if (browserNotifEnabled) {
      setBrowserNotifEnabled(false);
      try {
        localStorage.setItem(BROWSER_NOTIF_STORAGE_KEY, 'false');
      } catch {
        // ignore
      }
      return;
    }

    let perm = Notification.permission;
    if (perm === 'default') {
      perm = await Notification.requestPermission();
    }

    if (perm === 'granted') {
      setBrowserNotifEnabled(true);
      try {
        localStorage.setItem(BROWSER_NOTIF_STORAGE_KEY, 'true');
      } catch {
        // ignore
      }
      new Notification('KPSS Radar Bildirimleri Açık', {
        body: 'Yeni tam uygun KPSS ilanı bulunduğunda masaüstü bildirimi alacaksınız.',
      });
    } else {
      setBrowserNotifEnabled(false);
      setBrowserNotifError(
        'Tarayıcı bildirim izni reddedildi. Tarayıcı adres çubuğundan izin verebilirsiniz.'
      );
    }
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setImportError(null);
    setImportedResult(null);

    if (importMode === 'pdf') {
      if (!pdfFile) {
        setImportError('Lütfen analiz etmek için bir PDF dosyası seçin.');
        return;
      }
      setImporting(true);
      try {
        const result = await importAnnouncementPdf(pdfFile, {
          title: importTitle.trim() || undefined,
          institution: importInstitution.trim() || undefined,
          url: importUrl.trim() || undefined,
        });
        setImportedResult(result);
        setPdfFile(null);
        setImportTitle('');
        setImportInstitution('');
        setImportUrl('');
        onAnnouncementImported?.(result);
      } catch (err) {
        setImportError(err instanceof Error ? err.message : 'PDF içe aktarılamadı.');
      } finally {
        setImporting(false);
      }
      return;
    }

    if (!importTitle.trim() || !importRawText.trim()) {
      setImportError('Lütfen ilan başlığı ve ilan metnini girin.');
      return;
    }

    setImporting(true);
    try {
      const result = await importAnnouncementText({
        title: importTitle.trim(),
        institution: importInstitution.trim() || 'Kamu Kurumu',
        url: importUrl.trim(),
        raw_text: importRawText.trim(),
      });
      setImportedResult(result);
      setImportTitle('');
      setImportInstitution('');
      setImportUrl('');
      setImportRawText('');
      onAnnouncementImported?.(result);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'İlan metni içe aktarılamadı.');
    } finally {
      setImporting(false);
    }
  };

  const handleAddCustomSource = async (e: React.FormEvent) => {
    e.preventDefault();
    setCustomError(null);
    if (!customName.trim() || !customUrl.trim()) {
      setCustomError('Lütfen kurum adı ve geçerli bir URL girin.');
      return;
    }

    setAddingCustom(true);
    try {
      const keywords = customKeywords
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean);
      const created = await createCustomSource({
        name: customName.trim(),
        url: customUrl.trim(),
        keywords,
      });
      setCustomSources((prev) => [created, ...prev]);
      setCustomName('');
      setCustomUrl('');
    } catch (err) {
      setCustomError(err instanceof Error ? err.message : 'Özel kaynak eklenemedi.');
    } finally {
      setAddingCustom(false);
    }
  };

  const handleDeleteCustomSource = async (id: number) => {
    try {
      await deleteCustomSource(id);
      setCustomSources((prev) => prev.filter((s) => s.id !== id));
    } catch {
      // ignore
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setSavingNotif(true);
    setNotifSavedMsg(null);
    try {
      await onSaveProfile({
        ...profile,
        scan_interval_minutes: scanInterval,
        telegram_bot_token: botToken.trim(),
        telegram_chat_id: chatId.trim(),
        webhook_url: webhookUrl.trim(),
      });
      setNotifSavedMsg('Tarama aralığı ve bildirim ayarları kaydedildi.');
      setTimeout(() => setNotifSavedMsg(null), 3500);
    } finally {
      setSavingNotif(false);
    }
  };

  const handleSendTest = async () => {
    setTestingNotif(true);
    setTestResult(null);
    try {
      const res = await sendTestNotification();
      setTestResult(res);
    } catch (err) {
      setTestResult({
        sent: false,
        channel: 'telegram/webhook',
        error: err instanceof Error ? err.message : 'Test bildirimi gönderilemedi.',
      });
    } finally {
      setTestingNotif(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
            Kaynaklar, Otomatik Tarama & Bildirimler
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            {stats?.sources?.length ?? 10} yerleşik ulusal ve kurumsal kaynak grubunu canlı izleyin,{' '}
            {catalog?.total ?? 163} resmi kurumu inceleyin ve bildirimlerinizi yönetin.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void onTriggerSourceScan('all')}
          disabled={isScanning}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-sm transition-colors disabled:opacity-60 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isScanning ? 'animate-spin' : ''}`} />
          <span>{isScanning ? 'Tarama Sürüyor...' : 'Tüm Kaynakları Şimdi Tara'}</span>
        </button>
      </div>

      {/* 1. Official Sources Live Health (10 built-in source groups) */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
            <Radio className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3>Otomatik Taranan Resmi Kaynaklar ({stats?.sources?.length ?? 10})</h3>
          </div>
          {stats?.last_scan_at && (
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Son genel tarama: {formatRelativeDateTime(stats.last_scan_at)}
            </span>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {(stats?.sources ?? []).map((src) => {
            const isThisRunning = isScanning && currentSource === src.source_name;
            const isSuccess = src.status === 'success';
            const isError = src.status === 'error';
            const isOsymEmpty =
              src.source_name === 'osym' && isSuccess && src.items_found === 0;

            return (
              <div
                key={src.source_name}
                className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm flex flex-col justify-between gap-3"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-start gap-1 text-sm font-bold text-slate-900 dark:text-slate-100 hover:text-indigo-600 dark:hover:text-indigo-400 leading-snug"
                      >
                        <span className="break-words">{src.source_label}</span>
                        <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      </a>
                      <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5 truncate">
                        {src.url}
                      </p>
                    </div>

                    {isThisRunning ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-[11px] font-bold shrink-0 whitespace-nowrap">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Taranıyor</span>
                      </span>
                    ) : isSuccess ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-[11px] font-bold shrink-0 whitespace-nowrap">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Sağlıklı</span>
                      </span>
                    ) : isError ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-red-50 dark:bg-red-950/60 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 text-[11px] font-bold shrink-0 whitespace-nowrap">
                        <XCircle className="w-3 h-3" />
                        <span>Hata</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-[11px] font-semibold shrink-0 whitespace-nowrap">
                        <Clock className="w-3 h-3" />
                        <span>Beklemede</span>
                      </span>
                    )}
                  </div>

                  {isOsymEmpty && (
                    <p className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
                      Şu an açık yeni yerleştirme kılavuzu yok
                    </p>
                  )}

                  {src.error_message && (
                    <div className="p-2 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-[11px] text-red-700 dark:text-red-300 line-clamp-2">
                      {src.error_message}
                    </div>
                  )}
                </div>

                <div className="pt-2.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 text-xs text-slate-600 dark:text-slate-400">
                    <span>
                      Bulunan:{' '}
                      <strong className="text-slate-900 dark:text-slate-100">
                        {src.items_found}
                      </strong>
                    </span>
                    <span>
                      Yeni:{' '}
                      <strong className="text-emerald-700 dark:text-emerald-400">
                        +{src.items_new}
                      </strong>
                    </span>
                  </div>

                  <button
                    type="button"
                    disabled={isScanning}
                    onClick={() => void onTriggerSourceScan(src.source_name)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white text-xs font-bold disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3 h-3 ${isThisRunning ? 'animate-spin' : ''}`} />
                    <span>Tara</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 2. Built-in Automatic Institution Network (163 Resmi Kurum — Compact summary + expandable) */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
              <Building2 className="w-5 h-5 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <h3>
                Yerleşik Otomatik Kurum Ağı ({catalog?.total ?? 163} Resmi Kurum — Ekstra Kurulum
                Gerektirmez)
              </h3>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-bold">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span>Otomatik Takip Ediliyor</span>
              </span>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Bakanlıklar, üst kurullar, KİT&apos;ler, 28 büyükşehir + 44 il belediyesi ve
              üniversite PDB&apos;leri doğrudan; 1390+ ilçe belediyesi ve 208 üniversite SBB/Resmî
              Gazete/Memurlar.net üzerinden yakalanır.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setNetworkExpanded((p) => !p)}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs sm:text-sm font-bold transition-colors shrink-0"
          >
            {networkExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                <span>Kurum Listesini Gizle</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                <span>Kurum Ağını Görüntüle / Ara ({catalog?.total ?? 163})</span>
              </>
            )}
          </button>
        </div>

        {/* Compact Group Summary Pills when collapsed */}
        {!networkExpanded && catalog && (
          <div className="flex flex-wrap gap-1.5">
            {catalog.groups.map((grp) => (
              <button
                key={grp.group_key}
                type="button"
                onClick={() => {
                  setSelectedGroupKey(grp.group_key);
                  setNetworkExpanded(true);
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium transition-colors"
              >
                {grp.group_label}
              </button>
            ))}
          </div>
        )}

        {/* Expanded Searchable Institution Grid */}
        {networkExpanded && (
          <div className="space-y-4 pt-2 border-t border-slate-100 dark:border-slate-800">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setSelectedGroupKey('all')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                    selectedGroupKey === 'all'
                      ? 'bg-slate-900 dark:bg-indigo-600 text-white shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  Tümü ({catalog?.total ?? 163})
                </button>
                {(catalog?.groups ?? []).map((grp) => {
                  const active = selectedGroupKey === grp.group_key;
                  return (
                    <button
                      key={grp.group_key}
                      type="button"
                      onClick={() => setSelectedGroupKey(grp.group_key)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                        active
                          ? 'bg-slate-900 dark:bg-indigo-600 text-white shadow-sm'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-700'
                      }`}
                    >
                      {grp.group_label}
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="relative w-full sm:w-80">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={instSearch}
                    onChange={(e) => setInstSearch(e.target.value)}
                    placeholder="Kurum veya şehir ara (örn. Ankara, SGK)..."
                    className="w-full h-9 pl-9 pr-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 focus:bg-white dark:focus:bg-slate-900 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none"
                  />
                  {instSearch && (
                    <button
                      type="button"
                      onClick={() => setInstSearch('')}
                      className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                      aria-label="Aramayı temizle"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
                  Gösterilen:{' '}
                  <strong className="text-slate-900 dark:text-slate-100">
                    {filteredInstitutions.length}
                  </strong>{' '}
                  kurum
                </span>
              </div>
            </div>

            {loadingCatalog ? (
              <div className="py-10 flex items-center justify-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                <span>Kurum ağı yükleniyor...</span>
              </div>
            ) : catalogError ? (
              <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs text-red-700 dark:text-red-300 flex items-center justify-between">
                <span>{catalogError}</span>
                <button
                  type="button"
                  onClick={() => void loadCatalog()}
                  className="px-3 py-1 rounded-lg bg-red-600 text-white font-bold"
                >
                  Tekrar Dene
                </button>
              </div>
            ) : filteredInstitutions.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
                Aramanızla eşleşen kurum bulunamadı.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-[420px] overflow-y-auto pr-1">
                {filteredInstitutions.map((inst, idx) => {
                  const isOk = inst.status === 'ok' || inst.status === 'success';
                  const isErr = inst.status === 'error';

                  return (
                    <div
                      key={`${inst.name}-${idx}`}
                      className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-white dark:hover:bg-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-colors flex items-center justify-between gap-2.5"
                    >
                      <div className="min-w-0 space-y-1">
                        <div
                          className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate"
                          title={inst.name}
                        >
                          {inst.name}
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="inline-flex items-center gap-0.5 text-[11px] text-slate-500 dark:text-slate-400">
                            <MapPin className="w-3 h-3 text-slate-400" />
                            {inst.city}
                          </span>

                          {isErr ? (
                            <span className="px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-[10px] font-semibold">
                              Erişim Uyarısı
                            </span>
                          ) : isOk ? (
                            <span className="px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-[10px] font-semibold">
                              Aktif{inst.found > 0 ? ` • ${inst.found} ilan` : ''}
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-[10px] font-semibold">
                              Otomatik İzleniyor
                            </span>
                          )}
                        </div>
                      </div>

                      <a
                        href={inst.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-indigo-400 text-slate-600 dark:text-slate-300 hover:text-indigo-700 dark:hover:text-indigo-400 transition-colors shrink-0"
                        title={`${inst.name} duyuru sayfasını aç`}
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </section>

      {/* 3. e-Devlet / WAF Korumalı Portallar — 1-Tık Günlük Kontrol & Akıllı İlan İçe Aktarma */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
            <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <h3>
              e-Devlet / WAF Korumalı Portallar — 1-Tık Günlük Kontrol & Akıllı İlan İçe Aktarma
            </h3>
          </div>
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 shrink-0">
            Bugün kontrol edilen:{' '}
            <strong className="text-emerald-700 dark:text-emerald-400">
              {PROTECTED_PORTALS.filter((p) => dailyCheckedPortals[p.id]).length}/
              {PROTECTED_PORTALS.length}
            </strong>
          </span>
        </div>

        <div className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-800/70 text-xs text-amber-950 dark:text-amber-200 leading-relaxed">
          Bu 4 portal e-Devlet/WAF korumalıdır; ilanların %95+&apos;ı Memurlar.net ve İşin Olsa
          üzerinden otomatik yakalanır. Tam kesinlik için portalları tek tıkla kontrol edip
          gördüğünüz PDF/metni aşağıdan profilinizle eşleştirebilirsiniz.
        </div>

        {/* 1-Click Daily Check Strip (single clean "Portalı Aç ↗" link per card) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {PROTECTED_PORTALS.map((portal) => {
            const isChecked = Boolean(dailyCheckedPortals[portal.id]);
            return (
              <div
                key={portal.id}
                className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-3 ${
                  isChecked
                    ? 'bg-emerald-50/60 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800'
                    : 'bg-slate-50/70 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div>
                  <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    {portal.name}
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1 leading-snug">
                    {portal.subtitle}
                  </p>
                </div>

                <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-200/70 dark:border-slate-700">
                  <a
                    href={portal.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 hover:border-indigo-400 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:text-indigo-700 dark:hover:text-indigo-400"
                  >
                    <span>Portalı Aç</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>

                  <button
                    type="button"
                    onClick={() => toggleDailyPortalCheck(portal.id)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold transition-colors ${
                      isChecked
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                    }`}
                  >
                    {isChecked ? (
                      <>
                        <CheckSquare className="w-3.5 h-3.5" />
                        <span>Kontrol Edildi ✓</span>
                      </>
                    ) : (
                      <>
                        <Square className="w-3.5 h-3.5 text-slate-400" />
                        <span>Kontrol Et</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Smart PDF / Text Announcement Import Form */}
        <div className="rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-800/40 p-4 sm:p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Akıllı PDF / Metin İlan Analiz & İçe Aktarma
              </h4>
            </div>

            <div className="inline-flex p-1 rounded-xl bg-slate-200/70 dark:bg-slate-800 self-start sm:self-auto">
              <button
                type="button"
                onClick={() => {
                  setImportMode('pdf');
                  setImportError(null);
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  importMode === 'pdf'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <FileUp className="w-3.5 h-3.5" />
                <span>PDF Yükle</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setImportMode('text');
                  setImportError(null);
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  importMode === 'text'
                    ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Metin Yapıştır</span>
              </button>
            </div>
          </div>

          <form onSubmit={handleImportSubmit} className="space-y-3">
            {importMode === 'pdf' ? (
              <div className="space-y-3">
                <label className="block rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-400 bg-white dark:bg-slate-900 p-4 text-center cursor-pointer transition-colors">
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0] ?? null;
                      setPdfFile(file);
                    }}
                  />
                  <FileUp className="w-6 h-6 text-indigo-600 dark:text-indigo-400 mx-auto mb-1.5" />
                  <div className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-100">
                    {pdfFile
                      ? `Seçili PDF: ${pdfFile.name} (${Math.round(pdfFile.size / 1024)} KB)`
                      : 'İŞKUR Kurumdışı veya resmi ilan PDF dosyasını seçmek için tıklayın'}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                    KPSS puanı, eğitim, bölüm ve son başvuru tarihi otomatik çıkarılır
                  </div>
                </label>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <input
                    type="text"
                    value={importTitle}
                    onChange={(e) => setImportTitle(e.target.value)}
                    placeholder="Başlık (opsiyonel — PDF'ten okunur)"
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    value={importInstitution}
                    onChange={(e) => setImportInstitution(e.target.value)}
                    placeholder="Kurum adı (opsiyonel)"
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                  <input
                    type="url"
                    value={importUrl}
                    onChange={(e) => setImportUrl(e.target.value)}
                    placeholder="Kaynak URL (opsiyonel)"
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-2.5">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <input
                    type="text"
                    value={importTitle}
                    onChange={(e) => setImportTitle(e.target.value)}
                    placeholder="İlan başlığı (zorunlu)..."
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                  <input
                    type="text"
                    value={importInstitution}
                    onChange={(e) => setImportInstitution(e.target.value)}
                    placeholder="Kurum adı (örn. X SYDV)"
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                  <input
                    type="url"
                    value={importUrl}
                    onChange={(e) => setImportUrl(e.target.value)}
                    placeholder="İlan URL (opsiyonel)"
                    className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <textarea
                  rows={4}
                  value={importRawText}
                  onChange={(e) => setImportRawText(e.target.value)}
                  placeholder="Kariyer Kapısı, İŞKUR e-Şube veya SYDV sayfasından kopyaladığınız ilan metnini buraya yapıştırın..."
                  className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3.5 py-2.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
                />
              </div>
            )}

            {importError && (
              <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-xs font-semibold text-red-700 dark:text-red-300">
                {importError}
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={importing}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-bold shadow-sm transition-colors disabled:opacity-60"
              >
                {importing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span>
                  {importing
                    ? 'Analiz Ediliyor...'
                    : importMode === 'pdf'
                    ? "PDF'i Analiz Et ve Radara Ekle"
                    : 'Metni Analiz Et ve Radara Ekle'}
                </span>
              </button>
            </div>
          </form>

          {/* Immediate Result Card */}
          {importedResult && (
            <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-white dark:bg-slate-900 p-4 shadow-sm space-y-2.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      importedResult.match.match_status === 'eligible'
                        ? 'bg-emerald-600 text-white'
                        : importedResult.match.match_status === 'review'
                        ? 'bg-amber-500 text-white'
                        : 'bg-slate-500 text-white'
                    }`}
                  >
                    %{importedResult.match.match_score} •{' '}
                    {importedResult.match.match_status === 'eligible'
                      ? 'Tam Uygun'
                      : importedResult.match.match_status === 'review'
                      ? 'İnceleme Gerekli'
                      : 'Uygun Değil'}
                  </span>
                  <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    {importedResult.institution}
                  </span>
                </div>

                {onSelectAnnouncement && (
                  <button
                    type="button"
                    onClick={() => onSelectAnnouncement(importedResult.id)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-bold"
                  >
                    <span>İlan Detayını Gör</span>
                  </button>
                )}
              </div>

              <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {importedResult.title}
              </div>
              <div className="text-xs text-slate-700 dark:text-slate-300">
                {importedResult.match.headline}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 4. Auto-scan Interval + Browser Desktop Notifications + Telegram & Webhook */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <Bell className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <h3>Otomatik Tarama & Anlık Bildirim Ayarları</h3>
        </div>

        {/* Browser Desktop Notifications Toggle */}
        <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-800/40 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-start gap-2.5">
            <BellRing className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100">
                Tarayıcı Masaüstü Bildirimleri
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Tarama tamamlandığında yeni tam uygun ilan bulunursa masaüstünüzde anlık bildirim
                gösterilir.
              </p>
              {browserNotifError && (
                <p className="text-xs font-semibold text-red-600 dark:text-red-400 mt-1">
                  {browserNotifError}
                </p>
              )}
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleToggleBrowserNotif()}
            className={`px-3.5 py-2 rounded-xl text-xs font-bold border transition-colors shrink-0 ${
              browserNotifEnabled
                ? 'bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-500'
                : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            {browserNotifEnabled ? 'Masaüstü Bildirimi: Açık ✓' : 'Masaüstü Bildirimlerini Aç'}
          </button>
        </div>

        <form onSubmit={handleSaveSettings} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Otomatik Tarama Aralığı
              </label>
              <select
                value={scanInterval}
                onChange={(e) => setScanInterval(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              >
                <option value={15}>Her 15 Dakikada Bir</option>
                <option value={30}>Her 30 Dakikada Bir</option>
                <option value={60}>Saatlik (60 Dakika)</option>
                <option value={120}>2 Saatte Bir</option>
                <option value={240}>4 Saatte Bir</option>
                <option value={360}>6 Saatte Bir</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Webhook URL (Discord / Slack / Özel Sunucu)
              </label>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://discord.com/api/webhooks/..."
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Telegram Bot Token
              </label>
              <input
                type="text"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                placeholder="123456789:ABCdefGHIjklMNO..."
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Telegram Chat ID
              </label>
              <input
                type="text"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                placeholder="Örn. 987654321"
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {notifSavedMsg && (
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold text-emerald-800 dark:text-emerald-200">
              {notifSavedMsg}
            </div>
          )}

          {testResult && (
            <div
              className={`p-3 rounded-xl border text-xs font-semibold ${
                testResult.sent
                  ? 'bg-emerald-50 dark:bg-emerald-950/50 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
                  : 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-900 text-red-700 dark:text-red-300'
              }`}
            >
              {testResult.sent
                ? `Test bildirimi başarıyla gönderildi (${testResult.channel}).`
                : `Bildirim gönderilemedi (${testResult.channel}): ${
                    testResult.error ?? 'Ayarları kontrol edin.'
                  }`}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <button
              type="button"
              onClick={handleSendTest}
              disabled={testingNotif}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold border border-slate-200 dark:border-slate-700 disabled:opacity-60"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{testingNotif ? 'Gönderiliyor...' : 'Test Bildirimi Gönder'}</span>
            </button>

            <button
              type="submit"
              disabled={savingNotif || !profile}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-sm disabled:opacity-60"
            >
              <Save className="w-4 h-4" />
              <span>{savingNotif ? 'Kaydediliyor...' : 'Ayarları Kaydet'}</span>
            </button>
          </div>
        </form>
      </section>

      {/* 5. Unique Official Portals Compact Quick Strip */}
      <section className="space-y-3">
        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
          Diğer Resmi Portallar Hızlı Erişim
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {UNIQUE_QUICK_PORTALS.map((portal) => (
            <a
              key={portal.name}
              href={portal.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500 p-4 shadow-sm hover:shadow transition-all flex items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-extrabold text-slate-900 dark:text-slate-100 group-hover:text-indigo-700 dark:group-hover:text-indigo-400">
                    {portal.name}
                  </span>
                  <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-[10px] font-semibold">
                    {portal.badge}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
                  {portal.description}
                </p>
              </div>
              <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 shrink-0" />
            </a>
          ))}
        </div>
      </section>

      {/* 6. Optional Collapsible Extra Custom URL Watcher */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
        <button
          type="button"
          onClick={() => setCustomExpanded((prev) => !prev)}
          className="w-full px-5 py-4 flex items-center justify-between gap-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <Globe className="w-4 h-4 text-slate-500 dark:text-slate-400 shrink-0" />
            <div className="min-w-0">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 truncate">
                İsteğe Bağlı Ek URL İzleyici — Listede Olmayan Özel Bir Sayfa İçin
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {customSources.length > 0
                  ? `${customSources.length} ek özel sayfa izleniyor`
                  : `Yukarıdaki ${catalog?.total ?? 163} kurum dışında spesifik bir ilçe belediyesi veya birim sayfası eklemek isterseniz açın`}
              </p>
            </div>
          </div>
          {customExpanded ? (
            <ChevronUp className="w-4 h-4 text-slate-500 shrink-0" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" />
          )}
        </button>

        {customExpanded && (
          <div className="px-5 pb-5 pt-2 border-t border-slate-100 dark:border-slate-800 space-y-4">
            <form onSubmit={handleAddCustomSource} className="grid grid-cols-1 md:grid-cols-12 gap-2.5">
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Kurum Adı (örn. Kadıköy Belediyesi)"
                className="md:col-span-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
              <input
                type="url"
                value={customUrl}
                onChange={(e) => setCustomUrl(e.target.value)}
                placeholder="https://www.kurum.bel.tr/duyurular"
                className="md:col-span-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
              <input
                type="text"
                value={customKeywords}
                onChange={(e) => setCustomKeywords(e.target.value)}
                placeholder="Anahtar kelimeler (virgülle ayırın)"
                className="md:col-span-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs sm:text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={addingCustom}
                className="md:col-span-2 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-bold disabled:opacity-60"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>{addingCustom ? 'Ekleniyor' : 'Ekle'}</span>
              </button>
            </form>

            {customError && (
              <p className="text-xs font-semibold text-red-600 dark:text-red-400">{customError}</p>
            )}

            {loadingCustom ? (
              <div className="text-xs text-slate-500 dark:text-slate-400 py-1">Yükleniyor...</div>
            ) : customSources.length === 0 ? (
              <div className="text-xs text-slate-500 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/50 border border-dashed border-slate-200 dark:border-slate-700 rounded-xl p-3 text-center">
                Henüz ekstra özel URL eklenmedi.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 dark:divide-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
                {customSources.map((cs) => (
                  <div
                    key={cs.id}
                    className="p-3 bg-white dark:bg-slate-900 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="font-bold text-xs sm:text-sm text-slate-900 dark:text-slate-100">
                        {cs.name}
                      </div>
                      <a
                        href={cs.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline inline-flex items-center gap-1 truncate max-w-md"
                      >
                        <span>{cs.url}</span>
                        <ExternalLink className="w-3 h-3 shrink-0" />
                      </a>
                    </div>

                    <button
                      type="button"
                      onClick={() => void handleDeleteCustomSource(cs.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 border border-red-200 dark:border-red-900 self-start sm:self-center"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Sil</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
};
