"""Custom institution/municipality HTML and RSS/Atom feed watcher."""

from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    extract_quota_from_text,
    html_to_text,
    infer_application_channel,
    infer_category,
    normalize_whitespace,
    parse_turkish_date,
    stable_external_id,
    turkish_lower,
)

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "personel",
    "memur",
    "alım",
    "alımı",
    "kpss",
    "sözleşmeli",
    "işçi",
    "sınav",
    "kadro",
    "müfettiş",
    "uzman",
    "öğretim",
]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    low = turkish_lower(text)
    return any(turkish_lower(kw) in low for kw in keywords if kw.strip())


def _parse_rss_or_atom(
    xml_text: str,
    name: str,
    base_url: str,
    keywords: list[str],
) -> list[RawAnnouncement]:
    root = ET.fromstring(xml_text)
    results: list[RawAnnouncement] = []
    source_name = f"custom:{name}"

    # RSS 2.0 <item>
    for item in root.findall(".//item"):
        title = normalize_whitespace(item.findtext("title") or "")
        link = normalize_whitespace(item.findtext("link") or "") or base_url
        desc = html_to_text(item.findtext("description") or "")
        pub_raw = item.findtext("pubDate") or ""
        combined = f"{title} {desc}"
        if not title or not _matches_keywords(combined, keywords):
            continue
        link = urllib.parse.urljoin(base_url, link)
        results.append(
            RawAnnouncement(
                source_name=source_name,
                source_label=name,
                external_id=stable_external_id("custom", link + title),
                url=link,
                title=title,
                institution=name,
                category=infer_category(title, desc),
                publish_date=parse_turkish_date(pub_raw),
                deadline_date=None,
                city=None,
                quota_count=extract_quota_from_text(title, desc),
                raw_text=desc or title,
                pdf_url=link if link.lower().endswith(".pdf") else None,
                application_channel=infer_application_channel(combined) or "Kurum Sitesi",
            )
        )

    # Atom <entry>
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns) + root.findall(".//entry"):
        title_el = entry.find("atom:title", ns) or entry.find("title")
        title = normalize_whitespace(title_el.text if title_el is not None and title_el.text else "")
        link_el = entry.find("atom:link", ns) or entry.find("link")
        link = link_el.attrib.get("href", base_url) if link_el is not None else base_url
        summary_el = entry.find("atom:summary", ns) or entry.find("summary") or entry.find("atom:content", ns)
        desc = html_to_text(summary_el.text if summary_el is not None and summary_el.text else "")
        upd_el = entry.find("atom:updated", ns) or entry.find("updated") or entry.find("atom:published", ns)
        pub_raw = upd_el.text if upd_el is not None and upd_el.text else ""
        combined = f"{title} {desc}"
        if not title or not _matches_keywords(combined, keywords):
            continue
        link = urllib.parse.urljoin(base_url, link)
        results.append(
            RawAnnouncement(
                source_name=source_name,
                source_label=name,
                external_id=stable_external_id("custom", link + title),
                url=link,
                title=title,
                institution=name,
                category=infer_category(title, desc),
                publish_date=parse_turkish_date(pub_raw),
                deadline_date=None,
                city=None,
                quota_count=extract_quota_from_text(title, desc),
                raw_text=desc or title,
                pdf_url=link if link.lower().endswith(".pdf") else None,
                application_channel=infer_application_channel(combined) or "Kurum Sitesi",
            )
        )

    return results


async def scrape_custom_source(
    name: str,
    url: str,
    keywords: list[str] | None = None,
) -> list[RawAnnouncement]:
    """Fetch a custom institution URL or RSS feed and return matching recruitment items."""
    active_keywords = [k for k in (keywords or DEFAULT_KEYWORDS) if k.strip()]
    if not active_keywords:
        active_keywords = list(DEFAULT_KEYWORDS)

    client = HttpClient(timeout=15.0, max_retries=1)
    payload = await client.get_text(url)

    stripped = payload.lstrip()
    if stripped.startswith("<?xml") or "<rss" in stripped[:400].lower() or "<feed" in stripped[:400].lower():
        try:
            return _parse_rss_or_atom(payload, name, url, active_keywords)[:30]
        except Exception as exc:
            logger.debug("Custom RSS parse failed for %s, falling back to HTML: %s", url, exc)

    soup = BeautifulSoup(payload, "lxml")
    results: list[RawAnnouncement] = []
    seen_urls: set[str] = set()
    source_name = f"custom:{name}"

    for a in soup.select("a[href]"):
        href = a.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        text = normalize_whitespace(a.get("title") or a.get_text(" ", strip=True))
        if len(text) < 10 or len(text) > 240:
            continue
        if not _matches_keywords(text, active_keywords):
            continue

        full_url = urllib.parse.urljoin(url, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        results.append(
            RawAnnouncement(
                source_name=source_name,
                source_label=name,
                external_id=stable_external_id("custom", full_url),
                url=full_url,
                title=text,
                institution=name,
                category=infer_category(text),
                publish_date=parse_turkish_date(text),
                deadline_date=None,
                city=None,
                quota_count=extract_quota_from_text(text),
                raw_text=f"{name} — {text}\nKaynak: {full_url}",
                pdf_url=full_url if full_url.lower().endswith(".pdf") else None,
                application_channel=infer_application_channel(text) or "Kurum Sitesi",
            )
        )
        if len(results) >= 30:
            break

    logger.info("Custom source '%s' matched %d announcements", name, len(results))
    return results
