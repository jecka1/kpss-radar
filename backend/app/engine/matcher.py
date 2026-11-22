"""Zero-miss 3-tier KPSS eligibility matching engine (ARCHITECTURE.md Section 2.5)."""

from __future__ import annotations

import datetime
import json
from typing import Any

from app.scrapers.base import normalize_ascii_tr

EDU_LABELS = {
    "lisans": "Lisans",
    "onlisans": "Önlisans",
    "ortaogretim": "Ortaöğretim",
    "ilkogretim": "İlköğretim",
}

PRIMARY_SCORE_BY_EDU = {
    "lisans": "P3",
    "onlisans": "P93",
    "ortaogretim": "P94",
}


def _get_extracted(announcement: dict) -> dict:
    ext = announcement.get("extracted")
    if isinstance(ext, dict):
        return ext
    raw_json = announcement.get("extracted_json")
    if isinstance(raw_json, str) and raw_json.strip():
        try:
            return json.loads(raw_json)
        except Exception:
            return {}
    return {}


def _get_cities(announcement: dict, extracted: dict) -> list[str]:
    cities = announcement.get("cities") or extracted.get("cities")
    if isinstance(cities, list) and cities:
        return [str(c) for c in cities if c]
    raw_cities = announcement.get("cities_json")
    if isinstance(raw_cities, str) and raw_cities.strip():
        try:
            parsed = json.loads(raw_cities)
            if isinstance(parsed, list) and parsed:
                return [str(c) for c in parsed if c]
        except Exception:
            pass
    if announcement.get("city"):
        return [str(announcement["city"])]
    return []


def _dept_matches(user_depts: list[str], ad_depts: list[str]) -> list[str]:
    matched: list[str] = []
    for ud in user_depts:
        u_norm = normalize_ascii_tr(ud)
        if not u_norm:
            continue
        for ad in ad_depts:
            a_norm = normalize_ascii_tr(ad)
            if not a_norm:
                continue
            if u_norm == a_norm or u_norm in a_norm or a_norm in u_norm:
                matched.append(ad)
            else:
                # Word-level overlap for e.g. "Bilgisayar Mühendisliği" vs "Mühendis"
                u_words = {w for w in u_norm.split() if len(w) >= 4}
                a_words = {w for w in a_norm.split() if len(w) >= 4}
                if len(u_words & a_words) >= 1 and (u_words & a_words) != {"muhendisligi"}:
                    matched.append(ad)
    return matched


