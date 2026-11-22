"""Telegram Bot API and generic JSON Webhook notification sender."""

from __future__ import annotations

import html
import logging

import httpx

logger = logging.getLogger(__name__)

# Ensure Windows truststore is active if notifier is called standalone
try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass


def _format_telegram_digest(announcements: list[dict]) -> str:
    lines = [f"<b>KPSS Radar — {len(announcements)} Yeni Uygun İlan</b>", ""]
    for ann in announcements[:8]:
        inst = html.escape(str(ann.get("institution") or "Kamu Kurumu"))
        title = html.escape(str(ann.get("title") or "İlan"))
        match = ann.get("match") or {}
        score = match.get("match_score", 0)
        deadline = ann.get("deadline_date") or "Detayda"
        sources = ann.get("sources") or []
        url = sources[0].get("url", "") if sources else ""

        lines.append(f"• <b>{inst}</b> — {title}")
        lines.append(f"  Uygunluk: <b>%{score}</b> | Son Başvuru: {html.escape(str(deadline))}")
        if url:
            lines.append(f"  <a href=\"{html.escape(url)}\">İlan Bağlantısı</a>")
        lines.append("")

    if len(announcements) > 8:
        lines.append(f"...ve {len(announcements) - 8} ilan daha KPSS Radar panelinde.")
    return "\n".join(lines).strip()


async def _send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or "Telegram API returned ok=false")


async def _send_webhook(webhook_url: str, payload: dict) -> None:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(webhook_url.strip(), json=payload)
        resp.raise_for_status()


async def send_notifications(profile: dict, announcements: list[dict]) -> dict:
    """Send matching announcement alerts via Telegram Bot API and/or Webhook."""
    if not announcements:
        return {"sent": False, "channel": "none", "error": None}

    bot_token = (profile.get("telegram_bot_token") or "").strip()
    chat_id = (profile.get("telegram_chat_id") or "").strip()
    webhook_url = (profile.get("webhook_url") or "").strip()

    has_telegram = bool(bot_token and chat_id)
    has_webhook = bool(webhook_url)
    if not has_telegram and not has_webhook:
        return {"sent": False, "channel": "none", "error": "Bildirim kanalı yapılandırılmamış"}

    channels_sent: list[str] = []
    errors: list[str] = []

    if has_telegram:
        try:
            await _send_telegram(bot_token, chat_id, _format_telegram_digest(announcements))
            channels_sent.append("telegram")
        except Exception as exc:
            logger.warning("Telegram notification failed: %s", exc)
            errors.append(f"Telegram: {exc}")

    if has_webhook:
        try:
            webhook_payload = {
                "event": "kpss_radar.new_matches",
                "count": len(announcements),
                "announcements": [
                    {
                        "id": a.get("id"),
                        "institution": a.get("institution"),
                        "title": a.get("title"),
                        "category": a.get("category"),
                        "deadline_date": a.get("deadline_date"),
                        "match": a.get("match"),
                        "sources": a.get("sources"),
                    }
                    for a in announcements[:20]
                ],
            }
            await _send_webhook(webhook_url, webhook_payload)
            channels_sent.append("webhook")
        except Exception as exc:
            logger.warning("Webhook notification failed: %s", exc)
            errors.append(f"Webhook: {exc}")

    return {
        "sent": len(channels_sent) > 0,
        "channel": "+".join(channels_sent) if channels_sent else "none",
        "error": "; ".join(errors) if errors else None,
    }


async def send_test_notification(profile: dict) -> dict:
    """Send a test message to verify Telegram Bot and/or Webhook configuration."""
    bot_token = (profile.get("telegram_bot_token") or "").strip()
    chat_id = (profile.get("telegram_chat_id") or "").strip()
    webhook_url = (profile.get("webhook_url") or "").strip()

    has_telegram = bool(bot_token and chat_id)
    has_webhook = bool(webhook_url)

    if not has_telegram and not has_webhook:
        return {
            "sent": False,
            "channel": "none",
            "error": "Lütfen önce Telegram Bot Token + Chat ID veya Webhook URL girin.",
        }

    channels_sent: list[str] = []
    errors: list[str] = []

    if has_telegram:
        try:
            await _send_telegram(
                bot_token,
                chat_id,
                "<b>KPSS Radar Test Bildirimi</b>\nBildirim bağlantınız başarıyla çalışıyor!",
            )
            channels_sent.append("telegram")
        except Exception as exc:
            errors.append(f"Telegram: {exc}")

    if has_webhook:
        try:
            await _send_webhook(
                webhook_url,
                {
                    "event": "kpss_radar.test",
                    "message": "KPSS Radar test bildirimi başarıyla ulaştı.",
                },
            )
            channels_sent.append("webhook")
        except Exception as exc:
            errors.append(f"Webhook: {exc}")

    return {
        "sent": len(channels_sent) > 0,
        "channel": "+".join(channels_sent) if channels_sent else "none",
        "error": "; ".join(errors) if errors else None,
    }
