"""Cross-source Turkish announcement deduplication and merging engine."""

from __future__ import annotations

import datetime
import hashlib
import re
from difflib import SequenceMatcher

from app.scrapers.base import deduplicate_preserve_order, normalize_ascii_tr

# Generic institutional words stripped to isolate distinctive institution core tokens
_CORE_INST_STOPWORDS = {
    "tc",
    "t",
    "c",
    "rektorlugu",
    "rektorlugunden",
    "rektorluk",
    "baskanligi",
    "baskanligindan",
    "baskanlik",
    "genel",
    "mudurlugu",
    "mudurlugunden",
    "mudurluk",
    "bakanligi",
    "bakanligindan",
    "bakanlik",
    "universitesi",
    "universite",
    "teknik",
    "devlet",
    "belediyesi",
    "belediye",
    "buyuksehir",
    "kurumu",
    "kurum",
    "kurulu",
    "kurul",
    "valiligi",
    "kaymakamligi",
    "il",
    "ozel",
    "idaresi",
    "idare",
    "sosyal",
    "yardimlasma",
    "dayanisma",
    "vakfi",
    "vakif",
    "enstitusu",
    "hastanesi",
    "komutanligi",
    "ajansi",
    "kalkinma",
}

_TITLE_STOPWORDS = {
    "alacak",
    "alimi",
    "alim",
    "ilani",
    "ilan",
    "alinacaktir",
    "duyurusu",
    "duyuru",
    "personel",
    "adet",
    "kisi",
}

_SUBROLE_CONFLICT_GROUPS: list[tuple[str, ...]] = [
    ("ogretim uyesi", "ogretim elemani", "ogretim gorevlisi", "arastirma gorevlisi"),
    ("mufettis", "denetmen", "denetci", "uzman", "kontrolor", "kaymakam"),
    ("on lisans", "lisans", "ortaogretim", "lise", "dhbt", "ekpss"),
    ("sozlesmeli", "akademik", "isci", "memur"),
]


def _normalize_institution(institution: str) -> str:
    norm = normalize_ascii_tr(institution)
    norm = re.sub(r"[^a-z0-9\s]", " ", norm)
    return re.sub(r"\s+", " ", norm).strip()


def extract_core_tokens(institution: str) -> set[str]:
    """Extract distinctive non-generic tokens from an institution name."""
    norm = _normalize_institution(institution)
    tokens = {
        tok
        for tok in norm.split()
        if len(tok) >= 2 and tok not in _CORE_INST_STOPWORDS
    }
    return tokens


def _normalize_title(title: str, institution: str = "") -> str:
    norm = normalize_ascii_tr(title)
    norm = re.sub(r"[^a-z0-9\s]", " ", norm)
    core = extract_core_tokens(institution)
    tokens = [
        t
        for t in norm.split()
        if not t.isdigit()
        and t not in _TITLE_STOPWORDS
        and t not in core
        and t not in _CORE_INST_STOPWORDS
    ]
    return " ".join(tokens)


def _dates_are_close(d1: str | None, d2: str | None, max_days: int = 7) -> bool:
    if not d1 or not d2:
        return True
    try:
        dt1 = datetime.date.fromisoformat(d1[:10])
        dt2 = datetime.date.fromisoformat(d2[:10])
        return abs((dt1 - dt2).days) <= max_days
    except ValueError:
        return True


def compute_dedup_key(
    institution: str,
    title: str,
    publish_date: str | None = None,
) -> str:
    """Compute a normalized Turkish deduplication key based on core institution tokens."""
    core_str = " ".join(sorted(extract_core_tokens(institution)))
    title_core = _normalize_title(title, institution)
    month_bucket = publish_date[:7] if publish_date and len(publish_date) >= 7 else ""
    payload = f"{core_str}|{title_core}|{month_bucket}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]


