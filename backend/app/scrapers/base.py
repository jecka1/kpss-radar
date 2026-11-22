"""Base scraper models, Windows-TLS-resilient HTTP client, and Turkish text/date helpers."""

from __future__ import annotations

import asyncio
import datetime
import hashlib
import io
import logging
import os
import re
import shutil
from dataclasses import dataclass
from typing import Iterable

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

logger = logging.getLogger(__name__)

# Inject Windows system certificate store so Turkish public-sector TLS chains
# (KamuSM / TUBITAK intermediate CAs) verify cleanly on Windows.
try:
    import truststore

    truststore.inject_into_ssl()
except Exception as exc:  # pragma: no cover - defensive fallback
    logger.warning("truststore.inject_into_ssl() failed: %s", exc)


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

TURKISH_MONTHS: dict[str, int] = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}


@dataclass
class RawAnnouncement:
    """Raw announcement contract shared between scrapers and the NLP/DB pipeline."""

    source_name: str
    source_label: str
    external_id: str
    url: str
    title: str
    institution: str
    category: str
    publish_date: str | None
    deadline_date: str | None
    city: str | None
    quota_count: int | None
    raw_text: str
    pdf_url: str | None = None
    application_channel: str | None = None


def turkish_lower(text: str) -> str:
    """Lowercase Turkish text without producing combining-dot artifacts on 'İ'."""
    if not text:
        return ""
    return (
        text.replace("I", "ı")
        .replace("İ", "i")
        .lower()
        .replace("\u0307", "")
    )


