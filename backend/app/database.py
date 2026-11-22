"""SQLite (WAL mode) persistence layer for KPSS Radar."""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.config import DB_PATH, DEFAULT_PROFILE_DICT

_WRITE_LOCK = threading.RLock()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _resolve_db_path(db_path: Path | None = None) -> Path:
    path = Path(db_path) if db_path is not None else Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open a clean SQLite connection configured with WAL mode and Row factory."""
    path = _resolve_db_path(db_path)
    conn = sqlite3.connect(str(path), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        yield conn
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    """Create all database tables and seed default unconfigured profile row if missing."""
    with _WRITE_LOCK, get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                is_configured INTEGER NOT NULL DEFAULT 0,
                profile_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dedup_key TEXT NOT NULL,
                title TEXT NOT NULL,
                institution TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'diger',
                city TEXT,
                cities_json TEXT NOT NULL DEFAULT '[]',
                publish_date TEXT,
                deadline_date TEXT,
                quota_count INTEGER,
                raw_text TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                extracted_json TEXT NOT NULL DEFAULT '{}',
                sources_json TEXT NOT NULL DEFAULT '[]',
                first_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                notified_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_announcements_dedup_key
                ON announcements(dedup_key);
            CREATE INDEX IF NOT EXISTS idx_announcements_deadline
                ON announcements(deadline_date);
            CREATE INDEX IF NOT EXISTS idx_announcements_first_seen
                ON announcements(first_seen_at);

            CREATE TABLE IF NOT EXISTS announcement_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
                source_name TEXT NOT NULL,
                external_id TEXT NOT NULL,
                source_label TEXT NOT NULL,
                url TEXT NOT NULL,
                pdf_url TEXT,
                scraped_at TEXT NOT NULL,
                UNIQUE(source_name, external_id)
            );

            CREATE INDEX IF NOT EXISTS idx_ann_sources_lookup
                ON announcement_sources(source_name, external_id);
            CREATE INDEX IF NOT EXISTS idx_ann_sources_ann_id
                ON announcement_sources(announcement_id);

            CREATE TABLE IF NOT EXISTS user_announcement_state (
                announcement_id INTEGER PRIMARY KEY REFERENCES announcements(id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'none',
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                source_label TEXT NOT NULL,
                url TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                items_found INTEGER NOT NULL DEFAULT 0,
                items_new INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_scrape_runs_source
                ON scrape_runs(source_name, id DESC);

            CREATE TABLE IF NOT EXISTS custom_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                keywords_json TEXT NOT NULL DEFAULT '[]',
                enabled INTEGER NOT NULL DEFAULT 1,
                last_checked_at TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        row = conn.execute("SELECT id FROM user_profile WHERE id = 1").fetchone()
        if row is None:
            default_profile = copy.deepcopy(DEFAULT_PROFILE_DICT)
            conn.execute(
                """
                INSERT INTO user_profile (id, is_configured, profile_json, updated_at)
                VALUES (1, 0, ?, ?)
                """,
                (json.dumps(default_profile, ensure_ascii=False), _now_iso()),
            )
        conn.commit()


def _merge_profile_with_defaults(data: dict) -> dict:
    merged = copy.deepcopy(DEFAULT_PROFILE_DICT)
    for key, value in data.items():
        if key == "scores" and isinstance(value, dict):
            merged["scores"].update(value)
        else:
            merged[key] = value
    return merged


def get_profile(db_path: Path | None = None) -> dict:
    """Return the singleton candidate profile (id=1)."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT is_configured, profile_json FROM user_profile WHERE id = 1"
        ).fetchone()
    if row is None:
        init_db(db_path)
        return copy.deepcopy(DEFAULT_PROFILE_DICT)
    stored = json.loads(row["profile_json"])
    stored["is_configured"] = bool(row["is_configured"])
    return _merge_profile_with_defaults(stored)


def save_profile(profile_data: dict, db_path: Path | None = None) -> dict:
    """Persist singleton candidate profile (id=1) and return normalized dict."""
    merged = _merge_profile_with_defaults(profile_data)
    is_configured = bool(merged.get("is_configured", True))
    merged["is_configured"] = is_configured
    now = _now_iso()
    with _WRITE_LOCK, get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO user_profile (id, is_configured, profile_json, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                is_configured = excluded.is_configured,
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (1 if is_configured else 0, json.dumps(merged, ensure_ascii=False), now),
        )
        conn.commit()
    return merged


def get_known_external_ids(source_name: str, db_path: Path | None = None) -> set[str]:
    """Return external_ids already stored with non-empty text for a given source."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT s.external_id
            FROM announcement_sources s
            JOIN announcements a ON a.id = s.announcement_id
            WHERE s.source_name = ?
              AND LENGTH(TRIM(COALESCE(a.raw_text, ''))) > 20
            """,
            (source_name,),
        ).fetchall()
    return {row["external_id"] for row in rows}