def _institutions_match(inst_a: str, inst_b: str) -> bool:
    core_a = extract_core_tokens(inst_a)
    core_b = extract_core_tokens(inst_b)
    if not core_a or not core_b:
        return False
    if core_a == core_b:
        return True
    # Allow strict subset match only when one side is an expansion (e.g. "Adalet Bakanlığı Adli Tıp" vs "Adli Tıp")
    # and the intersection is non-trivial
    inter = core_a & core_b
    if not inter:
        return False
    if core_a <= core_b or core_b <= core_a:
        # Guard single generic city token (like "istanbul") matching "istanbul medeniyet" vs "istanbul cerrahpasa"
        # Wait: "istanbul" alone is not a subset of two different universities; it would only match if inst_a was literally "İstanbul Üniversitesi".
        return len(inter) >= 1 and (len(core_a) == len(core_b) or max(len(core_a), len(core_b)) <= len(inter) + 2)
    # Require strong Jaccard overlap (>= 0.75) for minor abbreviation variants; rejects {"gebze"} vs {"erzurum"} (0.0) and {"istanbul","medeniyet"} vs {"istanbul","cerrahpasa"} (0.33)
    union = core_a | core_b
    return (len(inter) / len(union)) >= 0.75


def _has_subrole_or_category_conflict(new_item: dict, existing: dict) -> bool:
    cat_a = new_item.get("category") or "diger"
    cat_b = existing.get("category") or "diger"
    if cat_a != "diger" and cat_b != "diger" and cat_a != cat_b:
        # Never merge e.g. akademik with sozlesmeli_4b, or isci with memur
        compatible_pairs = {
            frozenset({"memur", "sozlesmeli_4b"}),
            frozenset({"kpss_a", "sozlesmeli_4b"}),
        }
        if frozenset({cat_a, cat_b}) not in compatible_pairs:
            return True

    ta = normalize_ascii_tr(new_item.get("title", "")).replace("onlisans", "on lisans")
    tb = normalize_ascii_tr(existing.get("title", "")).replace("onlisans", "on lisans")

    for group in _SUBROLE_CONFLICT_GROUPS:
        hits_a = {term for term in group if re.search(rf"\b{re.escape(term)}\b", ta)}
        hits_b = {term for term in group if re.search(rf"\b{re.escape(term)}\b", tb)}
        if hits_a and hits_b and not (hits_a & hits_b):
            return True
    return False


def _titles_match(new_item: dict, existing: dict) -> bool:
    if _has_subrole_or_category_conflict(new_item, existing):
        return False

    t1 = _normalize_title(new_item.get("title", ""), new_item.get("institution", ""))
    t2 = _normalize_title(existing.get("title", ""), existing.get("institution", ""))
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True

    q1 = new_item.get("quota_count")
    q2 = existing.get("quota_count")
    if q1 is not None and q2 is not None and q1 != q2:
        return False

    if SequenceMatcher(None, t1, t2).ratio() >= 0.74:
        return True

    # Same quota across compatible institution + compatible category/sub-role -> merge
    if q1 is not None and q2 is not None and q1 == q2 and q1 >= 1:
        return True

    return False


def find_matching_existing_id(new_item: dict, existing_items: list[dict]) -> int | None:
    """Find an existing announcement ID representing the same recruitment call across sources."""
    new_source = (new_item.get("source_name") or "").strip()
    new_key = new_item.get("dedup_key") or compute_dedup_key(
        new_item.get("institution", ""),
        new_item.get("title", ""),
        new_item.get("publish_date"),
    )
    new_url = (new_item.get("url") or "").strip()

    for existing in existing_items:
        ex_id = existing.get("id")
        if ex_id is None:
            continue

        existing_sources = existing.get("sources") or []
        existing_source_names = {s.get("source_name") for s in existing_sources if s.get("source_name")}

        # Direct URL match (same URL)
        if new_url and any((src.get("url") or "").strip() == new_url for src in existing_sources):
            return int(ex_id)

        # Rule A: Two different listings from the SAME source_name must never be merged
        if new_source and new_source in existing_source_names:
            continue

        # Must also pass sub-role / category and date guards even on dedup_key match
        if _has_subrole_or_category_conflict(new_item, existing):
            continue
        if not _dates_are_close(new_item.get("publish_date"), existing.get("publish_date"), max_days=7):
            continue
        if not _dates_are_close(new_item.get("deadline_date"), existing.get("deadline_date"), max_days=4):
            continue

        if existing.get("dedup_key") == new_key and _institutions_match(
            new_item.get("institution", ""), existing.get("institution", "")
        ):
            return int(ex_id)

        if _institutions_match(new_item.get("institution", ""), existing.get("institution", "")):
            if _titles_match(new_item, existing):
                return int(ex_id)

    return None


