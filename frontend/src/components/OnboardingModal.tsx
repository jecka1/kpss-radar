import React, { useState } from 'react';
import {
  Sparkles,
  CheckCircle2,
  X,
  ArrowRight,
  GraduationCap,
  MapPin,
  Award,
  Zap,
} from 'lucide-react';
import type { EducationLevel, KpssScoreKey, UserProfile } from '../types';
import {
  EDUCATION_OPTIONS,
  SAMPLE_PROFILE,
  TURKEY_CITIES,
  getDepartmentsForEducation,
} from '../constants';
import { DepartmentAutocomplete } from './DepartmentAutocomplete';

interface OnboardingBannerProps {
  onOpenWizard: () => void;
  onUseSampleProfile: () => Promise<void>;
  savingSample: boolean;
}

export const OnboardingBanner: React.FC<OnboardingBannerProps> = ({
  onOpenWizard,
  onUseSampleProfile,
  savingSample,
}) => {
  return (
    <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white p-5 sm:p-6 shadow-md border border-slate-700/70">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="space-y-1.5 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-400/30 text-amber-200 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Profiliniz Henüz Yapılandırılmadı</span>
          </div>
          <h2 className="text-lg sm:text-xl font-bold tracking-tight">
            30 saniyede KPSS profilinizi tanımlayın, size uygun hiçbir alımı kaçırmayın
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            Şu anda tüm ilanlar <strong className="text-amber-300">İnceleme Gerekli</strong> olarak
            gösteriliyor. Eğitim düzeyinizi, puanınızı ve bölümünüzü girerek ilanları otomatik
            olarak puanlayın.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={onOpenWizard}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition-colors shadow-sm"
          >
            <span>Hızlı Kurulum Başlat</span>
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={onUseSampleProfile}
            disabled={savingSample}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-semibold text-sm border border-white/20 transition-colors disabled:opacity-60"
          >
            <Zap className="w-4 h-4 text-amber-300" />
            <span>
              {savingSample ? 'Yükleniyor...' : 'Örnek KPSS Profiliyle Hemen Dene'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

interface OnboardingModalProps {
  isOpen: boolean;
  initialProfile: UserProfile | null;
  onClose: () => void;
  onSaveProfile: (profile: UserProfile) => Promise<void>;
}

const QUICK_SCORE_TYPES: { key: KpssScoreKey; label: string }[] = [
  { key: 'P3', label: 'KPSS P3 (Lisans)' },
  { key: 'P93', label: 'KPSS P93 (Önlisans)' },
  { key: 'P94', label: 'KPSS P94 (Ortaöğretim)' },
  { key: 'P1', label: 'KPSS P1 (A Grubu)' },
  { key: 'EKPSS', label: 'EKPSS' },
];

export const OnboardingModal: React.FC<OnboardingModalProps> = ({
  isOpen,
  initialProfile,
  onClose,
  onSaveProfile,
}) => {
  const [educationLevel, setEducationLevel] = useState<EducationLevel>(
    initialProfile?.education_level ?? 'lisans'
  );
  const [scoreType, setScoreType] = useState<KpssScoreKey>('P3');
  const [scoreValue, setScoreValue] = useState<string>(
    initialProfile?.scores?.P3 ? String(initialProfile.scores.P3) : '82.5'
  );
  const [department, setDepartment] = useState<string>(
    initialProfile?.departments?.[0] ?? 'Bilgisayar Mühendisliği'
  );
  const [birthYear, setBirthYear] = useState<string>(
    initialProfile?.birth_year ? String(initialProfile.birth_year) : '1999'
  );
  const [allCities, setAllCities] = useState<boolean>(initialProfile?.all_cities ?? true);
  const [selectedCity, setSelectedCity] = useState<string>(
    initialProfile?.preferred_cities?.[0] ?? 'Ankara'
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleEducationChange = (level: EducationLevel) => {
    setEducationLevel(level);
    if (level === 'lisans') setScoreType('P3');
    else if (level === 'onlisans') setScoreType('P93');
    else if (level === 'ortaogretim') setScoreType('P94');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      const parsedScore = scoreValue.trim() ? Number(scoreValue.replace(',', '.')) : null;
      if (parsedScore !== null && (Number.isNaN(parsedScore) || parsedScore < 0 || parsedScore > 100)) {
        setError('KPSS puanı 0 ile 100 arasında geçerli bir sayı olmalıdır.');
        setSaving(false);
        return;
      }

      const parsedBirthYear = birthYear.trim() ? Number(birthYear) : null;
      if (
        parsedBirthYear !== null &&
        (Number.isNaN(parsedBirthYear) || parsedBirthYear < 1955 || parsedBirthYear > 2010)
      ) {
        setError('Lütfen geçerli bir doğum yılı girin (1955 - 2010).');
        setSaving(false);
        return;
      }

      const base: UserProfile = initialProfile
        ? { ...initialProfile }
        : { ...SAMPLE_PROFILE };

      const updatedScores = {
        ...base.scores,
        [scoreType]: parsedScore,
      };

      const defaultCode =
        educationLevel === 'lisans'
          ? '4001'
          : educationLevel === 'onlisans'
          ? '3001'
          : educationLevel === 'ortaogretim'
          ? '2001'
          : '';

      const nextQualCodes =
        base.qualification_codes.length > 0
          ? base.qualification_codes
          : defaultCode
          ? [defaultCode]
          : [];

      const payload: UserProfile = {
        ...base,
        is_configured: true,
        education_level: educationLevel,
        scores: updatedScores,
        departments: department.trim() ? [department.trim()] : [],
        qualification_codes: nextQualCodes,
        birth_year: parsedBirthYear,
        all_cities: allCities,
        preferred_cities: allCities ? [] : [selectedCity],
      };

      await onSaveProfile(payload);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Profil kaydedilemedi.');
    } finally {
      setSaving(false);
    }
  };

  const handleUseSample = async () => {
    setError(null);
    setSaving(true);
    try {
      await onSaveProfile({ ...SAMPLE_PROFILE, is_configured: true });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Örnek profil yüklenemedi.');
    } finally {
      setSaving(false);
    }
  };

  const currentYear = new Date().getFullYear();
  const computedAge =
    birthYear.trim() && !Number.isNaN(Number(birthYear))
      ? currentYear - Number(birthYear)
      : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/65 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 w-full max-w-2xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 bg-slate-900 text-white flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 text-emerald-300 text-xs font-semibold mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Hızlı Başlangıç Sihirbazı</span>
            </div>
            <h2 className="text-xl font-bold">KPSS Aday Profilinizi Oluşturun</h2>
            <p className="text-xs text-slate-300 mt-1">
              Bilgilerinizi kaydedin; tüm ilanlar anında sizin için puanlansın.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Kapat"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-5">
          {error && (
            <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm font-medium">
              {error}
            </div>
          )}

          {/* Education */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
              <GraduationCap className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <span>1. Eğitim Düzeyiniz</span>
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {EDUCATION_OPTIONS.map((opt) => {
                const selected = educationLevel === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleEducationChange(opt.value)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      selected
                        ? 'border-emerald-600 bg-emerald-50/70 dark:bg-emerald-950/40 ring-2 ring-emerald-500/20'
                        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800/60'
                    }`}
                  >
                    <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {opt.label}
                    </div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-tight">
                      {opt.subtitle}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Score & Department */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
                <Award className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>2. KPSS Puan Türü & Puanınız</span>
              </label>
              <div className="flex gap-2">
                <select
                  value={scoreType}
                  onChange={(e) => setScoreType(e.target.value as KpssScoreKey)}
                  className="w-40 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm font-medium text-slate-800 dark:text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                >
                  {QUICK_SCORE_TYPES.map((st) => (
                    <option key={st.key} value={st.key}>
                      {st.label}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  placeholder="Örn. 84.5"
                  value={scoreValue}
                  onChange={(e) => setScoreValue(e.target.value)}
                  className="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm font-semibold text-slate-900 dark:text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 block mb-2">
                3. Doğum Yılınız
                {computedAge !== null && computedAge > 15 && computedAge < 75 && (
                  <span className="ml-2 text-xs font-medium text-slate-500 dark:text-slate-400">
                    ({computedAge} yaş)
                  </span>
                )}
              </label>
              <input
                type="number"
                min="1955"
                max="2010"
                placeholder="Örn. 1999"
                value={birthYear}
                onChange={(e) => setBirthYear(e.target.value)}
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm font-medium text-slate-900 dark:text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
              />
            </div>
          </div>

          {/* Department */}
          <div>
            <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 block mb-2">
              4. Mezuniyet Bölümünüz
            </label>
            <DepartmentAutocomplete
              educationLevel={educationLevel}
              value={department}
              onChangeValue={setDepartment}
              onSelectDepartment={setDepartment}
              clearOnSelect={false}
              placeholder="Bölüm ara (örn. Dış Ticaret, Bilgisayar, İşletme)..."
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {getDepartmentsForEducation(educationLevel)
                .slice(0, 5)
                .map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setDepartment(preset)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                      department === preset
                        ? 'bg-slate-900 dark:bg-indigo-600 text-white border-slate-900 dark:border-indigo-600'
                        : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    {preset}
                  </button>
                ))}
            </div>
          </div>

          {/* City Preference */}
          <div>
            <label className="flex items-center gap-2 text-sm font-semibold text-slate-800 dark:text-slate-200 mb-2">
              <MapPin className="w-4 h-4 text-sky-600 dark:text-sky-400" />
              <span>5. Şehir Tercihiniz</span>
            </label>
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 cursor-pointer text-sm font-medium text-slate-800 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={allCities}
                  onChange={(e) => setAllCities(e.target.checked)}
                  className="rounded text-emerald-600 focus:ring-emerald-500"
                />
                <span>Tüm Türkiye (81 İl)</span>
              </label>
              {!allCities && (
                <select
                  value={selectedCity}
                  onChange={(e) => setSelectedCity(e.target.value)}
                  className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 focus:border-emerald-500 focus:outline-none"
                >
                  {TURKEY_CITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Footer Actions */}
          <div className="pt-4 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <button
              type="button"
              onClick={handleUseSample}
              disabled={saving}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 dark:hover:bg-amber-900/60 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-xs sm:text-sm font-semibold transition-colors"
            >
              <Zap className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span>Örnek Profille Hemen Dene (Lisans • P3: 84.5)</span>
            </button>

            <div className="flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Şimdi Değil
              </button>
              <button
                type="submit"
                disabled={saving}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-sm disabled:opacity-60"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{saving ? 'Kaydediliyor...' : 'Profili Kaydet ve Eşleştir'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
