"""Scraper for T.C. Resmî Gazete Çeşitli İlanlar (https://www.resmigazete.gov.tr/)."""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
import urllib.parse

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    extract_pdf_text,
    extract_quota_from_text,
    infer_application_channel,
    infer_category,
    is_cancelled_announcement_title,
    normalize_whitespace,
    turkish_lower,
)

logger = logging.getLogger(__name__)

DAYS_LOOKBACK = 14
MAX_PDF_FETCHES = 40
PDF_CONCURRENCY = 6

# Institutions/notices that are unambiguously non-personnel (saves PDF bandwidth)
NON_PERSONNEL_LINK_PATTERNS = (
    "maden ve petrol işleri",
    "icra dairesi",
    "icra müdürlüğü",
    "sulh hukuk",
    "asliye hukuk",
    "asliye ticaret",
    "vergi dairesi",
    "kadastro",
    "tapu müdürlüğü",
    "iflas müdürlüğü",
    "aile mahkemesi",
    "ağır ceza",
    "tüketici mahkemesi",
)

RECRUITMENT_KEYWORDS = (
    "personel alım",
    "sözleşmeli personel",
    "memur alım",
    "kpss",
    "öğretim üyesi",
    "öğretim elemanı",
    "araştırma görevlisi",
    "öğretim görevlisi",
    "müfettiş yardımcısı",
    "uzman yardımcısı",
    "denetçi yardımcısı",
    "kontrolör",
    "kaymakam adayı",
    "işçi alım",
    "daimi işçi",
    "zabıt katibi",
    "infaz ve koruma",
    "sınav ilanı",
    "giriş sınavı",
    "istihdam edilmek üzere",
    "alınacaktır",
    "657 sayılı devlet memurları",
    "kadro ve pozisyon",
    "başvuruda bulunacak aday",
)

NOISE_KEYWORDS = (
    "petrol hakkına müteallik",
    "ihale ilanı",
    "kapalı teklif usulü",
    "açık teklif usulü",
    "2886 sayılı devlet ihale",
    "4734 sayılı kamu ihale",
    "tebligat ilanı",
    "konkordato",
    "iflasın açılması",
    "kamulaştırma",
    "vergi borcu",
    "gümrük müdürlüğünden",
    "satış ilanı",
)


def _turkish_title_case(text: str) -> str:
    """Convert uppercase Turkish headings cleanly without combining-dot artifacts."""
    words = re.sub(r"\s+", " ", text).strip().split()
    out: list[str] = []
    for w in words:
        low = turkish_lower(w)
        if not low:
            continue
        if low in ("ve", "ile", "veya"):
            out.append(low)
        else:
            first = "İ" if low[0] == "i" else ("I" if low[0] == "ı" else low[0].upper())
            out.append(first + low[1:])
    return " ".join(out)


def _clean_rg_institution(raw_link_text: str) -> str:
    txt = re.sub(r"\s+", " ", raw_link_text).rstrip(":").strip()
    # Strip trailing Turkish ablative 'ndan'/'nden' to preserve nominative vowel ('Başkanlığı', 'Rektörlüğü')
    cleaned = re.sub(r"(?:ndan|nden)$", "", txt, flags=re.I)
    return cleaned.strip() or txt


def _is_obviously_non_personnel(link_text: str) -> bool:
    low = turkish_lower(link_text)
    return any(p in low for p in NON_PERSONNEL_LINK_PATTERNS)


def _is_recruitment_pdf(text: str, institution: str) -> bool:
    """Filter PDF text so tenders, tax notices, and legal summons are excluded."""
    if not text or len(text.strip()) < 80:
        return False
    low = turkish_lower(text)
    rec_hits = sum(1 for k in RECRUITMENT_KEYWORDS if k in low)
    noise_hits = sum(1 for k in NOISE_KEYWORDS if k in low)
    if rec_hits == 0:
        return False
    if noise_hits >= 2 and rec_hits <= 1:
        return False
    return True


