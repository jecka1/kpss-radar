"""Scraper registry and dispatchers matching ARCHITECTURE.md Section 2.2."""

from __future__ import annotations

from app.scrapers.base import RawAnnouncement
from app.scrapers.custom_watcher import scrape_custom_source
from app.scrapers.isinolsa import scrape_isinolsa
from app.scrapers.memurlar_net import scrape_memurlar_net
from app.scrapers.official_institutions import (
    OFFICIAL_INSTITUTIONS_CATALOG,
    get_institutions_catalog_with_status,
    scrape_bakanliklar_kurumlar,
    scrape_belediyeler,
    scrape_il_belediyeleri,
    scrape_kurullar_kitler,
    scrape_universiteler,
)
from app.scrapers.osym import scrape_osym
from app.scrapers.resmi_gazete import scrape_resmi_gazete
from app.scrapers.sbb_kamuilan import scrape_sbb_kamuilan

SCRAPER_REGISTRY: dict[str, dict] = {
    "sbb_kamuilan": {"label": "SBB Kamu İlan", "url": "https://kamuilan.sbb.gov.tr/"},
    "memurlar_net": {"label": "Memurlar.net İlanlar", "url": "https://ilan.memurlar.net/"},
    "resmi_gazete": {"label": "T.C. Resmî Gazete", "url": "https://www.resmigazete.gov.tr/"},
    "osym": {"label": "ÖSYM KPSS Duyuruları", "url": "https://www.osym.gov.tr/"},
    "isinolsa": {"label": "İşin Olsa Kamu Alımları", "url": "https://www.isinolsa.com/kamu-personeli-alimi/"},
    "bakanliklar_kurumlar": {"label": "Bakanlıklar & Kamu Kurumları (37)", "url": "https://www.turkiye.gov.tr/"},
    "kurullar_kitler": {"label": "Yargı, Üst Kurullar & KİT'ler (35)", "url": "https://www.tbmm.gov.tr/"},
    "belediyeler": {"label": "Büyükşehir Belediyeleri (28)", "url": "https://www.tbb.gov.tr/"},
    "il_belediyeleri": {"label": "İl Belediyeleri (44)", "url": "https://www.tbb.gov.tr/"},
    "universiteler": {"label": "Üniversite Personel Daireleri (19)", "url": "https://www.yok.gov.tr/"},
}


async def run_scraper(
    source_name: str,
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Execute a registered live scraper by name."""
    if source_name == "sbb_kamuilan":
        return await scrape_sbb_kamuilan(known_external_ids=known_external_ids)
    if source_name == "memurlar_net":
        return await scrape_memurlar_net(known_external_ids=known_external_ids)
    if source_name == "resmi_gazete":
        return await scrape_resmi_gazete(known_external_ids=known_external_ids)
    if source_name == "osym":
        return await scrape_osym(known_external_ids=known_external_ids)
    if source_name == "isinolsa":
        return await scrape_isinolsa(known_external_ids=known_external_ids)
    if source_name == "bakanliklar_kurumlar":
        return await scrape_bakanliklar_kurumlar(known_external_ids=known_external_ids)
    if source_name == "kurullar_kitler":
        return await scrape_kurullar_kitler(known_external_ids=known_external_ids)
    if source_name == "belediyeler":
        return await scrape_belediyeler(known_external_ids=known_external_ids)
    if source_name == "il_belediyeleri":
        return await scrape_il_belediyeleri(known_external_ids=known_external_ids)
    if source_name == "universiteler":
        return await scrape_universiteler(known_external_ids=known_external_ids)
    raise ValueError(f"Unknown scraper source: {source_name}")


async def run_custom_source(
    name: str,
    url: str,
    keywords: list[str] | None = None,
) -> list[RawAnnouncement]:
    """Execute the custom URL/RSS watcher for user-configured sources."""
    return await scrape_custom_source(name=name, url=url, keywords=keywords)


__all__ = [
    "RawAnnouncement",
    "SCRAPER_REGISTRY",
    "OFFICIAL_INSTITUTIONS_CATALOG",
    "get_institutions_catalog_with_status",
    "run_scraper",
    "run_custom_source",
]
