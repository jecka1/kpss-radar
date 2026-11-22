"""End-to-end FastAPI TestClient API tests with an isolated temporary SQLite DB."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config, database, main  # noqa: E402
from app.scheduler import scheduler  # noqa: E402


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    """Provide a FastAPI TestClient wired to an isolated temporary SQLite DB."""
    temp_db = tmp_path / "test_kpss_radar.db"
    monkeypatch.setattr(database, "DB_PATH", temp_db)
    monkeypatch.setattr(config, "DB_PATH", temp_db)

    async def _noop_start() -> None:
        return None

    async def _noop_stop() -> None:
        return None

    monkeypatch.setattr(scheduler, "start", _noop_start)
    monkeypatch.setattr(scheduler, "stop", _noop_stop)

    database.init_db(db_path=temp_db)

    today = datetime.date.today()
    soon_deadline = (today + datetime.timedelta(days=3)).isoformat()
    later_deadline = (today + datetime.timedelta(days=18)).isoformat()

    seed_items = [
        {
            "source_name": "sbb_kamuilan",
            "source_label": "SBB Kamu İlan",
            "external_id": "seed-eligible",
            "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=101",
            "pdf_url": "https://kamuilan.sbb.gov.tr/pdf/101.pdf",
            "title": "10 Memur Alım İlanı",
            "institution": "Gençlik ve Spor Bakanlığı",
            "category": "memur",
            "city": "Ankara",
            "cities": ["Ankara"],
            "publish_date": today.isoformat(),
            "deadline_date": soon_deadline,
            "quota_count": 10,
            "raw_text": "KPSS P3 en az 70 puan ile 4001 nitelik kodlu lisans mezunu memur alımı.",
            "summary": "KPSS P3 en az 70 puan ile 10 memur alımı.",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 70.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "departments": [],
                "accepts_any_department": True,
                "qualification_codes": ["4001"],
                "max_age": None,
                "cities": ["Ankara"],
                "application_channel": "Kariyer Kapısı",
                "has_pdf": True,
                "missing_fields": [],
                "confidence": 0.92,
            },
        },
        {
            "source_name": "memurlar_net",
            "source_label": "Memurlar.net İlanlar",
            "external_id": "seed-review",
            "url": "https://ilan.memurlar.net/ilan/202",
            "pdf_url": None,
            "title": "25 Sözleşmeli Personel Alımı",
            "institution": "İstanbul Üniversitesi",
            "category": "sozlesmeli_4b",
            "city": "İstanbul",
            "cities": ["İstanbul"],
            "publish_date": (today - datetime.timedelta(days=1)).isoformat(),
            "deadline_date": later_deadline,
            "quota_count": 25,
            "raw_text": "İstanbul Üniversitesi 25 sözleşmeli personel ilanı detayları.",
            "summary": "İstanbul Üniversitesi 25 sözleşmeli personel ilanı.",
            "extracted": {
                "kpss_types": [],
                "min_score": None,
                "requires_kpss": None,
                "education_levels": [],
                "departments": [],
                "accepts_any_department": False,
                "qualification_codes": [],
                "max_age": None,
                "cities": ["İstanbul"],
                "application_channel": "Kurum Sitesi",
                "has_pdf": False,
                "missing_fields": ["min_score", "education_levels"],
                "confidence": 0.5,
            },
        },
        {
            "source_name": "resmi_gazete",
            "source_label": "T.C. Resmî Gazete",
            "external_id": "seed-ineligible",
            "url": "https://www.resmigazete.gov.tr/ilan/303",
            "pdf_url": None,
            "title": "1 Tabip Alım İlanı",
            "institution": "İzmir Devlet Hastanesi",
            "category": "sozlesmeli_4b",
            "city": "İzmir",
            "cities": ["İzmir"],
            "publish_date": (today - datetime.timedelta(days=2)).isoformat(),
            "deadline_date": later_deadline,
            "quota_count": 1,
            "raw_text": "Tıp Fakültesi mezunu, KPSS P3 en az 95 puan şartı aranır.",
            "summary": "1 tabip alım ilanı.",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 95.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "departments": ["Tıp"],
                "accepts_any_department": False,
                "qualification_codes": [],
                "max_age": 30,
                "cities": ["İzmir"],
                "application_channel": "Kariyer Kapısı",
                "has_pdf": False,
                "missing_fields": [],
                "confidence": 0.9,
            },
        },
    ]
    database.upsert_announcements(seed_items, db_path=temp_db)

    with TestClient(main.app) as client:
        yield client


def test_health_endpoint(api_client: TestClient):
    resp = api_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_ok"] is True
    assert data["announcements_count"] == 3


def test_profile_get_and_put(api_client: TestClient):
    get_resp = api_client.get("/api/profile")
    assert get_resp.status_code == 200
    initial = get_resp.json()
    assert initial["is_configured"] is False

    payload = {
        **initial,
        "is_configured": True,
        "full_name": "Ayşe Yılmaz",
        "education_level": "lisans",
        "scores": {**initial["scores"], "P3": 85.4},
        "departments": ["Bilgisayar Mühendisliği"],
        "qualification_codes": ["4001", "4531"],
        "birth_year": 1999,
        "all_cities": True,
    }
    put_resp = api_client.put("/api/profile", json=payload)
    assert put_resp.status_code == 200
    saved = put_resp.json()
    assert saved["is_configured"] is True
    assert saved["full_name"] == "Ayşe Yılmaz"
    assert saved["scores"]["P3"] == 85.4

    get_after = api_client.get("/api/profile")
    assert get_after.status_code == 200
    assert get_after.json()["is_configured"] is True


def _configure_profile(api_client: TestClient) -> None:
    prof = api_client.get("/api/profile").json()
    prof["is_configured"] = True
    prof["full_name"] = "Test Aday"
    prof["education_level"] = "lisans"
    prof["scores"]["P3"] = 85.0
    prof["departments"] = ["Bilgisayar Mühendisliği"]
    prof["qualification_codes"] = ["4001"]
    prof["birth_year"] = 1998
    prof["all_cities"] = True
    resp = api_client.put("/api/profile", json=prof)
    assert resp.status_code == 200


def test_announcements_filters_sorting_and_detail(api_client: TestClient):
    _configure_profile(api_client)

    # All active
    all_resp = api_client.get("/api/announcements")
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 3

    # match_status filters
    elig = api_client.get("/api/announcements", params={"match_status": "eligible"}).json()
    assert elig["total"] == 1
    assert elig["items"][0]["institution"] == "Gençlik ve Spor Bakanlığı"

    rev = api_client.get("/api/announcements", params={"match_status": "review"}).json()
    assert rev["total"] == 1
    assert rev["items"][0]["institution"] == "İstanbul Üniversitesi"

    inelig = api_client.get("/api/announcements", params={"match_status": "ineligible"}).json()
    assert inelig["total"] == 1
    assert inelig["items"][0]["institution"] == "İzmir Devlet Hastanesi"

    # category filter
    memur = api_client.get("/api/announcements", params={"category": "memur"}).json()
    assert memur["total"] == 1

    # source filter
    mn = api_client.get("/api/announcements", params={"source": "memurlar_net"}).json()
    assert mn["total"] == 1

    # city filter (Turkish lowercase/ASCII normalization)
    ist = api_client.get("/api/announcements", params={"city": "istanbul"}).json()
    assert ist["total"] == 1
    assert ist["items"][0]["city"] == "İstanbul"

    # deadline_soon filter
    soon = api_client.get("/api/announcements", params={"deadline_soon": True}).json()
    assert soon["total"] == 1
    assert soon["items"][0]["days_remaining"] <= 5

    # free text search q
    q_res = api_client.get("/api/announcements", params={"q": "genclik"}).json()
    assert q_res["total"] == 1

    # sort options
    for sort_mode in ("match_score", "deadline", "newest"):
        s_resp = api_client.get("/api/announcements", params={"sort": sort_mode})
        assert s_resp.status_code == 200
        assert len(s_resp.json()["items"]) == 3

    # Detail endpoint includes raw_text
    ann_id = elig["items"][0]["id"]
    detail_resp = api_client.get(f"/api/announcements/{ann_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert "raw_text" in detail
    assert "4001" in detail["raw_text"]

    # Unknown id -> 404
    assert api_client.get("/api/announcements/999999").status_code == 404


def test_announcement_state_and_stats(api_client: TestClient):
    _configure_profile(api_client)
    items = api_client.get("/api/announcements").json()["items"]
    id_by_inst = {item["institution"]: item["id"] for item in items}

    # Save first, dismiss ineligible
    r_save = api_client.patch(
        f"/api/announcements/{id_by_inst['Gençlik ve Spor Bakanlığı']}/state",
        json={"status": "saved", "notes": "Hafta sonu başvur"},
    )
    assert r_save.status_code == 200
    assert r_save.json()["status"] == "saved"
    assert r_save.json()["notes"] == "Hafta sonu başvur"

    r_dismiss = api_client.patch(
        f"/api/announcements/{id_by_inst['İzmir Devlet Hastanesi']}/state",
        json={"status": "dismissed", "notes": ""},
    )
    assert r_dismiss.status_code == 200

    assert (
        api_client.patch("/api/announcements/999999/state", json={"status": "saved", "notes": ""}).status_code
        == 404
    )

    stats = api_client.get("/api/stats").json()
    assert stats["total_active"] == 2
    assert stats["eligible_count"] == 1
    assert stats["review_count"] == 1
    assert stats["ineligible_count"] == 0
    assert stats["saved_count"] == 1
    assert stats["dismissed_count"] == 1
    assert stats["deadline_soon_count"] == 1


def test_nitelik_kodlari_search(api_client: TestClient):
    resp = api_client.get("/api/nitelik-kodlari", params={"q": "4001"})
    assert resp.status_code == 200
    items = resp.json()
    assert any(item["code"] == "4001" for item in items)


def test_custom_sources_crud_and_duplicate_409(api_client: TestClient):
    create_resp = api_client.post(
        "/api/custom-sources",
        json={
            "name": "TÜBİTAK İlanlar",
            "url": "https://kariyer.tubitak.gov.tr/",
            "keywords": ["mühendis", "uzman"],
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "TÜBİTAK İlanlar"
    src_id = created["id"]

    # Duplicate URL -> 409 Conflict
    dup_resp = api_client.post(
        "/api/custom-sources",
        json={
            "name": "TÜBİTAK Tekrar",
            "url": "https://kariyer.tubitak.gov.tr/",
            "keywords": [],
        },
    )
    assert dup_resp.status_code == 409

    list_resp = api_client.get("/api/custom-sources")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    del_resp = api_client.delete(f"/api/custom-sources/{src_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    assert api_client.delete(f"/api/custom-sources/{src_id}").status_code == 404


def test_ics_calendar_export_utf8(api_client: TestClient):
    _configure_profile(api_client)
    resp = api_client.get("/api/announcements/export/ics")
    assert resp.status_code == 200
    assert "text/calendar" in resp.headers["content-type"]

    body = resp.content.decode("utf-8")
    assert "BEGIN:VCALENDAR" in body
    assert "VERSION:2.0" in body
    assert "BEGIN:VEVENT" in body
    assert "Gençlik ve Spor Bakanlığı" in body
    assert "END:VCALENDAR" in body


def test_spa_root_serves_html_when_dist_exists(api_client: TestClient):
    dist_index = config.FRONTEND_DIST_DIR / "index.html"
    if not dist_index.is_file():
        pytest.skip("frontend/dist/index.html henüz derlenmemiş")

    resp = api_client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "<html" in resp.text.lower()


def test_institutions_catalog_endpoint(api_client: TestClient):
    resp = api_client.get("/api/institutions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 163
    groups = {g["group_key"]: g for g in data["groups"]}
    assert set(groups.keys()) == {
        "bakanliklar",
        "kamu_kurumlari",
        "yargi_kurullar",
        "kitler",
        "belediyeler",
        "il_belediyeleri",
        "universiteler",
    }
    assert groups["bakanliklar"]["count"] == 15
    assert groups["kamu_kurumlari"]["count"] == 22
    assert groups["yargi_kurullar"]["count"] == 13
    assert groups["kitler"]["count"] == 22
    assert groups["belediyeler"]["count"] == 28
    assert groups["il_belediyeleri"]["count"] == 44
    assert groups["universiteler"]["count"] == 19
    assert len(groups["il_belediyeleri"]["items"]) == 44
    assert all("name" in item and "url" in item and "city" in item for item in groups["il_belediyeleri"]["items"])


def test_scrape_trigger_async_endpoint(api_client: TestClient):
    # Unknown source returns 200 with started=False (verifies async endpoint does not 500 on event loop)
    resp = api_client.post("/api/scrape/trigger", json={"source": "nonexistent_source"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["started"] is False
    assert "nonexistent_source" in data["message"]


def test_manual_import_text_and_dedup(api_client: TestClient):
    _configure_profile(api_client)
    payload = {
        "title": "12 Büro Personeli Alım İlanı",
        "institution": "Çalışma ve Sosyal Güvenlik Bakanlığı",
        "url": "https://isealimkariyerkapisi.cbiko.gov.tr/ilan/98765",
        "raw_text": (
            "KPSS P3 puan türünden en az 70 puan almış olmak. "
            "4001 herhangi bir lisans programından mezun olmak. Son başvuru tarihi: 20.12.2026."
        ),
    }
    r1 = api_client.post("/api/announcements/import", json=payload)
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["institution"] == "Çalışma ve Sosyal Güvenlik Bakanlığı"
    assert d1["match"]["match_status"] == "eligible"
    assert "4001" in d1["extracted"]["qualification_codes"]

    # Re-importing the exact same announcement deduplicates into the existing record ID
    r2 = api_client.post("/api/announcements/import", json=payload)
    assert r2.status_code == 201
    assert r2.json()["id"] == d1["id"]

    # Blank title/raw_text -> 400 or 422
    r_bad = api_client.post(
        "/api/announcements/import",
        json={"title": "  ", "institution": "Kurum", "url": "", "raw_text": ""},
    )
    assert r_bad.status_code in (400, 422)


def test_manual_import_pdf_and_invalid_file(api_client: TestClient):
    _configure_profile(api_client)
    minimal_pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    resp = api_client.post(
        "/api/announcements/import-pdf",
        files={"file": ("iskur_kurumdisi_2026.pdf", minimal_pdf, "application/pdf")},
        data={
            "title": "İŞKUR Kurumdışı 5 Personel Alım İlanı",
            "institution": "Lüleburgaz Belediyesi",
            "url": "https://www.iskur.gov.tr/",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["institution"] == "Lüleburgaz Belediyesi"
    # Minimal/scanned PDF without extractable text triggers zero-miss 'review'
    assert data["match"]["match_status"] == "review"

    # Non-PDF upload returns 400
    bad_resp = api_client.post(
        "/api/announcements/import-pdf",
        files={"file": ("notlar.txt", b"duz metin icerik", "text/plain")},
    )
    assert bad_resp.status_code == 400
