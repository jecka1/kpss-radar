import React, { useEffect, useMemo, useState } from 'react';
import {
  Save,
  CheckCircle2,
  Plus,
  X,
  Search,
  GraduationCap,
  Award,
  BookOpen,
  Tag,
  User,
  MapPin,
  Briefcase,
  Loader2,
  Zap,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from 'lucide-react';
import { searchNitelikKodlari } from '../api';
import type { EducationLevel, KpssScoreKey, NitelikKodu, UserProfile } from '../types';
import {
  CATEGORY_LIST,
  DRIVER_LICENSE_OPTIONS,
  EDUCATION_LABELS,
  EDUCATION_OPTIONS,
  KPSS_SCORE_META,
  SAMPLE_PROFILE,
  TURKEY_CITIES,
  getDepartmentsForEducation,
} from '../constants';
import { DepartmentAutocomplete } from './DepartmentAutocomplete';

interface ProfilePageProps {
  profile: UserProfile | null;
  onSaveProfile: (profile: UserProfile) => Promise<void>;
}

const PRIMARY_SCORE_KEYS_BY_LEVEL: Record<EducationLevel, KpssScoreKey[]> = {
  lisans: ['P3', 'P1', 'P2', 'P10', 'P121', 'EKPSS', 'YDS'],
  onlisans: ['P93', 'EKPSS', 'YDS'],
  ortaogretim: ['P94', 'EKPSS'],
  ilkogretim: ['EKPSS'],
};

export const ProfilePage: React.FC<ProfilePageProps> = ({ profile, onSaveProfile }) => {
  const baseline = useMemo(
    () => profile ?? { ...SAMPLE_PROFILE, is_configured: false },
    [profile]
  );

  const [form, setForm] = useState<UserProfile>(baseline);
  const [showAllScores, setShowAllScores] = useState(false);
  const [newDepartment, setNewDepartment] = useState('');
  const [newCertificate, setNewCertificate] = useState('');
  const [nitelikQuery, setNitelikQuery] = useState('');
  const [nitelikResults, setNitelikResults] = useState<NitelikKodu[]>([]);
  const [nitelikLoading, setNitelikLoading] = useState(false);
  const [citySearch, setCitySearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (profile) {
      setForm(profile);
    }
  }, [profile]);

  const isDirty = useMemo(() => {
    return JSON.stringify(form) !== JSON.stringify(baseline);
  }, [form, baseline]);

  // Live ÖSYM qualification code search
  useEffect(() => {
    const q = nitelikQuery.trim();
    const timer = setTimeout(async () => {
      setNitelikLoading(true);
      try {
        const results = await searchNitelikKodlari(q || '4001');
        setNitelikResults(results.slice(0, 12));
      } catch {
        setNitelikResults([]);
      } finally {
        setNitelikLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [nitelikQuery]);

  const currentYear = new Date().getFullYear();
  const computedAge =
    form.birth_year && form.birth_year > 1940 && form.birth_year <= currentYear
      ? currentYear - form.birth_year
      : null;

  const filteredCities = useMemo(() => {
    const q = citySearch.trim().toLocaleLowerCase('tr-TR');
    if (!q) return TURKEY_CITIES;
    return TURKEY_CITIES.filter((c) => c.toLocaleLowerCase('tr-TR').includes(q));
  }, [citySearch]);

  const primaryScoreKeys = useMemo(
    () => PRIMARY_SCORE_KEYS_BY_LEVEL[form.education_level] ?? ['P3', 'P93', 'P94'],
    [form.education_level]
  );

  const visibleScoreMeta = useMemo(() => {
    if (showAllScores) return KPSS_SCORE_META;
    return KPSS_SCORE_META.filter(
      (m) =>
        primaryScoreKeys.includes(m.key) ||
        (form.scores[m.key] !== null && form.scores[m.key] !== undefined)
    );
  }, [showAllScores, primaryScoreKeys, form.scores]);

  const hiddenScoreCount = KPSS_SCORE_META.length - visibleScoreMeta.length;

  const quickPickDepartments = useMemo(
    () => getDepartmentsForEducation(form.education_level),
    [form.education_level]
  );

  const handleScoreChange = (key: KpssScoreKey, raw: string) => {
    const trimmed = raw.trim().replace(',', '.');
    const val = trimmed === '' ? null : Number(trimmed);
    if (val !== null && Number.isNaN(val)) return;
    setForm((prev) => ({
      ...prev,
      scores: {
        ...prev.scores,
        [key]: val,
      },
    }));
  };

  const addDepartment = (dept: string) => {
    const clean = dept.trim();
    if (!clean) return;
    if (
      form.departments.some(
        (d) => d.toLocaleLowerCase('tr-TR') === clean.toLocaleLowerCase('tr-TR')
      )
    ) {
      return;
    }
    setForm((prev) => ({ ...prev, departments: [...prev.departments, clean] }));
    setNewDepartment('');
  };

  const removeDepartment = (dept: string) => {
    setForm((prev) => ({
      ...prev,
      departments: prev.departments.filter((d) => d !== dept),
    }));
  };

  const toggleQualificationCode = (code: string) => {
    setForm((prev) => {
      const exists = prev.qualification_codes.includes(code);
      return {
        ...prev,
        qualification_codes: exists
          ? prev.qualification_codes.filter((c) => c !== code)
          : [...prev.qualification_codes, code],
      };
    });
  };

  const toggleDriverLicense = (lic: string) => {
    setForm((prev) => {
      const exists = prev.driver_licenses.includes(lic);
      return {
        ...prev,
        driver_licenses: exists
          ? prev.driver_licenses.filter((l) => l !== lic)
          : [...prev.driver_licenses, lic],
      };
    });
  };

  const addCertificate = () => {
    const clean = newCertificate.trim();
    if (!clean) return;
    if (!form.certificates.includes(clean)) {
      setForm((prev) => ({ ...prev, certificates: [...prev.certificates, clean] }));
    }
    setNewCertificate('');
  };

  const toggleCity = (city: string) => {
    setForm((prev) => {
      const exists = prev.preferred_cities.includes(city);
      return {
        ...prev,
        preferred_cities: exists
          ? prev.preferred_cities.filter((c) => c !== city)
          : [...prev.preferred_cities, city],
      };
    });
  };

  const toggleCategory = (cat: string) => {
    setForm((prev) => {
      const exists = prev.preferred_categories.includes(cat);
      return {
        ...prev,
        preferred_categories: exists
          ? prev.preferred_categories.filter((c) => c !== cat)
          : [...prev.preferred_categories, cat],
      };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);

    try {
      await onSaveProfile({
        ...form,
        is_configured: true,
      });
      setSaveSuccess(
        'Profiliniz kaydedildi! Tüm ilanların uygunluk skorları güncel profilinize göre yeniden hesaplandı.'
      );
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Profil kaydedilirken hata oluştu.');
    } finally {
      setSaving(false);
    }
  };

  const handleFillSample = () => {
    if (
      profile?.is_configured &&
      !window.confirm(
        'Mevcut kayıtlı profil bilgileriniz örnek profil verileriyle değiştirilecek. Devam etmek istiyor musunuz?'
      )
    ) {
      return;
    }
    setForm({ ...SAMPLE_PROFILE, is_configured: true });
    setSaveSuccess(null);
    setSaveError(null);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 pb-24">
      {/* Page Header */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 dark:text-slate-100">
            Aday Profilim & KPSS Bilgileri
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Puanlarınız, bölümünüz ve nitelik kodlarınız tüm ilanlarla anlık olarak karşılaştırılır.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {!profile?.is_configured && (
            <button
              type="button"
              onClick={handleFillSample}
              className="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 dark:hover:bg-amber-900/60 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-xs font-bold transition-colors"
            >
              <Zap className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
              <span>Örnek Profili Doldur</span>
            </button>
          )}

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-sm transition-colors disabled:opacity-60"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            <span>{saving ? 'Kaydediliyor...' : 'Profili Kaydet'}</span>
          </button>
        </div>
      </div>

      {saveSuccess && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 text-sm font-semibold flex items-center gap-2.5">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>{saveSuccess}</span>
        </div>
      )}

      {saveError && (
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-800 dark:text-red-300 text-sm font-semibold">
          {saveError}
        </div>
      )}

      {/* 1. Education Level & Exam Year */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <GraduationCap className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          <h3>Eğitim Düzeyi ve Sınav Yılı</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {EDUCATION_OPTIONS.map((opt) => {
            const active = form.education_level === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() =>
                  setForm((prev) => ({ ...prev, education_level: opt.value as EducationLevel }))
                }
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  active
                    ? 'border-emerald-600 bg-emerald-50/70 dark:bg-emerald-950/40 ring-2 ring-emerald-500/20'
                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800/60'
                }`}
              >
                <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  {opt.label}
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {opt.subtitle}
                </div>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Ad Soyad / Profil Etiketi
            </label>
            <input
              type="text"
              value={form.full_name}
              onChange={(e) => setForm((prev) => ({ ...prev, full_name: e.target.value }))}
              placeholder="Örn. Ahmet Yılmaz"
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              KPSS Sınav Yılı
            </label>
            <select
              value={form.kpss_year}
              onChange={(e) => setForm((prev) => ({ ...prev, kpss_year: Number(e.target.value) }))}
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              {[2026, 2025, 2024, 2023, 2022].map((yr) => (
                <option key={yr} value={yr}>
                  {yr} KPSS
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* 2. KPSS Scores (Filtered by Education Level + Expandable) */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
            <Award className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3>
              KPSS, EKPSS ve YDS Puanları ({EDUCATION_LABELS[form.education_level]})
            </h3>
          </div>

          {hiddenScoreCount > 0 && (
            <button
              type="button"
              onClick={() => setShowAllScores((p) => !p)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200"
            >
              {showAllScores ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5" />
                  <span>Yalnızca İlgili Puanları Göster</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5" />
                  <span>Diğer Puan Türlerini Göster (+{hiddenScoreCount})</span>
                </>
              )}
            </button>
          )}
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Seçtiğiniz {EDUCATION_LABELS[form.education_level]} düzeyine uygun ana puan türleri öne
          çıkarıldı. Boş bıraktığınız puan türleri dikkate alınmaz.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {visibleScoreMeta.map((meta) => (
            <div
              key={meta.key}
              className="p-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <label
                  htmlFor={`score-${meta.key}`}
                  className="text-xs font-bold text-slate-800 dark:text-slate-200"
                >
                  {meta.label}
                </label>
                {form.scores[meta.key] !== null && (
                  <button
                    type="button"
                    onClick={() => handleScoreChange(meta.key, '')}
                    className="text-[11px] text-slate-400 hover:text-red-600 dark:hover:text-red-400"
                  >
                    Temizle
                  </button>
                )}
              </div>
              <input
                id={`score-${meta.key}`}
                type="number"
                step="0.01"
                min="0"
                max="100"
                placeholder="Örn. 84.50"
                value={form.scores[meta.key] ?? ''}
                onChange={(e) => handleScoreChange(meta.key, e.target.value)}
                className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-900 dark:text-slate-100 focus:border-emerald-500 focus:outline-none"
              />
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
                {meta.hint}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Graduation Departments */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <BookOpen className="w-5 h-5 text-sky-600 dark:text-sky-400" />
          <h3>Mezuniyet Bölümleri</h3>
        </div>

        {/* Selected Departments */}
        <div className="flex flex-wrap gap-2">
          {form.departments.length === 0 ? (
            <span className="text-xs text-slate-500 dark:text-slate-400 italic">
              Henüz bölüm eklenmedi.
            </span>
          ) : (
            form.departments.map((dept) => (
              <span
                key={dept}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 dark:bg-indigo-600 text-white text-xs font-semibold"
              >
                <span>{dept}</span>
                <button
                  type="button"
                  onClick={() => removeDepartment(dept)}
                  className="hover:text-red-300"
                  aria-label={`${dept} bölümünü kaldır`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Add / Autocomplete Department */}
        <div className="flex gap-2">
          <DepartmentAutocomplete
            educationLevel={form.education_level}
            value={newDepartment}
            onChangeValue={setNewDepartment}
            onSelectDepartment={addDepartment}
            existingDepartments={form.departments}
            clearOnSelect
          />
          <button
            type="button"
            onClick={() => addDepartment(newDepartment)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 dark:bg-indigo-600 hover:bg-slate-800 dark:hover:bg-indigo-500 text-white text-xs font-bold shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Ekle</span>
          </button>
        </div>

        {/* Quick pick filtered by education level */}
        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
            Yaygın {EDUCATION_LABELS[form.education_level]} Bölümleri (Hızlı Ekle):
          </p>
          <div className="flex flex-wrap gap-1.5">
            {quickPickDepartments.map((dept) => {
              const added = form.departments.includes(dept);
              return (
                <button
                  key={dept}
                  type="button"
                  onClick={() => (added ? removeDepartment(dept) : addDepartment(dept))}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                    added
                      ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                      : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                  }`}
                >
                  {added ? '✓ ' : '+ '}
                  {dept}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* 4. Live ÖSYM Nitelik Kodları Search */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <Tag className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          <h3>ÖSYM Nitelik Kodları</h3>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          ÖSYM tercih kılavuzlarındaki nitelik kodlarınızı arayıp tek tıkla profilinize ekleyin
          (örn. 4001, 3001, 4531, 6225, 7225).
        </p>

        {/* Selected Codes */}
        <div className="flex flex-wrap gap-2">
          {form.qualification_codes.length === 0 ? (
            <span className="text-xs text-slate-500 dark:text-slate-400 italic">
              Henüz nitelik kodu eklenmedi.
            </span>
          ) : (
            form.qualification_codes.map((code) => (
              <span
                key={code}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-violet-600 text-white text-xs font-bold"
              >
                <span>{code}</span>
                <button
                  type="button"
                  onClick={() => toggleQualificationCode(code)}
                  className="hover:text-violet-200"
                  aria-label={`${code} kodunu kaldır`}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))
          )}
        </div>

        {/* Live Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={nitelikQuery}
            onChange={(e) => setNitelikQuery(e.target.value)}
            placeholder="Nitelik kodu veya bölüm adı ara (örn. 4001, 3001, bilgisayar, 6225)..."
            className="w-full pl-9 pr-10 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/20"
          />
          {nitelikLoading && (
            <Loader2 className="w-4 h-4 animate-spin text-violet-600 absolute right-3.5 top-1/2 -translate-y-1/2" />
          )}
        </div>

        {/* Search Results */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
          {nitelikResults.map((nk) => {
            const added = form.qualification_codes.includes(nk.code);
            return (
              <button
                key={nk.code}
                type="button"
                onClick={() => toggleQualificationCode(nk.code)}
                className={`p-3 rounded-xl border text-left transition-all flex items-start justify-between gap-2 ${
                  added
                    ? 'bg-violet-50 dark:bg-violet-950/50 border-violet-400 dark:border-violet-700 ring-1 ring-violet-400/40'
                    : 'bg-slate-50/70 dark:bg-slate-800/60 hover:bg-slate-100 dark:hover:bg-slate-800 border-slate-200 dark:border-slate-700'
                }`}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-md bg-slate-900 dark:bg-slate-700 text-white text-xs font-bold">
                      {nk.code}
                    </span>
                    <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      {EDUCATION_LABELS[nk.level] ?? nk.level}
                    </span>
                  </div>
                  <p className="text-xs font-medium text-slate-800 dark:text-slate-200 mt-1 leading-snug">
                    {nk.title}
                  </p>
                </div>
                <span
                  className={`shrink-0 text-xs font-bold px-2 py-1 rounded-lg ${
                    added
                      ? 'bg-violet-600 text-white'
                      : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200'
                  }`}
                >
                  {added ? 'Eklendi' : '+ Ekle'}
                </span>
              </button>
            );
          })}
          {!nitelikLoading && nitelikResults.length === 0 && nitelikQuery.trim() && (
            <div className="col-span-full text-xs text-slate-500 dark:text-slate-400 py-3 text-center">
              &quot;{nitelikQuery}&quot; için eşleşen nitelik kodu bulunamadı.
            </div>
          )}
        </div>
      </section>

      {/* 5. Personal Info, Driver Licenses & Certificates */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <User className="w-5 h-5 text-slate-700 dark:text-slate-300" />
          <h3>Kişisel Bilgiler & Belgeler</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Doğum Yılı{' '}
              {computedAge !== null && (
                <span className="text-emerald-700 dark:text-emerald-400 font-bold">
                  ({computedAge} yaş)
                </span>
              )}
            </label>
            <input
              type="number"
              min="1950"
              max="2010"
              value={form.birth_year ?? ''}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  birth_year: e.target.value ? Number(e.target.value) : null,
                }))
              }
              placeholder="Örn. 1999"
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Cinsiyet
            </label>
            <select
              value={form.gender}
              onChange={(e) => setForm((prev) => ({ ...prev, gender: e.target.value }))}
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              <option value="belirtmek_istemiyorum">Belirtmek İstemiyorum</option>
              <option value="erkek">Erkek</option>
              <option value="kadin">Kadın</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Askerlik Durumu
            </label>
            <select
              value={form.military_status}
              onChange={(e) => setForm((prev) => ({ ...prev, military_status: e.target.value }))}
              className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              <option value="muaf_veya_yapildi">Yapıldı / Muaf / İlgisiz</option>
              <option value="tecilli">Tecilli</option>
              <option value="yapilmadi">Yapılmadı</option>
            </select>
          </div>
        </div>

        {/* Driver Licenses */}
        <div>
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Sürücü Belgeleri
          </p>
          <div className="flex flex-wrap gap-2">
            {DRIVER_LICENSE_OPTIONS.map((lic) => {
              const selected = form.driver_licenses.includes(lic);
              return (
                <button
                  key={lic}
                  type="button"
                  onClick={() => toggleDriverLicense(lic)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-colors ${
                    selected
                      ? 'bg-slate-900 dark:bg-indigo-600 text-white border-slate-900 dark:border-indigo-600'
                      : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                  }`}
                >
                  {lic}
                </button>
              );
            })}
          </div>
        </div>

        {/* Certificates */}
        <div>
          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Sertifikalar (MEB Bilgisayar İşletmenliği, Silahlı Güvenlik vb.)
          </p>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {form.certificates.map((cert) => (
              <span
                key={cert}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-medium"
              >
                <span>{cert}</span>
                <button
                  type="button"
                  onClick={() =>
                    setForm((prev) => ({
                      ...prev,
                      certificates: prev.certificates.filter((c) => c !== cert),
                    }))
                  }
                  className="text-slate-400 hover:text-red-600"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={newCertificate}
              onChange={(e) => setNewCertificate(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addCertificate();
                }
              }}
              placeholder="Sertifika adı ekleyin..."
              className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={addCertificate}
              className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold"
            >
              Ekle
            </button>
          </div>
        </div>
      </section>

      {/* 6. City Preferences (Compact when Tüm Türkiye active) */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
            <MapPin className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            <h3>Şehir Tercihleri</h3>
          </div>

          <label className="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 cursor-pointer text-xs font-bold text-emerald-900 dark:text-emerald-200">
            <input
              type="checkbox"
              checked={form.all_cities}
              onChange={(e) => setForm((prev) => ({ ...prev, all_cities: e.target.checked }))}
              className="rounded text-emerald-600 focus:ring-emerald-500"
            />
            <span>Tüm Türkiye (81 İl) İlanlarını Göster</span>
          </label>
        </div>

        {form.all_cities ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            81 ilin tamamındaki ilanlar profilinizle eşleştirilir. Yalnızca belirli illeri takip
            etmek isterseniz yukarıdaki kutucuğu kapatın.
          </p>
        ) : (
          <div className="space-y-3 pt-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <input
                type="text"
                value={citySearch}
                onChange={(e) => setCitySearch(e.target.value)}
                placeholder="İl ara..."
                className="w-full sm:w-72 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3.5 py-2 text-sm text-slate-900 dark:text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Seçili: <strong className="text-slate-900 dark:text-white">{form.preferred_cities.length}</strong> il
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-1.5 max-h-60 overflow-y-auto p-1">
              {filteredCities.map((city) => {
                const selected = form.preferred_cities.includes(city);
                return (
                  <button
                    key={city}
                    type="button"
                    onClick={() => toggleCity(city)}
                    className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border text-left truncate transition-colors ${
                      selected
                        ? 'bg-slate-900 dark:bg-indigo-600 text-white border-slate-900 dark:border-indigo-600'
                        : 'bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-700'
                    }`}
                  >
                    {city}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* 7. Categories & No-KPSS Switch */}
      <section className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-base font-bold text-slate-900 dark:text-slate-100">
          <Briefcase className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          <h3>İlgilenilen Alım Kategorileri</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {CATEGORY_LIST.map((cat) => {
            const checked = form.preferred_categories.includes(cat.value);
            return (
              <label
                key={cat.value}
                className={`p-3 rounded-xl border cursor-pointer flex items-start gap-2.5 transition-colors ${
                  checked
                    ? 'bg-indigo-50/60 dark:bg-indigo-950/40 border-indigo-300 dark:border-indigo-700'
                    : 'bg-white dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleCategory(cat.value)}
                  className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <div className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    {cat.label}
                  </div>
                  <div className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight mt-0.5">
                    {cat.description}
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
          <label className="inline-flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={form.include_no_kpss}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, include_no_kpss: e.target.checked }))
              }
              className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500"
            />
            <div>
              <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                KPSS Şartı Olmayan Kamu Alımlarını da Göster
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400">
                İŞKUR kura ile işçi alımları, bazı SYDV veya sözleşmeli alımlar da uygunluk
                listesine dahil edilir.
              </div>
            </div>
          </label>
        </div>
      </section>

      {/* Secondary safe sample reset if already configured */}
      {profile?.is_configured && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
          <span className="text-xs text-slate-500 dark:text-slate-400">
            Test amaçlı örnek aday profilini yüklemek isterseniz onaylı olarak sıfırlayabilirsiniz.
          </span>
          <button
            type="button"
            onClick={handleFillSample}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-amber-50 dark:hover:bg-amber-950/50 text-slate-700 dark:text-slate-200 hover:text-amber-900 dark:hover:text-amber-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold transition-colors"
          >
            <Zap className="w-3.5 h-3.5 text-amber-600" />
            <span>Örnek Profili Yükle (Onaylı)</span>
          </button>
        </div>
      )}

      {/* Floating Sticky Save Bar when dirty */}
      {isDirty && (
        <div className="fixed bottom-4 left-4 right-4 lg:left-80 lg:right-8 z-40">
          <div className="max-w-5xl mx-auto rounded-2xl bg-slate-900 dark:bg-slate-800 text-white px-4 sm:px-5 py-3 shadow-2xl border border-slate-700 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              <span>Kaydedilmemiş değişiklikleriniz var</span>
            </div>

            <div className="flex items-center gap-2 ml-auto">
              <button
                type="button"
                onClick={() => setForm(baseline)}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
              >
                Vazgeç
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs sm:text-sm font-extrabold shadow-sm transition-colors disabled:opacity-60"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                <span>{saving ? 'Kaydediliyor...' : 'Değişiklikleri Kaydet'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </form>
  );
};