def _row_to_announcement_dict(row: sqlite3.Row) -> dict:
    extracted = json.loads(row["extracted_json"] or "{}")
    cities = json.loads(row["cities_json"] or "[]")
    sources = json.loads(row["sources_json"] or "[]")
    state_status = row["user_status"] if "user_status" in row.keys() and row["user_status"] else "none"
    state_notes = row["user_notes"] if "user_notes" in row.keys() and row["user_notes"] else ""
    return {
        "id": row["id"],
        "dedup_key": row["dedup_key"],
        "title": row["title"],
        "institution": row["institution"],
        "category": row["category"],
        "city": row["city"],
        "cities": cities,
        "publish_date": row["publish_date"],
        "deadline_date": row["deadline_date"],
        "quota_count": row["quota_count"],
        "raw_text": row["raw_text"],
        "summary": row["summary"],
        "extracted": extracted,
        "sources": sources,
        "first_seen_at": row["first_seen_at"],
        "updated_at": row["updated_at"],
        "notified_at": row["notified_at"],
        "user_state": {
            "status": state_status,
            "notes": state_notes,
        },
    }


def list_announcements(db_path: Path | None = None) -> list[dict]:
    """Fetch all announcements joined with user state, newest first."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT a.*,
                   COALESCE(s.status, 'none') AS user_status,
                   COALESCE(s.notes, '') AS user_notes
            FROM announcements a
            LEFT JOIN user_announcement_state s ON s.announcement_id = a.id
            ORDER BY a.id DESC
            """
        ).fetchall()
    return [_row_to_announcement_dict(r) for r in rows]


def get_announcement_by_id(announcement_id: int, db_path: Path | None = None) -> dict | None:
    """Fetch a single announcement with user state by id."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT a.*,
                   COALESCE(s.status, 'none') AS user_status,
                   COALESCE(s.notes, '') AS user_notes
            FROM announcements a
            LEFT JOIN user_announcement_state s ON s.announcement_id = a.id
            WHERE a.id = ?
            """,
            (announcement_id,),
        ).fetchone()
    if row is None:
        return None
    return _row_to_announcement_dict(row)


