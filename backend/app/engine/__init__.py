"""Turkish KPSS extraction, cross-source deduplication, zero-miss matching, and notification engine."""

from app.engine.deduplicator import (
    compute_dedup_key,
    find_matching_existing_id,
    merge_announcement_records,
)
from app.engine.extractor import extract_criteria
from app.engine.matcher import evaluate_match
from app.engine.notifier import send_notifications, send_test_notification

__all__ = [
    "extract_criteria",
    "compute_dedup_key",
    "find_matching_existing_id",
    "merge_announcement_records",
    "evaluate_match",
    "send_notifications",
    "send_test_notification",
]