_OFFICIAL_SOURCES = {
    "sbb_kamuilan",
    "resmi_gazete",
    "osym",
    "bakanliklar_kurumlar",
    "kurullar_kitler",
    "belediyeler",
    "il_belediyeleri",
    "universiteler",
    "manual_import",
}


def _source_priority(source_name: str | None) -> int:
    name = (source_name or "").strip()
    if name in _OFFICIAL_SOURCES:
        return 3
    if name == "memurlar_net":
        return 2
    return 1


def _record_priority(record: dict) -> int:
    prios = [_source_priority(record.get("source_name"))]
    for src in record.get("sources") or []:
        prios.append(_source_priority(src.get("source_name")))
    return max(prios)


def _merge_sources(existing_sources: list[dict], incoming_sources: list[dict]) -> list[dict]:
    """Deduplicate sources strictly by source_name (at most one badge per source)."""
    merged_by_name: dict[str, dict] = {}
    for src in existing_sources + incoming_sources:
        s_name = (src.get("source_name") or "").strip()
        if not s_name:
            continue
        if s_name not in merged_by_name:
            merged_by_name[s_name] = dict(src)
        else:
            prev = merged_by_name[s_name]
            prev_ts = prev.get("scraped_at") or ""
            new_ts = src.get("scraped_at") or ""
            if src.get("url") and (not prev.get("url") or new_ts >= prev_ts):
                prev["url"] = src["url"]
            if src.get("pdf_url") and (not prev.get("pdf_url") or new_ts >= prev_ts):
                prev["pdf_url"] = src["pdf_url"]
            if new_ts > prev_ts:
                prev["scraped_at"] = new_ts
    return list(merged_by_name.values())


def _fill_missing_extracted(primary_ext: dict, secondary_ext: dict) -> dict:
    """Keep authoritative primary extracted criteria intact; fill only missing metadata."""
    out = dict(primary_ext)
    for key in ("min_score", "requires_kpss", "max_age", "quota_count", "publish_date", "deadline_date", "application_channel"):
        if out.get(key) is None and secondary_ext.get(key) is not None:
            out[key] = secondary_ext[key]
    for list_key in ("cities",):
        if not out.get(list_key) and secondary_ext.get(list_key):
            out[list_key] = list(secondary_ext[list_key])
    if not out.get("summary") and secondary_ext.get("summary"):
        out["summary"] = secondary_ext["summary"]
    out["has_pdf"] = bool(out.get("has_pdf") or secondary_ext.get("has_pdf"))
    return out


def _merge_extracted(existing_ext: dict, incoming_ext: dict, prefer_incoming: bool) -> dict:
    primary = incoming_ext if prefer_incoming else existing_ext
    secondary = existing_ext if prefer_incoming else incoming_ext

    kpss_types = deduplicate_preserve_order(
        list(primary.get("kpss_types") or []) + list(secondary.get("kpss_types") or [])
    )
    edu_levels = deduplicate_preserve_order(
        list(primary.get("education_levels") or []) + list(secondary.get("education_levels") or [])
    )
    departments = deduplicate_preserve_order(
        list(primary.get("departments") or []) + list(secondary.get("departments") or [])
    )
    qual_codes = deduplicate_preserve_order(
        list(primary.get("qualification_codes") or []) + list(secondary.get("qualification_codes") or [])
    )
    cities = deduplicate_preserve_order(
        list(primary.get("cities") or []) + list(secondary.get("cities") or [])
    )

    min_score = primary.get("min_score")
    if min_score is None:
        min_score = secondary.get("min_score")

    requires_kpss = primary.get("requires_kpss")
    if requires_kpss is None:
        requires_kpss = secondary.get("requires_kpss")

    max_age = primary.get("max_age")
    if max_age is None:
        max_age = secondary.get("max_age")

    return {
        "kpss_types": kpss_types,
        "min_score": min_score,
        "requires_kpss": requires_kpss,
        "education_levels": edu_levels,
        "departments": departments,
        "accepts_any_department": bool(
            primary.get("accepts_any_department") or secondary.get("accepts_any_department")
        ),
        "qualification_codes": qual_codes,
        "max_age": max_age,
        "cities": cities,
        "quota_count": primary.get("quota_count") or secondary.get("quota_count"),
        "publish_date": primary.get("publish_date") or secondary.get("publish_date"),
        "deadline_date": primary.get("deadline_date") or secondary.get("deadline_date"),
        "application_channel": primary.get("application_channel") or secondary.get("application_channel"),
        "has_pdf": bool(primary.get("has_pdf") or secondary.get("has_pdf")),
        "missing_fields": primary.get("missing_fields") or secondary.get("missing_fields") or [],
        "confidence": max(float(primary.get("confidence") or 0.0), float(secondary.get("confidence") or 0.0)),
        "summary": (
            primary.get("summary")
            if len(primary.get("summary") or "") >= len(secondary.get("summary") or "")
            else secondary.get("summary")
        )
        or "",
    }