def update_announcement_state(
    announcement_id: int,
    status: str,
    notes: str = "",
    db_path: Path | None = None,
) -> dict | None:
    """Insert or update the user state for an announcement."""
    now = _now_iso()
    with _WRITE_LOCK, get_connection(db_path) as conn:
        exists = conn.execute(
            "SELECT id FROM announcements WHERE id = ?", (announcement_id,)
        ).fetchone()
        if exists is None:
            return None
        conn.execute(
            """
            INSERT INTO user_announcement_state (announcement_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(announcement_id) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (announcement_id, status, notes, now),
        )
        conn.commit()
    return {"id": announcement_id, "status": status, "notes": notes}


def upsert_announcements(items: list[dict], db_path: Path | None = None) -> dict:
    """
    Insert or merge announcements into SQLite using cross-source deduplication.

    Each item in `items` should contain:
        source_name, source_label, external_id, url, pdf_url, title, institution,
        category, city, cities, publish_date, deadline_date, quota_count,
        raw_text, summary, extracted, sources (optional list)
    Returns:
        {"inserted": int, "updated": int, "new_ids": list[int]}
    """
    if not items:
        return {"inserted": 0, "updated": 0, "new_ids": [], "ids": []}

    from app.engine.deduplicator import (
        compute_dedup_key,
        find_matching_existing_id,
        merge_announcement_records,
    )

    now = _now_iso()
    inserted = 0
    updated = 0
    new_ids: list[int] = []
    all_ids: list[int] = []

    with _WRITE_LOCK, get_connection(db_path) as conn:
        existing_rows = conn.execute(
            "SELECT *, 'none' AS user_status, '' AS user_notes FROM announcements ORDER BY id DESC LIMIT 1000"
        ).fetchall()
        existing_by_id: dict[int, dict] = {
            r["id"]: _row_to_announcement_dict(r) for r in existing_rows
        }
        existing_list: list[dict] = list(existing_by_id.values())

        for raw_item in items:
            source_name = raw_item["source_name"]
            external_id = raw_item["external_id"]
            source_label = raw_item.get("source_label") or source_name
            url = raw_item.get("url") or ""
            pdf_url = raw_item.get("pdf_url")
            scraped_at = raw_item.get("scraped_at") or now

            sources_list = raw_item.get("sources") or [
                {
                    "source_name": source_name,
                    "source_label": source_label,
                    "url": url,
                    "pdf_url": pdf_url,
                    "scraped_at": scraped_at,
                }
            ]
            dedup_key = raw_item.get("dedup_key") or compute_dedup_key(
                raw_item.get("institution", ""),
                raw_item.get("title", ""),
                raw_item.get("publish_date"),
            )
            incoming = {
                **raw_item,
                "dedup_key": dedup_key,
                "sources": sources_list,
                "cities": raw_item.get("cities") or ([raw_item["city"]] if raw_item.get("city") else []),
            }

            # 1) Exact (source_name, external_id) match check
            src_row = conn.execute(
                """
                SELECT announcement_id FROM announcement_sources
                WHERE source_name = ? AND external_id = ?
                """,
                (source_name, external_id),
            ).fetchone()

            target_id: int | None = src_row["announcement_id"] if src_row is not None else None

            # 2) Cross-source deduplication match check
            if target_id is None:
                target_id = find_matching_existing_id(incoming, existing_list)

            if target_id is not None:
                existing_record = existing_by_id.get(target_id)
                if existing_record is None:
                    row = conn.execute(
                        "SELECT *, 'none' AS user_status, '' AS user_notes FROM announcements WHERE id = ?",
                        (target_id,),
                    ).fetchone()
                    if row is not None:
                        existing_record = _row_to_announcement_dict(row)

                if existing_record is not None:
                    merged = merge_announcement_records(existing_record, incoming)
                    conn.execute(
                        """
                        UPDATE announcements SET
                            dedup_key = ?,
                            title = ?,
                            institution = ?,
                            category = ?,
                            city = ?,
                            cities_json = ?,
                            publish_date = ?,
                            deadline_date = ?,
                            quota_count = ?,
                            raw_text = ?,
                            summary = ?,
                            extracted_json = ?,
                            sources_json = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            merged.get("dedup_key") or dedup_key,
                            merged.get("title") or incoming["title"],
                            merged.get("institution") or incoming["institution"],
                            merged.get("category") or incoming.get("category", "diger"),
                            merged.get("city"),
                            json.dumps(merged.get("cities", []), ensure_ascii=False),
                            merged.get("publish_date"),
                            merged.get("deadline_date"),
                            merged.get("quota_count"),
                            merged.get("raw_text", ""),
                            merged.get("summary", ""),
                            json.dumps(merged.get("extracted", {}), ensure_ascii=False),
                            json.dumps(merged.get("sources", sources_list), ensure_ascii=False),
                            now,
                            target_id,
                        ),
                    )
                    conn.execute(
                        """
                        INSERT INTO announcement_sources
                            (announcement_id, source_name, external_id, source_label, url, pdf_url, scraped_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(source_name, external_id) DO UPDATE SET
                            announcement_id = excluded.announcement_id,
                            source_label = excluded.source_label,
                            url = excluded.url,
                            pdf_url = COALESCE(excluded.pdf_url, announcement_sources.pdf_url),
                            scraped_at = excluded.scraped_at
                        """,
                        (target_id, source_name, external_id, source_label, url, pdf_url, scraped_at),
                    )
                    merged["id"] = target_id
                    existing_by_id[target_id] = merged
                    for idx, item in enumerate(existing_list):
                        if item.get("id") == target_id:
                            existing_list[idx] = merged
                            break
                    updated += 1
                    all_ids.append(target_id)
                    continue

            # 3) Insert new announcement
            cursor = conn.execute(
                """
                INSERT INTO announcements (
                    dedup_key, title, institution, category, city, cities_json,
                    publish_date, deadline_date, quota_count, raw_text, summary,
                    extracted_json, sources_json, first_seen_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dedup_key,
                    incoming["title"],
                    incoming["institution"],
                    incoming.get("category", "diger"),
                    incoming.get("city"),
                    json.dumps(incoming.get("cities", []), ensure_ascii=False),
                    incoming.get("publish_date"),
                    incoming.get("deadline_date"),
                    incoming.get("quota_count"),
                    incoming.get("raw_text", ""),
                    incoming.get("summary", ""),
                    json.dumps(incoming.get("extracted", {}), ensure_ascii=False),
                    json.dumps(sources_list, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            new_id = int(cursor.lastrowid)
            conn.execute(
                """
                INSERT INTO announcement_sources
                    (announcement_id, source_name, external_id, source_label, url, pdf_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name, external_id) DO UPDATE SET
                    announcement_id = excluded.announcement_id,
                    source_label = excluded.source_label,
                    url = excluded.url,
                    pdf_url = COALESCE(excluded.pdf_url, announcement_sources.pdf_url),
                    scraped_at = excluded.scraped_at
                """,
                (new_id, source_name, external_id, source_label, url, pdf_url, scraped_at),
            )
            new_record = {
                **incoming,
                "id": new_id,
                "first_seen_at": now,
                "updated_at": now,
                "notified_at": None,
                "user_state": {"status": "none", "notes": ""},
            }
            existing_by_id[new_id] = new_record
            existing_list.insert(0, new_record)
            inserted += 1
            new_ids.append(new_id)
            all_ids.append(new_id)

        conn.commit()

    return {"inserted": inserted, "updated": updated, "new_ids": new_ids, "ids": all_ids}


def mark_announcements_notified(announcement_ids: list[int], db_path: Path | None = None) -> None:
    """Stamp notified_at for newly notified announcements."""
    if not announcement_ids:
        return
    now = _now_iso()
    placeholders = ",".join("?" for _ in announcement_ids)
    with _WRITE_LOCK, get_connection(db_path) as conn:
        conn.execute(
            f"UPDATE announcements SET notified_at = ? WHERE id IN ({placeholders})",
            [now, *announcement_ids],
        )
        conn.commit()


def record_scrape_run(
    source_name: str,
    source_label: str,
    url: str,
    status: str,
    items_found: int = 0,
    items_new: int = 0,
    error_message: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Log a completed or failed scraper run."""
    now = _now_iso()
    with _WRITE_LOCK, get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO scrape_runs
                (source_name, source_label, url, status, items_found, items_new, error_message, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_name,
                source_label,
                url,
                status,
                items_found,
                items_new,
                error_message,
                started_at or now,
                finished_at or now,
            ),
        )
        conn.commit()