def normalize_ascii_tr(text: str) -> str:
    """Fold Turkish characters to ASCII lowercase for fuzzy matching and dedup keys."""
    t = turkish_lower(text)
    translation = str.maketrans("çğıöşüâîû", "cgiosuaiu")
    return t.translate(translation)


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive spaces/tabs while preserving single spaces."""
    if not text:
        return ""
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


def stable_external_id(prefix: str, value: str) -> str:
    """Return a deterministic short ID safe for DB unique constraints."""
    digest = hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{prefix}:{digest}" if prefix else digest


def decode_html_bytes(content: bytes, declared_encoding: str | None = None) -> str:
    """Decode Turkish HTML payloads supporting utf-8 (even with stray non-utf8 bytes) and windows-1254."""
    if not content:
        return ""

    # If the payload is overwhelmingly valid UTF-8 with Turkish characters (even if 1-2 stray
    # bytes exist in an inline CSS comment like ktu.edu.tr), prefer UTF-8 over cp1254 mojibake.
    utf_rep = content.decode("utf-8", errors="replace")
    rep_count = utf_rep.count("\ufffd")
    tr_char_count = sum(1 for ch in utf_rep if ch in "ğüşıöçĞÜŞİÖÇ")
    if rep_count == 0 and tr_char_count > 0:
        return utf_rep
    if tr_char_count > 0 and rep_count <= max(5, len(utf_rep) // 5000) and tr_char_count > rep_count * 5:
        return utf_rep

    head = content[:2500].decode("ascii", errors="ignore")
    meta_match = re.search(r"charset\s*=\s*['\"]?\s*([A-Za-z0-9_\-]+)", head, re.I)
    candidates: list[str] = []

    for enc in (meta_match.group(1) if meta_match else None, declared_encoding):
        if not enc:
            continue
        low = enc.strip().lower()
        if low in {"iso-8859-9", "latin5", "windows-1254", "cp1254"}:
            candidates.append("cp1254")
        elif low in {"utf-8", "utf8"}:
            candidates.append("utf-8")
        else:
            candidates.append(low)

    for fallback in ("utf-8", "cp1254"):
        if fallback not in candidates:
            candidates.append(fallback)

    for enc in candidates:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    return content.decode("cp1254", errors="replace")


def html_to_text(html: str) -> str:
    """Convert HTML into clean, readable Turkish plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [normalize_whitespace(line) for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def extract_pdf_text(pdf_bytes: bytes, max_pages: int = 6) -> str:
    """Extract clean text from the first `max_pages` of a PDF payload."""
    if not pdf_bytes or not pdf_bytes.lstrip().startswith(b"%PDF"):
        return ""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        for page in reader.pages[:max_pages]:
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_text.append(extracted.strip())
        combined = "\n\n".join(pages_text)
        # Clean stray tab/control whitespace from PDF streams
        lines = [normalize_whitespace(line) for line in combined.splitlines()]
        return "\n".join(line for line in lines if line)
    except Exception as exc:
        logger.debug("PDF extraction error: %s", exc)
        return ""


def _resolve_year_for_month(month: int, day: int, ref: datetime.date) -> datetime.date | None:
    """Resolve a day+month without year relative to reference date."""
    candidates: list[datetime.date] = []
    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            candidates.append(datetime.date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    # Prefer the candidate closest to ref (within ~180 days)
    return min(candidates, key=lambda d: abs((d - ref).days))


def parse_turkish_date(
    text: str,
    reference_date: datetime.date | None = None,
) -> str | None:
    """Parse common Turkish date formats into ISO YYYY-MM-DD."""
    if not text:
        return None
    ref = reference_date or datetime.date.today()
    cleaned = normalize_whitespace(text)

    # ISO YYYY-MM-DD
    m = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", cleaned)
    if m:
        try:
            dt = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return dt.isoformat()
        except ValueError:
            pass

    # DD.MM.YYYY or DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"\b(0?[1-9]|[12]\d|3[01])[./-](0?[1-9]|1[0-2])[./-](20\d{2})\b", cleaned)
    if m:
        try:
            dt = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return dt.isoformat()
        except ValueError:
            pass

    # DD MonthName YYYY (or DD MonthName without year)
    low = turkish_lower(cleaned)
    month_pattern = "|".join(re.escape(k) for k in TURKISH_MONTHS.keys())
    m = re.search(
        rf"\b(0?[1-9]|[12]\d|3[01])\s+({month_pattern})(?:\s+(20\d{{2}}))?\b",
        low,
    )
    if m:
        day = int(m.group(1))
        month = TURKISH_MONTHS[m.group(2)]
        year_str = m.group(3)
        if year_str:
            try:
                return datetime.date(int(year_str), month, day).isoformat()
            except ValueError:
                return None
        resolved = _resolve_year_for_month(month, day, ref)
        return resolved.isoformat() if resolved else None

    return None


def parse_date_range(
    text: str,
    reference_date: datetime.date | None = None,
) -> tuple[str | None, str | None]:
    """Parse ranges like '30 Kasım - 6 Aralık' or '28.11.2026 - 12.12.2026'."""
    if not text:
        return None, None
    ref = reference_date or datetime.date.today()
    cleaned = normalize_whitespace(text)

    # Split on '-', '–', '—', 'ile'
    parts = re.split(r"\s*[-–—]\s*|\s+ile\s+", cleaned, maxsplit=1)
    if len(parts) == 2:
        end_iso = parse_turkish_date(parts[1], reference_date=ref)
        if end_iso:
            end_dt = datetime.date.fromisoformat(end_iso)
            start_iso = parse_turkish_date(parts[0], reference_date=end_dt)
            if start_iso:
                start_dt = datetime.date.fromisoformat(start_iso)
                if start_dt > end_dt and not re.search(r"20\d{2}", parts[0]):
                    try:
                        start_dt = datetime.date(end_dt.year - 1, start_dt.month, start_dt.day)
                        start_iso = start_dt.isoformat()
                    except ValueError:
                        pass
            return start_iso, end_iso

    single = parse_turkish_date(cleaned, reference_date=ref)
    return single, None


def extract_quota_from_text(title: str, text: str = "") -> int | None:
    """Extract total recruitment quota count from title or leading announcement text."""
    for source in (title, text[:1500]):
        if not source:
            continue
        low = turkish_lower(source)
        # Match patterns like "181 sözleşmeli personel", "50 müfettiş yardımcısı", "6 uzman, 1 destek"
        matches = re.findall(
            r"\b(\d{1,4})\s*(?:adet\s*)?(?:"
            r"sözleşmeli\s+(?:personel|uzman|mühendis|tekniker|büro|hemşire|avukat|bilişim)|"
            r"personel|memur|işçi|daimi\s+işçi|geçici\s+işçi|müfettiş\s+yardımcısı|"
            r"uzman\s+yardımcısı|denetçi\s+yardımcısı|kontrolör|kaymakam\s+adayı|"
            r"öğretim\s+(?:üyesi|elemanı|görevlisi)|araştırma\s+görevlisi|"
            r"zabıt\s+katibi|infaz\s+ve\s+koruma|koruma\s+ve\s+güvenlik|şoför|"
            r"destek\s+personeli|büro\s+personeli|uzman|pozisyon|kadro|kişi"
            r")\b",
            low,
        )
        if matches:
            total = sum(int(x) for x in matches if 1 <= int(x) <= 5000)
            if total > 0:
                return total
    return None


def is_cancelled_announcement_title(title: str) -> bool:
    """Return True if the announcement title represents a cancellation notice."""
    if not title:
        return False
    low = turkish_lower(title)
    if re.search(
        r"\biptal\s+ilan[ıi]|\balım[ıi]?\s+iptal|\bdüzeltme\s*(?:&|ve)\s*iptal|\biptal\s+duyuru|\biptal\s+edil",
        low,
    ):
        return True
    # Catch standalone "... İPTAL" or "İPTAL İLANI" while avoiding false positives
    if re.search(r"\biptal\b", low) and "iptal edilmeyen" not in low:
        return True
    return False


def infer_category(title: str, raw_text: str = "", default: str = "diger") -> str:
    """Infer standardized KPSS Radar category from title and body text."""
    combined = turkish_lower(f"{title} {raw_text[:2000]}")
    title_low = turkish_lower(title)
    if any(k in combined for k in ("ekpss", "engelli personel", "engelli işçi", "engelli memur", "engelli alım")):
        return "engelli"
    if any(k in combined for k in ("sydv", "sosyal yardımlaşma ve dayanışma vakfı", "sosyal yardımlaşma vakfı")):
        return "sydv"
    if any(
        k in title_low
        for k in ("4/b", "4-b", "sözleşmeli personel", "sözleşmeli bilişim", "sözleşmeli uzman", "sözleşmeli büro")
    ):
        return "sozlesmeli_4b"
    if any(
        k in combined
        for k in (
            "öğretim üyesi",
            "öğretim elemanı",
            "öğretim görevlisi",
            "araştırma görevlisi",
            "profesör",
            "doçent",
            "doktor öğretim",
        )
    ):
        return "akademik"
    if any(
        k in combined
        for k in (
            "müfettiş yardımcısı",
            "uzman yardımcısı",
            "denetçi yardımcısı",
            "denetmen yardımcısı",
            "kontrolör",
            "kaymakam adayı",
            "gelir uzman",
            "vergi müfettiş",
            "hakim ve savcı",
            "kalkınma ajansı",
            "kpss a",
        )
    ):
        return "kpss_a"
    uniformed_terms = (
        "subay",
        "astsubay",
        "uzman erbaş",
        "sözleşmeli er",
        "jandarma uzman",
        "polis",
        "bekçi",
        "pomem",
        "pmyo",
        "paem",
    )
    has_civilian_title = any(
        civ in title_low for civ in ("memur", "sözleşmeli personel", "işçi", "4/b", "4-b")
    ) or ("sözleşmeli" in title_low and "sözleşmeli er" not in title_low)
    if any(k in title_low for k in uniformed_terms) or (
        not has_civilian_title and any(k in combined for k in uniformed_terms)
    ):
        return "askeri_emniyet"
    if any(
        k in combined
        for k in ("4/b", "4-b", "sözleşmeli personel", "sözleşmeli bilişim", "sözleşmeli uzman", "sözleşmeli büro")
    ):
        return "sozlesmeli_4b"
    # merkezi_atama strictly reserved for ÖSYM central placement / KPSS-202X/Y preference guides
    if (
        re.search(r"\bkpss\s*[-/]?\s*202\d\s*/\s*\d+\b", combined)
        or "ösym üzerinden tercih" in combined
        or "tercih kılavuzu" in title_low
        or ("merkezi yerleştirme" in combined and "sözleşmeli personel" not in title_low)
        or ("merkezi atama" in combined and "sözleşmeli personel" not in title_low)
    ):
        return "merkezi_atama"
    if any(k in combined for k in ("işçi", "daimi işçi", "geçici işçi", "temizlik görevlisi", "beden işçisi", "işkur")):
        return "isci"
    if any(k in combined for k in ("memur", "zabıta", "itfaiye eri", "zabıt katibi", "mübaşir", "657 sayılı")):
        return "memur"
    return default


def infer_application_channel(text: str) -> str | None:
    """Detect application channel from announcement body/links."""
    if not text:
        return None
    low = turkish_lower(text)
    if "kariyer kapısı" in low or "kariyerkapisi.cbiko.gov.tr" in low or "kariyerkapisi.gov.tr" in low:
        return "Kariyer Kapısı"
    if "ais.osym.gov.tr" in low or "ösym aday işlemleri" in low or "ösym" in low and "tercih" in low:
        return "ÖSYM AİS"
    if "işkur" in low or "iskur.gov.tr" in low:
        return "İŞKUR"
    if any(k in low for k in (".gov.tr", ".edu.tr", ".bel.tr", "şahsen", "posta yoluyla", "elektronik ortamda", "başvuru")):
        return "Kurum Sitesi"
    return None


class HttpClient:
    """Async HTTP client with Windows TLS truststore support, retries, and curl fallback."""

    def __init__(self, timeout: float = 15.0, max_retries: int = 2) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    async def _curl_fallback(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Fallback to system curl (Windows Schannel / Linux OpenSSL) if httpx fails on TLS."""
        curl_bin = shutil.which("curl") or ("curl.exe" if os.name == "nt" else "curl")
        cmd = [
            curl_bin,
            "-sSL",
            "--max-time",
            str(int(timeout or self.timeout)),
            "-A",
            DEFAULT_USER_AGENT,
        ]
        for k, v in (headers or {}).items():
            cmd.extend(["-H", f"{k}: {v}"])
        cmd.append(url)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0 or not stdout:
            raise RuntimeError(
                f"{curl_bin} failed ({proc.returncode}) for {url}: "
                f"{stderr.decode('utf-8', errors='ignore')[:200]}"
            )
        return stdout

    async def get_bytes(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> tuple[bytes, str | None]:
        """Fetch raw response bytes and optional declared charset."""
        req_headers = dict(self.default_headers)
        if headers:
            req_headers.update(headers)

        req_timeout = timeout or self.timeout
        last_exc: Exception | None = None

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(req_timeout),
            follow_redirects=True,
            headers=req_headers,
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.content, resp.encoding
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (400, 401, 403, 404, 410):
                        raise
                    last_exc = exc
                except Exception as exc:
                    last_exc = exc

                if attempt < self.max_retries:
                    await asyncio.sleep(0.5 * (attempt + 1))

        # Final fallback via Windows curl.exe (uses Schannel)
        try:
            data = await self._curl_fallback(url, headers=headers, timeout=req_timeout)
            return data, None
        except Exception as curl_exc:
            raise RuntimeError(f"HTTP GET failed for {url}: {last_exc or curl_exc}") from last_exc

    async def get_text(
        self,
        url: str,
        encoding: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> str:
        """Fetch and decode HTML/XML/text payload."""
        content, declared = await self.get_bytes(url, headers=headers, timeout=timeout)
        return decode_html_bytes(content, declared_encoding=encoding or declared)


def deduplicate_preserve_order(items: Iterable[str]) -> list[str]:
    """Deduplicate strings while preserving insertion order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
