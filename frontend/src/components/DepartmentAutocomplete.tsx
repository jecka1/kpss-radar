import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Plus, Search, Check } from 'lucide-react';
import {
  DEPARTMENT_CATALOG,
  EDUCATION_LABELS,
  normalizeTurkishForSearch,
  type DepartmentCatalogItem,
} from '../constants';

interface DepartmentAutocompleteProps {
  educationLevel: string;
  value: string;
  onChangeValue: (val: string) => void;
  onSelectDepartment: (deptName: string) => void;
  existingDepartments?: string[];
  placeholder?: string;
  clearOnSelect?: boolean;
}

const LEVEL_BADGE_CLASS: Record<DepartmentCatalogItem['level'], string> = {
  lisans:
    'bg-indigo-50 dark:bg-indigo-950/70 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
  onlisans:
    'bg-emerald-50 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
  ortaogretim:
    'bg-amber-50 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-800',
};

export const DepartmentAutocomplete: React.FC<DepartmentAutocompleteProps> = ({
  educationLevel,
  value,
  onChangeValue,
  onSelectDepartment,
  existingDepartments = [],
  placeholder = 'Bölüm ara veya yaz (örn. Dış Ticaret, Bilgisayar, Tıbbi Sekreterlik)...',
  clearOnSelect = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const normalizedExisting = useMemo(
    () => new Set(existingDepartments.map((d) => normalizeTurkishForSearch(d))),
    [existingDepartments]
  );

  const matches = useMemo(() => {
    const q = normalizeTurkishForSearch(value);
    const filtered = DEPARTMENT_CATALOG.filter((item) => {
      if (!q) return item.level === educationLevel || educationLevel === 'ilkogretim';
      return normalizeTurkishForSearch(item.name).includes(q);
    });

    filtered.sort((a, b) => {
      const aLevel = a.level === educationLevel ? 0 : 1;
      const bLevel = b.level === educationLevel ? 0 : 1;
      if (aLevel !== bLevel) return aLevel - bLevel;

      if (q) {
        const aStarts = normalizeTurkishForSearch(a.name).startsWith(q) ? 0 : 1;
        const bStarts = normalizeTurkishForSearch(b.name).startsWith(q) ? 0 : 1;
        if (aStarts !== bStarts) return aStarts - bStarts;
      }
      return a.name.localeCompare(b.name, 'tr-TR');
    });

    return filtered.slice(0, 14);
  }, [value, educationLevel]);

  const trimmedValue = value.trim();
  const hasExactMatch = useMemo(() => {
    if (!trimmedValue) return true;
    const norm = normalizeTurkishForSearch(trimmedValue);
    return DEPARTMENT_CATALOG.some((item) => normalizeTurkishForSearch(item.name) === norm);
  }, [trimmedValue]);

  const showCustomOption = Boolean(trimmedValue) && !hasExactMatch;
  const totalOptionsCount = matches.length + (showCustomOption ? 1 : 0);

  useEffect(() => {
    setActiveIndex(0);
  }, [value, isOpen]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const commitSelection = (deptName: string) => {
    const clean = deptName.trim();
    if (!clean) return;
    onSelectDepartment(clean);
    if (clearOnSelect) {
      onChangeValue('');
    } else {
      onChangeValue(clean);
    }
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) setIsOpen(true);
      else if (totalOptionsCount > 0) {
        setActiveIndex((prev) => (prev + 1) % totalOptionsCount);
      }
      return;
    }

    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (isOpen && totalOptionsCount > 0) {
        setActiveIndex((prev) => (prev - 1 + totalOptionsCount) % totalOptionsCount);
      }
      return;
    }

    if (e.key === 'Enter') {
      if (isOpen && totalOptionsCount > 0) {
        e.preventDefault();
        if (activeIndex < matches.length) {
          commitSelection(matches[activeIndex].name);
        } else if (showCustomOption) {
          commitSelection(trimmedValue);
        }
      } else if (trimmedValue) {
        e.preventDefault();
        commitSelection(trimmedValue);
      }
    }
  };

  return (
    <div ref={containerRef} className="relative flex-1">
      <div className="relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          value={value}
          onFocus={() => setIsOpen(true)}
          onChange={(e) => {
            onChangeValue(e.target.value);
            if (!isOpen) setIsOpen(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
          aria-expanded={isOpen}
          aria-autocomplete="list"
          className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        />
      </div>

      {isOpen && totalOptionsCount > 0 && (
        <div
          role="listbox"
          className="absolute z-40 left-0 right-0 mt-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl max-h-72 overflow-y-auto py-1"
        >
          {matches.map((item, idx) => {
            const isActive = idx === activeIndex;
            const alreadyAdded = normalizedExisting.has(normalizeTurkishForSearch(item.name));
            return (
              <button
                key={`${item.name}-${item.level}`}
                type="button"
                role="option"
                aria-selected={isActive}
                onMouseDown={(e) => {
                  e.preventDefault();
                  commitSelection(item.name);
                }}
                onMouseEnter={() => setActiveIndex(idx)}
                className={`w-full px-3.5 py-2 text-left flex items-center justify-between gap-2 text-xs sm:text-sm transition-colors ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-950 dark:text-indigo-100'
                    : 'text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
                }`}
              >
                <span className="flex items-center gap-2 min-w-0">
                  <span className="font-medium truncate">{item.name}</span>
                  {alreadyAdded && (
                    <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  )}
                </span>
                <span
                  className={`px-2 py-0.5 rounded-md text-[10px] font-bold border shrink-0 ${
                    LEVEL_BADGE_CLASS[item.level]
                  }`}
                >
                  {EDUCATION_LABELS[item.level] ?? item.level}
                </span>
              </button>
            );
          })}

          {showCustomOption && (
            <button
              type="button"
              role="option"
              aria-selected={activeIndex === matches.length}
              onMouseDown={(e) => {
                e.preventDefault();
                commitSelection(trimmedValue);
              }}
              onMouseEnter={() => setActiveIndex(matches.length)}
              className={`w-full px-3.5 py-2 text-left flex items-center gap-2 text-xs sm:text-sm border-t border-slate-100 dark:border-slate-800 transition-colors ${
                activeIndex === matches.length
                  ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-900 dark:text-emerald-200'
                  : 'text-emerald-700 dark:text-emerald-300 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <Plus className="w-4 h-4 shrink-0" />
              <span>
                &quot;<strong>{trimmedValue}</strong>&quot; özel bölüm olarak ekle
              </span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