def get_latest_scrape_runs(db_path: Path | None = None) -> list[dict]:
    """Return the most recent scrape run per source_name."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT r.*
            FROM scrape_runs r
            INNER JOIN (
                SELECT source_name, MAX(id) AS max_id
                FROM scrape_runs
                GROUP BY source_name
            ) latest ON r.id = latest.max_id
            ORDER BY r.id ASC
            """
        ).fetchall()
    return [
        {
            "source_name": r["source_name"],
            "source_label": r["source_label"],
            "url": r["url"],
            "status": r["status"],
            "items_found": r["items_found"],
            "items_new": r["items_new"],
            "last_run_at": r["finished_at"],
            "error_message": r["error_message"],
        }
        for r in rows
    ]


def get_last_scan_at(db_path: Path | None = None) -> str | None:
    """Return timestamp of the latest scrape run across all sources."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT MAX(finished_at) AS last_scan_at FROM scrape_runs").fetchone()
    return row["last_scan_at"] if row is not None else None


def count_announcements(db_path: Path | None = None) -> int:
    """Return total stored announcement count."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM announcements").fetchone()
    return int(row["cnt"]) if row is not None else 0


def list_custom_sources(enabled_only: bool = False, db_path: Path | None = None) -> list[dict]:
    """Return configured custom watcher sources."""
    query = "SELECT * FROM custom_sources"
    if enabled_only:
        query += " WHERE enabled = 1"
    query += " ORDER BY id DESC"
    with get_connection(db_path) as conn:
        rows = conn.execute(query).fetchall()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "url": r["url"],
            "keywords": json.loads(r["keywords_json"] or "[]"),
            "enabled": bool(r["enabled"]),
            "last_checked_at": r["last_checked_at"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def create_custom_source(
    name: str,
    url: str,
    keywords: list[str] | None = None,
    db_path: Path | None = None,
) -> dict:
    """Create a custom source URL watcher."""
    now = _now_iso()
    clean_keywords = [k.strip() for k in (keywords or []) if k and k.strip()]
    with _WRITE_LOCK, get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO custom_sources (name, url, keywords_json, enabled, created_at)
            VALUES (?, ?, ?, 1, ?)
            """,
            (name.strip(), url.strip(), json.dumps(clean_keywords, ensure_ascii=False), now),
        )
        new_id = int(cursor.lastrowid)
        conn.commit()
    return {
        "id": new_id,
        "name": name.strip(),
        "url": url.strip(),
        "keywords": clean_keywords,
        "enabled": True,
        "last_checked_at": None,
        "created_at": now,
    }


def delete_custom_source(source_id: int, db_path: Path | None = None) -> bool:
    """Delete a custom source by id. Returns True if a row was deleted."""
    with _WRITE_LOCK, get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM custom_sources WHERE id = ?", (source_id,))
        conn.commit()
        return cursor.rowcount > 0


def update_custom_source_checked(source_id: int, db_path: Path | None = None) -> None:
    """Update last_checked_at timestamp on a custom source."""
    with _WRITE_LOCK, get_connection(db_path) as conn:
        conn.execute(
            "UPDATE custom_sources SET last_checked_at = ? WHERE id = ?",
            (_now_iso(), source_id),
        )
        conn.commit()