def _extract_rg_title(pdf_text: str, institution: str) -> str:
    """Derive a readable announcement title from the top lines of a Resmî Gazete PDF."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in pdf_text.splitlines() if line.strip()]
    for line in lines[:12]:
        low = turkish_lower(line)
        if any(
            k in low
            for k in (
                "alım ilanı",
                "alımı ilanı",
                "giriş sınavı",
                "sınav ilanı",
                "personel alımı",
                "öğretim üyesi",
                "öğretim elemanı",
                "uzman yardımcısı",
                "müfettiş yardımcısı",
            )
        ) and 10 <= len(line) <= 130:
            formatted = _turkish_title_case(line) if line.isupper() else line
            return f"{institution} — {formatted}"

    low_all = turkish_lower(pdf_text[:2000])
    if "öğretim üyesi" in low_all or "öğretim elemanı" in low_all:
        return f"{institution} — Akademik Personel Alım İlanı"
    if "sözleşmeli personel" in low_all:
        return f"{institution} — Sözleşmeli Personel Alım İlanı"
    if "uzman yardımcısı" in low_all or "müfettiş yardımcısı" in low_all:
        return f"{institution} — Kariyer Uzman / Müfettiş Alım İlanı"
    if "işçi" in low_all:
        return f"{institution} — İşçi Alım İlanı"
    return f"{institution} — Kamu Personel Alım İlanı"


async def scrape_resmi_gazete(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scan today + last 7 days of Resmî Gazete Çeşitli İlanlar for recruitment PDFs."""
    known = known_external_ids or set()
    client = HttpClient(timeout=12.0, max_retries=1)
    today = datetime.date.today()

    candidates: list[dict] = []

    async def _fetch_day(offset: int) -> list[dict]:
        dt = today - datetime.timedelta(days=offset)
        day_url = f"https://www.resmigazete.gov.tr/ilanlar/eskiilanlar/{dt:%Y/%m/%Y%m%d}-4.htm"
        try:
            html = await client.get_text(day_url, timeout=10.0)
        except Exception:
            return []

        soup = BeautifulSoup(html, "lxml")
        day_items: list[dict] = []
        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            if ".pdf" not in href.lower():
                continue
            link_text = normalize_whitespace(a.get_text(" ", strip=True))
            if not link_text or _is_obviously_non_personnel(link_text):
                continue

            pdf_url = urllib.parse.urljoin(day_url, href)
            ext_id = href.rsplit("/", 1)[-1].replace(".pdf", "").replace(".PDF", "")
            day_items.append(
                {
                    "external_id": ext_id,
                    "pdf_url": pdf_url,
                    "day_url": day_url,
                    "publish_date": dt.isoformat(),
                    "institution": _clean_rg_institution(link_text),
                }
            )
        return day_items

    day_batches = await asyncio.gather(*(_fetch_day(d) for d in range(DAYS_LOOKBACK + 1)))
    seen_ids: set[str] = set()
    for batch in day_batches:
        for item in batch:
            if item["external_id"] not in seen_ids:
                seen_ids.add(item["external_id"])
                candidates.append(item)

    if not candidates:
        logger.warning("Resmî Gazete returned 0 candidate entries")
        return []

    semaphore = asyncio.Semaphore(PDF_CONCURRENCY)
    pdf_texts: dict[str, str] = {}
    unseen = [c for c in candidates if c["external_id"] not in known][:MAX_PDF_FETCHES]

    async def _fetch_pdf(item: dict) -> None:
        async with semaphore:
            try:
                pdf_bytes, _ = await client.get_bytes(item["pdf_url"], timeout=15.0)
                txt = await asyncio.to_thread(extract_pdf_text, pdf_bytes, 5)
                if txt:
                    pdf_texts[item["external_id"]] = txt
            except Exception as exc:
                logger.debug("RG PDF failed (%s): %s", item["pdf_url"], exc)

    if unseen:
        await asyncio.gather(*(_fetch_pdf(c) for c in unseen), return_exceptions=True)

    results: list[RawAnnouncement] = []
    for item in candidates:
        ext_id = item["external_id"]
        if ext_id in known:
            # Already in DB with full text; return lightweight reference so existing text stays intact
            results.append(
                RawAnnouncement(
                    source_name="resmi_gazete",
                    source_label="Resmî Gazete",
                    external_id=ext_id,
                    url=item["pdf_url"],
                    title=f"{item['institution']} — Resmî Gazete İlanı",
                    institution=item["institution"],
                    category="diger",
                    publish_date=item["publish_date"],
                    deadline_date=None,
                    city=None,
                    quota_count=None,
                    raw_text="",
                    pdf_url=item["pdf_url"],
                    application_channel=None,
                )
            )
            continue

        txt = pdf_texts.get(ext_id, "")
        if not _is_recruitment_pdf(txt, item["institution"]):
            continue

        title = _extract_rg_title(txt, item["institution"])
        if is_cancelled_announcement_title(title) or is_cancelled_announcement_title(txt[:400]):
            continue
        category = infer_category(title, txt, default="memur")
        quota = extract_quota_from_text(title, txt)
        channel = infer_application_channel(txt)

        results.append(
            RawAnnouncement(
                source_name="resmi_gazete",
                source_label="Resmî Gazete",
                external_id=ext_id,
                url=item["pdf_url"],
                title=title,
                institution=item["institution"],
                category=category,
                publish_date=item["publish_date"],
                deadline_date=None,
                city=None,
                quota_count=quota,
                raw_text=txt,
                pdf_url=item["pdf_url"],
                application_channel=channel,
            )
        )

    logger.info(
        "Resmî Gazete scraped %d recruitment announcements (%d unseen PDFs inspected)",
        len(results),
        len(pdf_texts),
    )
    return results