def merge_announcement_records(existing: dict, incoming: dict) -> dict:
    """Merge an incoming announcement record into an existing DB record with source-priority protection."""
    ex_prio = _record_priority(existing)
    in_prio = _record_priority(incoming)

    ex_text = existing.get("raw_text") or ""
    in_text = incoming.get("raw_text") or ""
    ex_title = existing.get("title") or ""
    in_title = incoming.get("title") or ""
    ex_inst = existing.get("institution") or ""
    in_inst = incoming.get("institution") or ""
    ex_ext = existing.get("extracted") or {}
    in_ext = incoming.get("extracted") or {}

    if in_prio < ex_prio and len(ex_text.strip()) >= 60:
        # Secondary source (e.g. isinolsa) must NOT overwrite primary official title/text/criteria
        raw_text = ex_text
        title = ex_title or in_title
        institution = ex_inst if ex_inst not in ("", "Kamu Kurumu") else (in_inst or ex_inst)
        extracted = _fill_missing_extracted(ex_ext, in_ext)
        summary = existing.get("summary") or extracted.get("summary") or ""
    elif in_prio > ex_prio and len(in_text.strip()) >= 60:
        # Higher-priority official source upgrades existing secondary record cleanly
        raw_text = in_text
        title = in_title or ex_title
        institution = in_inst if in_inst not in ("", "Kamu Kurumu") else (ex_inst or in_inst)
        extracted = _fill_missing_extracted(in_ext, ex_ext)
        summary = incoming.get("summary") or extracted.get("summary") or existing.get("summary") or ""
    else:
        prefer_incoming_text = len(in_text.strip()) > len(ex_text.strip())
        raw_text = in_text if prefer_incoming_text else ex_text
        title = ex_title if len(ex_title) >= len(in_title) else in_title
        institution = (
            in_inst
            if (ex_inst in ("", "Kamu Kurumu") and in_inst not in ("", "Kamu Kurumu"))
            else ex_inst or in_inst
        )
        extracted = _merge_extracted(ex_ext, in_ext, prefer_incoming=prefer_incoming_text)
        summary = existing.get("summary") or ""
        in_summary = incoming.get("summary") or ""
        if prefer_incoming_text and len(in_summary) >= len(summary):
            summary = in_summary
        elif not summary:
            summary = in_summary or extracted.get("summary") or ""

    category = existing.get("category") or "diger"
    if in_prio > ex_prio and incoming.get("category") and incoming["category"] != "diger":
        category = incoming["category"]
    elif category == "diger" and incoming.get("category") and incoming["category"] != "diger":
        category = incoming["category"]

    cities = deduplicate_preserve_order(
        list(existing.get("cities") or []) + list(incoming.get("cities") or [])
    )
    city = existing.get("city") or incoming.get("city") or (cities[0] if cities else None)
    if cities:
        extracted["cities"] = cities

    return {
        **existing,
        "dedup_key": existing.get("dedup_key") or incoming.get("dedup_key"),
        "title": title,
        "institution": institution,
        "category": category,
        "city": city,
        "cities": cities,
        "publish_date": existing.get("publish_date") or incoming.get("publish_date"),
        "deadline_date": existing.get("deadline_date") or incoming.get("deadline_date"),
        "quota_count": existing.get("quota_count") or incoming.get("quota_count"),
        "raw_text": raw_text,
        "summary": summary,
        "extracted": extracted,
        "sources": _merge_sources(existing.get("sources") or [], incoming.get("sources") or []),
    }
