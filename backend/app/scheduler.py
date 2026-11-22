"""Background asyncio scan orchestrator and periodic scheduler for KPSS Radar."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from app import database
from app.config import DEFAULT_SCAN_INTERVAL_MINUTES

logger = logging.getLogger("kpss_radar.scheduler")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _raw_to_item_dict(raw: Any, extracted: dict, scraped_at: str) -> dict:
    """Combine a RawAnnouncement and its extracted criteria into a DB-ready dict."""
    raw_dict = asdict(raw) if is_dataclass(raw) else dict(raw)

    cities = extracted.get("cities") or []
    if not cities and raw_dict.get("city"):
        cities = [raw_dict["city"]]
    city = raw_dict.get("city") or (cities[0] if cities else None)

    publish_date = raw_dict.get("publish_date") or extracted.get("publish_date")
    deadline_date = raw_dict.get("deadline_date") or extracted.get("deadline_date")
    quota_count = (
        raw_dict.get("quota_count")
        if raw_dict.get("quota_count") is not None
        else extracted.get("quota_count")
    )

    extracted_clean = dict(extracted)
    extracted_clean["has_pdf"] = bool(extracted_clean.get("has_pdf") or raw_dict.get("pdf_url"))
    if not extracted_clean.get("application_channel") and raw_dict.get("application_channel"):
        extracted_clean["application_channel"] = raw_dict.get("application_channel")

    source_entry = {
        "source_name": raw_dict["source_name"],
        "source_label": raw_dict.get("source_label") or raw_dict["source_name"],
        "url": raw_dict.get("url") or "",
        "pdf_url": raw_dict.get("pdf_url"),
        "scraped_at": scraped_at,
    }

    return {
        "source_name": raw_dict["source_name"],
        "source_label": source_entry["source_label"],
        "external_id": raw_dict["external_id"],
        "url": source_entry["url"],
        "pdf_url": source_entry["pdf_url"],
        "title": (raw_dict.get("title") or "").strip() or "Kamu Personel Alım İlanı",
        "institution": (raw_dict.get("institution") or "").strip() or "Kamu Kurumu",
        "category": raw_dict.get("category") or "diger",
        "city": city,
        "cities": cities,
        "publish_date": publish_date,
        "deadline_date": deadline_date,
        "quota_count": quota_count,
        "raw_text": raw_dict.get("raw_text") or "",
        "summary": extracted_clean.get("summary") or "",
        "extracted": extracted_clean,
        "sources": [source_entry],
        "scraped_at": scraped_at,
    }


class ScanScheduler:
    """Coordinates manual and periodic scraping, extraction, deduplication, and notifications."""

    def __init__(self) -> None:
        self._scan_lock = asyncio.Lock()
        self._is_scanning: bool = False
        self._current_source: str | None = None
        self._active_task: asyncio.Task | None = None
        self._loop_task: asyncio.Task | None = None
        self._stop_event: asyncio.Event | None = None
        self._last_periodic_run_monotonic: float | None = None

    @property
    def is_scanning(self) -> bool:
        return self._is_scanning

    @property
    def current_source(self) -> str | None:
        return self._current_source

    def get_status(self) -> dict:
        from app.scrapers import SCRAPER_REGISTRY

        latest_by_source = {r["source_name"]: r for r in database.get_latest_scrape_runs()}
        runs: list[dict] = []

        for src_name, meta in SCRAPER_REGISTRY.items():
            if src_name in latest_by_source:
                runs.append(latest_by_source[src_name])
            else:
                runs.append(
                    {
                        "source_name": src_name,
                        "source_label": meta["label"],
                        "url": meta["url"],
                        "status": "idle",
                        "items_found": 0,
                        "items_new": 0,
                        "last_run_at": None,
                        "error_message": None,
                    }
                )

        # Include any custom source runs recorded in DB
        for src_name, run_data in latest_by_source.items():
            if src_name not in SCRAPER_REGISTRY:
                runs.append(run_data)

        return {
            "is_scanning": self._is_scanning,
            "current_source": self._current_source,
            "last_scan_at": database.get_last_scan_at(),
            "runs": runs,
        }

    async def start(self) -> None:
        """Start periodic scheduler loop and trigger initial scan if DB is empty."""
        self._stop_event = asyncio.Event()
        if database.count_announcements() == 0:
            logger.info("Veritabanı boş; ilk arka plan taraması başlatılıyor.")
            self.trigger_scan("all")

        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._periodic_loop(), name="kpss-radar-periodic")

    async def stop(self) -> None:
        """Stop periodic scheduler loop and cancel any in-flight scan task."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        if self._active_task is not None and not self._active_task.done():
            self._active_task.cancel()
            try:
                await self._active_task
            except asyncio.CancelledError:
                pass

    async def _periodic_loop(self) -> None:
        loop = asyncio.get_running_loop()
        self._last_periodic_run_monotonic = loop.time()

        while self._stop_event is not None and not self._stop_event.is_set():
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30.0)
                break
            except asyncio.TimeoutError:
                pass

            try:
                profile = database.get_profile()
                interval_minutes = int(
                    profile.get("scan_interval_minutes") or DEFAULT_SCAN_INTERVAL_MINUTES
                )
                interval_seconds = max(300, interval_minutes * 60)
                now_mono = loop.time()
                if (
                    self._last_periodic_run_monotonic is not None
                    and (now_mono - self._last_periodic_run_monotonic) >= interval_seconds
                ):
                    if not self._is_scanning:
                        logger.info("Periyodik tarama başlatılıyor (aralık: %s dk).", interval_minutes)
                        self.trigger_scan("all")
                    self._last_periodic_run_monotonic = now_mono
            except Exception as exc:
                logger.exception("Periyodik tarama döngüsünde hata: %s", exc)

    def trigger_scan(self, source: str = "all") -> dict:
        """Schedule a background scan if one is not already running."""
        from app.scrapers import SCRAPER_REGISTRY

        if source != "all" and source not in SCRAPER_REGISTRY and not source.startswith("custom:"):
            return {
                "started": False,
                "message": f"Bilinmeyen kaynak: {source}",
            }

        if self._is_scanning or self._scan_lock.locked():
            return {
                "started": False,
                "message": f"Tarama zaten devam ediyor ({self._current_source or 'hazırlanıyor'}).",
            }

        self._is_scanning = True
        self._current_source = source if source != "all" else "Hazırlanıyor"
        self._active_task = asyncio.create_task(
            self.run_scan_once(source), name=f"kpss-scan-{source}"
        )
        return {
            "started": True,
            "message": (
                "Tüm kaynaklar için tarama başlatıldı."
                if source == "all"
                else f"{source} kaynağı için tarama başlatıldı."
            ),
        }

    async def run_scan_once(self, source: str = "all") -> dict:
        """Execute a full or single-source scan sequentially with error isolation."""
        from app.engine.extractor import extract_criteria
        from app.engine.matcher import evaluate_match
        from app.engine.notifier import send_notifications
        from app.scrapers import SCRAPER_REGISTRY, run_custom_source, run_scraper

        def _extract_and_upsert(src_name: str, raw_items: list[Any]) -> dict:
            scraped_at = _now_iso()
            prepared_items: list[dict] = []
            for raw in raw_items:
                try:
                    extracted = extract_criteria(raw)
                except Exception as ext_exc:
                    logger.warning(
                        "Kriter çıkarma hatası (%s - %s): %s",
                        src_name,
                        getattr(raw, "title", "?"),
                        ext_exc,
                    )
                    extracted = {
                        "kpss_types": [],
                        "min_score": None,
                        "requires_kpss": None,
                        "education_levels": [],
                        "departments": [],
                        "accepts_any_department": False,
                        "qualification_codes": [],
                        "max_age": None,
                        "cities": [],
                        "quota_count": None,
                        "publish_date": None,
                        "deadline_date": None,
                        "application_channel": None,
                        "has_pdf": False,
                        "missing_fields": [],
                        "confidence": 0.0,
                        "summary": "",
                    }
                prepared_items.append(_raw_to_item_dict(raw, extracted, scraped_at))

            upsert_res = database.upsert_announcements(prepared_items)
            return {
                "items_found": len(prepared_items),
                "items_new": upsert_res["inserted"],
                "new_ids": upsert_res["new_ids"],
            }

        def _collect_notifications(new_ids: list[int]) -> tuple[dict, list[dict]]:
            profile = database.get_profile()
            has_telegram = bool(
                profile.get("telegram_bot_token") and profile.get("telegram_chat_id")
            )
            has_webhook = bool(profile.get("webhook_url"))
            if not (has_telegram or has_webhook):
                return profile, []

            to_notify: list[dict] = []
            for ann_id in new_ids:
                ann = database.get_announcement_by_id(ann_id)
                if ann is None:
                    continue
                match = evaluate_match(ann, profile)
                ann["match"] = match
                if match["match_status"] == "eligible" or (
                    match["match_status"] == "review" and match["match_score"] >= 70
                ):
                    to_notify.append(ann)
            return profile, to_notify

        async with self._scan_lock:
            self._is_scanning = True
            all_new_ids: list[int] = []
            summary_results: list[dict] = []

            try:
                custom_sources = await asyncio.to_thread(
                    database.list_custom_sources, True
                )

                targets: list[tuple[str, str, str, dict | None]] = []
                if source == "all":
                    for src_name, meta in SCRAPER_REGISTRY.items():
                        targets.append((src_name, meta["label"], meta["url"], None))
                    for cs in custom_sources:
                        src_name = f"custom:{cs['name']}"
                        targets.append((src_name, cs["name"], cs["url"], cs))
                elif source in SCRAPER_REGISTRY:
                    meta = SCRAPER_REGISTRY[source]
                    targets.append((source, meta["label"], meta["url"], None))
                elif source.startswith("custom:"):
                    target_key = source.split(":", 1)[1]
                    for cs in custom_sources:
                        if str(cs["id"]) == target_key or cs["name"] == target_key:
                            targets.append((f"custom:{cs['name']}", cs["name"], cs["url"], cs))

                for src_name, src_label, src_url, custom_cfg in targets:
                    self._current_source = src_label
                    started_at = _now_iso()
                    try:
                        if custom_cfg is not None:
                            raw_items = await run_custom_source(
                                custom_cfg["name"],
                                custom_cfg["url"],
                                custom_cfg.get("keywords") or None,
                            )
                            await asyncio.to_thread(
                                database.update_custom_source_checked, custom_cfg["id"]
                            )
                        else:
                            known_ids = await asyncio.to_thread(
                                database.get_known_external_ids, src_name
                            )
                            raw_items = await run_scraper(src_name, known_external_ids=known_ids)

                        batch_res = await asyncio.to_thread(
                            _extract_and_upsert, src_name, raw_items
                        )
                        items_found = batch_res["items_found"]
                        items_new = batch_res["items_new"]
                        all_new_ids.extend(batch_res["new_ids"])

                        await asyncio.to_thread(
                            database.record_scrape_run,
                            source_name=src_name,
                            source_label=src_label,
                            url=src_url,
                            status="success",
                            items_found=items_found,
                            items_new=items_new,
                            error_message=None,
                            started_at=started_at,
                            finished_at=_now_iso(),
                        )
                        summary_results.append(
                            {
                                "source_name": src_name,
                                "status": "success",
                                "items_found": items_found,
                                "items_new": items_new,
                            }
                        )
                    except Exception as exc:
                        logger.exception("Kaynak tarama hatası (%s): %s", src_name, exc)
                        await asyncio.to_thread(
                            database.record_scrape_run,
                            source_name=src_name,
                            source_label=src_label,
                            url=src_url,
                            status="error",
                            items_found=0,
                            items_new=0,
                            error_message=str(exc)[:500],
                            started_at=started_at,
                            finished_at=_now_iso(),
                        )
                        summary_results.append(
                            {
                                "source_name": src_name,
                                "status": "error",
                                "error": str(exc),
                            }
                        )

                # Send notifications for newly discovered eligible / high-score review announcements
                if all_new_ids:
                    try:
                        profile, to_notify = await asyncio.to_thread(
                            _collect_notifications, all_new_ids
                        )
                        if to_notify:
                            notif_res = await send_notifications(profile, to_notify)
                            if notif_res.get("sent"):
                                await asyncio.to_thread(
                                    database.mark_announcements_notified,
                                    [a["id"] for a in to_notify],
                                )
                    except Exception as notif_exc:
                        logger.exception("Bildirim gönderme hatası: %s", notif_exc)

                loop = asyncio.get_running_loop()
                self._last_periodic_run_monotonic = loop.time()
            finally:
                self._current_source = None
                self._is_scanning = False

            return {"new_ids": all_new_ids, "results": summary_results}


scheduler = ScanScheduler()