def evaluate_match(announcement: dict, profile: dict) -> dict[str, Any]:
    """
    Evaluate candidate suitability against an announcement with a strict Zero-Miss guarantee:
    - Unconfigured profiles return `review` (score 50).
    - Missing or ambiguous announcement criteria NEVER cause `fail` -> only `unknown` / `warn` (`review`).
    - Only explicit contradictions cause `ineligible`.
    """
    if not profile.get("is_configured", False):
        return {
            "match_status": "review",
            "match_score": 50,
            "headline": "Profilinizi doldurarak kişisel uygunluk analizi alın",
            "reasons": [
                {
                    "field": "education",
                    "label": "Aday Profili",
                    "status": "warn",
                    "message": "Profil henüz yapılandırılmadığı için tüm ilanlar inceleme modunda gösteriliyor.",
                }
            ],
        }

    ext = _get_extracted(announcement)
    reasons: list[dict[str, str]] = []

    # 1. Education Level
    user_edu = str(profile.get("education_level") or "lisans")
    user_edu_label = EDU_LABELS.get(user_edu, user_edu)
    ad_edus: list[str] = [str(e) for e in (ext.get("education_levels") or [])]

    if not ad_edus:
        reasons.append(
            {
                "field": "education",
                "label": "Eğitim Düzeyi",
                "status": "unknown",
                "message": "İlandaki eğitim düzeyi otomatik çıkarılamadı; detayları kontrol edin.",
            }
        )
    elif user_edu in ad_edus:
        reasons.append(
            {
                "field": "education",
                "label": "Eğitim Düzeyi",
                "status": "pass",
                "message": f"{user_edu_label} eğitim düzeyiniz bu ilanla uyumlu.",
            }
        )
    else:
        req_labels = ", ".join(EDU_LABELS.get(e, e) for e in ad_edus)
        reasons.append(
            {
                "field": "education",
                "label": "Eğitim Düzeyi",
                "status": "fail",
                "message": f"İlan yalnızca {req_labels} düzeyi istiyor (Profiliniz: {user_edu_label}).",
            }
        )

    # 2. KPSS Score & Type
    requires_kpss = ext.get("requires_kpss")
    kpss_types: list[str] = [str(k).upper() for k in (ext.get("kpss_types") or [])]
    min_score: float | None = ext.get("min_score")
    user_scores: dict[str, Any] = profile.get("scores") or {}
    include_no_kpss = bool(profile.get("include_no_kpss", True))

    if requires_kpss is False:
        if include_no_kpss:
            reasons.append(
                {
                    "field": "kpss_score",
                    "label": "KPSS Şartı",
                    "status": "pass",
                    "message": "KPSS şartı aranmıyor (KPSS'siz alımlar profilinizde aktif).",
                }
            )
        else:
            reasons.append(
                {
                    "field": "kpss_score",
                    "label": "KPSS Şartı",
                    "status": "fail",
                    "message": "KPSS şartı olmayan bir ilan (profilinizde KPSS'siz alımlar kapalı).",
                }
            )
    elif requires_kpss is None and not kpss_types and min_score is None:
        reasons.append(
            {
                "field": "kpss_score",
                "label": "KPSS Puanı",
                "status": "unknown",
                "message": "KPSS puan türü ve taban puan metinden net çıkarılamadı.",
            }
        )
    else:
        # KPSS is required or types/min_score exist
        matched_user_scores: list[tuple[str, float]] = []
        for kt in kpss_types:
            val = user_scores.get(kt)
            if val is not None:
                try:
                    matched_user_scores.append((kt, float(val)))
                except (TypeError, ValueError):
                    pass

        if kpss_types:
            if matched_user_scores:
                best_type, best_val = max(matched_user_scores, key=lambda x: x[1])
                if min_score is not None:
                    if best_val >= float(min_score):
                        reasons.append(
                            {
                                "field": "kpss_score",
                                "label": "KPSS Puanı",
                                "status": "pass",
                                "message": f"{best_type} puanınız ({best_val:g}) taban puanı ({min_score:g}) karşılıyor.",
                            }
                        )
                    else:
                        reasons.append(
                            {
                                "field": "kpss_score",
                                "label": "KPSS Puanı",
                                "status": "fail",
                                "message": f"{best_type} puanınız ({best_val:g}) taban puanın ({min_score:g}) altında.",
                            }
                        )
                else:
                    reasons.append(
                        {
                            "field": "kpss_score",
                            "label": "KPSS Puanı",
                            "status": "pass",
                            "message": f"İstenen {', '.join(kpss_types)} puan türlerinden {best_type} ({best_val:g}) profilinizde kayıtlı.",
                        }
                    )
            else:
                reasons.append(
                    {
                        "field": "kpss_score",
                        "label": "KPSS Puanı",
                        "status": "warn",
                        "message": f"İlan {', '.join(kpss_types)} puanı istiyor; profilinizde bu puan türü girilmemiş.",
                    }
                )
        else:
            # No specific kpss_types extracted, only min_score or general KPSS requirement
            primary_key = PRIMARY_SCORE_BY_EDU.get(user_edu, "P3")
            candidate_vals: list[tuple[str, float]] = []
            if user_scores.get(primary_key) is not None:
                candidate_vals.append((primary_key, float(user_scores[primary_key])))
            else:
                for k, v in user_scores.items():
                    if k != "YDS" and v is not None:
                        candidate_vals.append((k, float(v)))

            if min_score is not None and candidate_vals:
                best_k, best_v = max(candidate_vals, key=lambda x: x[1])
                if best_v >= float(min_score):
                    reasons.append(
                        {
                            "field": "kpss_score",
                            "label": "KPSS Puanı",
                            "status": "pass",
                            "message": f"{best_k} puanınız ({best_v:g}) belirtilen taban puanı ({min_score:g}) geçiyor.",
                        }
                    )
                else:
                    reasons.append(
                        {
                            "field": "kpss_score",
                            "label": "KPSS Puanı",
                            "status": "fail",
                            "message": f"{best_k} puanınız ({best_v:g}) taban puanın ({min_score:g}) altında.",
                        }
                    )
            else:
                reasons.append(
                    {
                        "field": "kpss_score",
                        "label": "KPSS Puanı",
                        "status": "unknown",
                        "message": "Puan türü belirtilmemiş; detay metnini kontrol edin.",
                    }
                )

    # 3. Department / Qualification Code
    accepts_any = bool(ext.get("accepts_any_department", False))
    ad_depts: list[str] = [str(d) for d in (ext.get("departments") or [])]
    ad_codes: list[str] = [str(c) for c in (ext.get("qualification_codes") or [])]
    user_depts: list[str] = [str(d) for d in (profile.get("departments") or [])]
    user_codes: list[str] = [str(c) for c in (profile.get("qualification_codes") or [])]

    code_overlap = sorted(set(user_codes) & set(ad_codes))
    dept_overlap = _dept_matches(user_depts, ad_depts)

    if accepts_any:
        reasons.append(
            {
                "field": "department",
                "label": "Bölüm / Nitelik",
                "status": "pass",
                "message": "Herhangi bir bölüm mezunu başvurabiliyor (4001/3001/2001 vb.).",
            }
        )
    elif code_overlap or dept_overlap:
        hit = ", ".join(dept_overlap[:3] or code_overlap[:3])
        reasons.append(
            {
                "field": "department",
                "label": "Bölüm / Nitelik",
                "status": "pass",
                "message": f"Bölüm veya nitelik kodunuz eşleşiyor ({hit}).",
            }
        )
    elif not ad_depts and not ad_codes:
        reasons.append(
            {
                "field": "department",
                "label": "Bölüm / Nitelik",
                "status": "unknown",
                "message": "Aranan bölüm şartı metinden otomatik çıkarılamadı.",
            }
        )
    elif not user_depts and not user_codes:
        reasons.append(
            {
                "field": "department",
                "label": "Bölüm / Nitelik",
                "status": "unknown",
                "message": f"İlanda {', '.join(ad_depts[:3] or ad_codes[:3])} geçiyor; profilinize bölüm ekleyin.",
            }
        )
    else:
        has_pdf = bool(ext.get("has_pdf", False))
        quota_val = announcement.get("quota_count")
        if quota_val is None:
            quota_val = ext.get("quota_count")
        is_single_code_only = (
            len(ad_codes) == 1
            and not has_pdf
            and (quota_val is None or int(quota_val) < 5)
            and len(ad_edus) <= 1
        )
        is_multi_or_pdf = (
            has_pdf
            or (quota_val is not None and int(quota_val) >= 5)
            or (len(ad_depts) >= 2 and not is_single_code_only)
            or len(ad_edus) >= 2
        )
        if is_multi_or_pdf:
            reasons.append(
                {
                    "field": "department",
                    "label": "Bölüm / Nitelik",
                    "status": "warn",
                    "message": "İlanda birden fazla kadro/PDF detayı bulunuyor; bölümünüz listede olabilir — mutlaka inceleyin.",
                }
            )
        else:
            # Narrow single-department call -> definite mismatch
            reasons.append(
                {
                    "field": "department",
                    "label": "Bölüm / Nitelik",
                    "status": "fail",
                    "message": f"İlan {', '.join(ad_depts[:3] or ad_codes[:3])} istiyor; profilinizdeki bölümlerle eşleşmiyor.",
                }
            )

    # 4. Age limit
    max_age = ext.get("max_age")
    birth_year = profile.get("birth_year")
    if max_age is None:
        reasons.append(
            {
                "field": "age",
                "label": "Yaş Şartı",
                "status": "pass",
                "message": "İlanda üst yaş sınırı belirtilmemiş (genel şartlar geçerli).",
            }
        )
    elif birth_year is None:
        reasons.append(
            {
                "field": "age",
                "label": "Yaş Şartı",
                "status": "warn",
                "message": f"İlan en fazla {max_age} yaş şartı arıyor; profilinizde doğum yılı girilmemiş.",
            }
        )
    else:
        current_year = datetime.date.today().year
        approx_age = current_year - int(birth_year)
        if approx_age <= int(max_age):
            reasons.append(
                {
                    "field": "age",
                    "label": "Yaş Şartı",
                    "status": "pass",
                    "message": f"Yaşınız (~{approx_age}) üst sınır olan {max_age} yaşa uygun.",
                }
            )
        else:
            reasons.append(
                {
                    "field": "age",
                    "label": "Yaş Şartı",
                    "status": "fail",
                    "message": f"İlan en fazla {max_age} yaş şartı arıyor (yaklaşık yaşınız: {approx_age}).",
                }
            )

    # 5. City preference
    all_cities = bool(profile.get("all_cities", True))
    pref_cities = [str(c) for c in (profile.get("preferred_cities") or [])]
    ad_cities = _get_cities(announcement, ext)

    if all_cities or not pref_cities:
        reasons.append(
            {
                "field": "city",
                "label": "Şehir",
                "status": "pass",
                "message": "Tüm Türkiye şehirleri tercihleriniz dahilinde.",
            }
        )
    elif not ad_cities:
        reasons.append(
            {
                "field": "city",
                "label": "Şehir",
                "status": "unknown",
                "message": "İlanın görev yeri metinden çıkarılamadı.",
            }
        )
    elif "Türkiye Geneli" in ad_cities or any(
        normalize_ascii_tr(pc) == normalize_ascii_tr(ac)
        for pc in pref_cities
        for ac in ad_cities
    ):
        reasons.append(
            {
                "field": "city",
                "label": "Şehir",
                "status": "pass",
                "message": f"Görev yeri ({', '.join(ad_cities[:3])}) şehir tercihinize uyuyor.",
            }
        )
    else:
        reasons.append(
            {
                "field": "city",
                "label": "Şehir",
                "status": "fail",
                "message": f"Görev yeri ({', '.join(ad_cities[:3])}) seçtiğiniz şehirler arasında değil.",
            }
        )

    # 6. Category preference (if user disabled a category, mark as fail so unwanted categories stay filtered out)
    pref_cats = [str(c) for c in (profile.get("preferred_categories") or [])]
    ad_cat = str(announcement.get("category") or "diger")
    if not pref_cats or ad_cat in pref_cats or ad_cat == "diger":
        reasons.append(
            {
                "field": "category",
                "label": "Alım Türü",
                "status": "pass",
                "message": "Seçili alım kategorileriniz arasında.",
            }
        )
    else:
        reasons.append(
            {
                "field": "category",
                "label": "Alım Türü",
                "status": "fail",
                "message": "Bu kategori profil tercihlerinizde kapalı.",
            }
        )

    # Aggregate 3-tier status
    statuses = [r["status"] for r in reasons]
    fails = [r for r in reasons if r["status"] == "fail"]
    warns_or_unknown = [r for r in reasons if r["status"] in ("warn", "unknown")]
    passes = [r for r in reasons if r["status"] == "pass"]

    if fails:
        match_status = "ineligible"
        base_score = 32 - (len(fails) - 1) * 10 + len(passes) * 3
        match_score = max(5, min(39, base_score))
        headline = fails[0]["message"]
    elif warns_or_unknown:
        match_status = "review"
        # Reward known passes while keeping review in 45-82 range
        score = 52 + len(passes) * 7 - sum(4 for r in reasons if r["status"] == "warn")
        match_score = max(42, min(84, score))
        core_warns = [r for r in warns_or_unknown if r["field"] in ("kpss_score", "education", "department")]
        headline = (core_warns[0] if core_warns else warns_or_unknown[0])["message"]
    else:
        match_status = "eligible"
        bonus = 4 if min_score is not None else 0
        match_score = min(100, 88 + bonus + min(8, len(passes)))
        headline = "Tüm ana şartlar profilinizle tam uyumlu"
        if kpss_types and min_score is not None:
            headline = f"KPSS {'/'.join(kpss_types[:2])} (≥{min_score:g}) ve {user_edu_label} şartlarına tam uyuyor"

    return {
        "match_status": match_status,
        "match_score": int(match_score),
        "headline": headline,
        "reasons": reasons,
    }
