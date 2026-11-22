"""Unit and integration tests for KPSS Radar NLP extractor, deduplicator, and zero-miss matcher."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import database
from app.engine.deduplicator import (
    compute_dedup_key,
    find_matching_existing_id,
    merge_announcement_records,
)
from app.engine.extractor import TURKISH_PROVINCES, extract_criteria
from app.engine.matcher import evaluate_match
from app.scrapers.base import (
    RawAnnouncement,
    infer_category,
    is_cancelled_announcement_title,
)
from app.scrapers.osym import _is_relevant_osym_title


def _make_raw(
    *,
    source_name: str = "sbb_kamuilan",
    source_label: str = "SBB Kamu İlan",
    external_id: str = "ext-1",
    url: str = "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=1",
    title: str = "Sözleşmeli Personel Alım İlanı",
    institution: str = "Örnek Kamu Kurumu",
    category: str = "sozlesmeli_4b",
    publish_date: str | None = "2026-11-20",
    deadline_date: str | None = None,
    city: str | None = None,
    quota_count: int | None = None,
    raw_text: str = "",
    pdf_url: str | None = None,
    application_channel: str | None = None,
) -> RawAnnouncement:
    return RawAnnouncement(
        source_name=source_name,
        source_label=source_label,
        external_id=external_id,
        url=url,
        title=title,
        institution=institution,
        category=category,
        publish_date=publish_date,
        deadline_date=deadline_date,
        city=city,
        quota_count=quota_count,
        raw_text=raw_text,
        pdf_url=pdf_url,
        application_channel=application_channel,
    )


def _configured_profile(**overrides) -> dict:
    profile = {
        "is_configured": True,
        "full_name": "Test Aday",
        "kpss_year": 2026,
        "education_level": "lisans",
        "scores": {
            "P3": 84.5,
            "P93": None,
            "P94": None,
            "P1": None,
            "P2": None,
            "P10": None,
            "P121": None,
            "EKPSS": None,
            "YDS": 70.0,
        },
        "departments": ["Bilgisayar Mühendisliği"],
        "qualification_codes": ["4001", "4531"],
        "birth_year": 1998,
        "preferred_cities": [],
        "all_cities": True,
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "kpss_a", "isci", "akademik", "sydv"],
        "include_no_kpss": True,
    }
    profile.update(overrides)
    return profile


# ---------------------------------------------------------------------------
# 1. EXTRACTOR TESTS
# ---------------------------------------------------------------------------


class TestExtractor:
    def test_extracts_kpss_types_min_score_and_4001_lisans(self):
        raw = _make_raw(
            title="181 Sözleşmeli Personel Alım İlanı",
            institution="Adli Tıp Kurumu Başkanlığı",
            raw_text=(
                "2026 yılı KPSS (B) grubu P3, P93 ve P94 puan türlerinden en az 70,5 puan almış olmak. "
                "Nitelik kodu: 4001 herhangi bir lisans programından mezun olmak. "
                "Başvurular Kariyer Kapısı (isealimkariyerkapisi.cbiko.gov.tr) üzerinden yapılacaktır. "
                "Son başvuru tarihi: 05.12.2026. Adayların 35 yaşını doldurmamış olması gerekir. "
                "Görev yeri İstanbul ve Ankara illeridir."
            ),
            pdf_url="https://kamuilan.sbb.gov.tr/ilan.pdf",
        )
        ext = extract_criteria(raw)

        assert "P3" in ext["kpss_types"]
        assert "P93" in ext["kpss_types"]
        assert "P94" in ext["kpss_types"]
        assert ext["min_score"] == 70.5
        assert ext["requires_kpss"] is True
        assert "4001" in ext["qualification_codes"]
        assert ext["accepts_any_department"] is True
        assert "lisans" in ext["education_levels"]
        assert ext["max_age"] == 35
        assert ext["quota_count"] == 181
        assert ext["deadline_date"] == "2026-12-05"
        assert ext["application_channel"] == "Kariyer Kapısı"
        assert ext["has_pdf"] is True
        assert "İstanbul" in ext["cities"]
        assert "Ankara" in ext["cities"]

    def test_extracts_3001_and_2001_qualification_codes(self):
        raw_onlisans = _make_raw(
            title="30 Büro Personeli Alımı",
            raw_text="3001 nitelik kodu ile önlisans mezunu KPSS P93 en az 65 puan şartı aranır.",
        )
        ext_onl = extract_criteria(raw_onlisans)
        assert "3001" in ext_onl["qualification_codes"]
        assert ext_onl["accepts_any_department"] is True
        assert "onlisans" in ext_onl["education_levels"]
        assert "P93" in ext_onl["kpss_types"]
        assert ext_onl["min_score"] == 65.0

        raw_orta = _make_raw(
            title="12 Destek Personeli Alımı",
            raw_text="Nitelik kodu: 2001 ortaöğretim lise mezunu KPSSP94 en az 60 puan.",
        )
        ext_ort = extract_criteria(raw_orta)
        assert "2001" in ext_ort["qualification_codes"]
        assert ext_ort["accepts_any_department"] is True
        assert "ortaogretim" in ext_ort["education_levels"]
        assert "P94" in ext_ort["kpss_types"]
        assert ext_ort["min_score"] == 60.0

    def test_extracts_no_kpss_requirement(self):
        raw = _make_raw(
            title="25 Daimi İşçi Alım İlanı",
            institution="Türkiye Kömür İşletmeleri Kurumu",
            category="isci",
            raw_text=(
                "Adaylardan KPSS şartı aranmamaktadır. Başvurular İŞKUR esube üzerinden alınacaktır. "
                "30 yaşını aşmamış olmak şarttır."
            ),
        )
        ext = extract_criteria(raw)
        assert ext["requires_kpss"] is False
        assert ext["max_age"] == 30
        assert ext["quota_count"] == 25
        assert ext["application_channel"] == "İŞKUR"

    def test_extracts_osym_ais_channel_and_turkish_word_age(self):
        raw = _make_raw(
            title="KPSS-2026/2 Merkezi Yerleştirme Tercih Kılavuzu",
            institution="ÖSYM Başkanlığı",
            category="merkezi_atama",
            raw_text=(
                "Tercih işlemleri ÖSYM AİS (ais.osym.gov.tr) üzerinden yapılacaktır. "
                "Otuz beş yaşını doldurmamış adaylar başvurabilir. Türkiye Geneli 81 il kadroları."
            ),
        )
        ext = extract_criteria(raw)
        assert ext["application_channel"] == "ÖSYM AİS"
        assert ext["max_age"] == 35
        assert ext["cities"][0] == "Türkiye Geneli"

    def test_extracts_relative_deadline_15_gun_icinde(self):
        raw = _make_raw(
            publish_date="2026-11-10",
            raw_text=(
                "Başvurular ilanın Resmî Gazete'de yayımlandığı tarihten itibaren 15 gün içinde "
                "kurum adresine şahsen yapılacaktır."
            ),
        )
        ext = extract_criteria(raw)
        assert ext["publish_date"] == "2026-11-10"
        assert ext["deadline_date"] == "2026-11-25"

    def test_extracts_turkish_month_date_range(self):
        raw = _make_raw(
            publish_date="2026-11-18",
            raw_text="Başvurular 20 Kasım - 5 Aralık 2026 tarihleri arasında alınacaktır.",
        )
        ext = extract_criteria(raw)
        assert ext["deadline_date"] == "2026-12-05"

    def test_all_81_turkish_provinces_detected(self):
        assert len(TURKISH_PROVINCES) == 81
        for province in TURKISH_PROVINCES:
            raw = _make_raw(
                title=f"{province} Personel Alım İlanı",
                institution=f"{province} İl Özel İdaresi",
                raw_text=f"Görev yeri {province} ili merkez teşkilatıdır.",
            )
            ext = extract_criteria(raw)
            assert province in ext["cities"], f"{province} il listesinde tespit edilemedi"

    def test_academic_forces_lisans_only_and_no_kpss(self):
        raw = _make_raw(
            title="Öğretim Üyesi ve Öğretim Görevlisi Alım İlanı",
            institution="Bartın Üniversitesi Rektörlüğü",
            category="akademik",
            raw_text=(
                "Üniversitemiz Meslek Yüksekokulu bünyesine öğretim görevlisi alınacaktır. "
                "ALES en az 70 puan şartı aranır."
            ),
        )
        ext = extract_criteria(raw)
        assert ext["education_levels"] == ["lisans"]
        assert ext["requires_kpss"] is False

    def test_kpss_a_adds_lisans_and_extracts_birth_year_cutoff(self):
        raw = _make_raw(
            title="100 Denetmen Yardımcısı Giriş Sınavı İlanı",
            institution="Sosyal Güvenlik Kurumu Başkanlığı",
            category="kpss_a",
            raw_text=(
                "KPSS P48 puan türünden en az 75 puan almış olmak. "
                "01 Ocak 1991 ve sonrası doğumlu olmak şarttır."
            ),
        )
        ext = extract_criteria(raw)
        assert "lisans" in ext["education_levels"]
        expected_age = datetime.date.today().year - 1991
        assert ext["max_age"] == expected_age

    def test_central_institution_city_and_clean_turkish_summary(self):
        # 1) Sayıştay without explicit city in text -> defaults to Ankara
        raw_sayistay = _make_raw(
            title="16 Sözleşmeli Personel Alacak",
            institution="Sayıştay Başkanlığı",
            deadline_date="2026-11-25",
            raw_text="KPSS P3 puan türünden en az 70 puan almış 16 sözleşmeli personel alınacaktır.",
        )
        ext1 = extract_criteria(raw_sayistay)
        assert ext1["cities"] == ["Ankara"]
        assert "16 kişilik 16 " not in ext1["summary"]
        assert "25 Kasım 2026" in ext1["summary"]

        # 2) Merkez ve taşra teşkilatı -> Türkiye Geneli
        raw_tasra = _make_raw(
            title="100 Memur Alım İlanı",
            institution="Ticaret Bakanlığı",
            raw_text="Bakanlığımız merkez ve taşra teşkilatı birimlerine memur alınacaktır.",
        )
        ext2 = extract_criteria(raw_tasra)
        assert ext2["cities"][0] == "Türkiye Geneli"


# ---------------------------------------------------------------------------
# 2. DEDUPLICATOR TESTS
# ---------------------------------------------------------------------------


class TestDeduplicator:
    def test_compute_dedup_key_normalizes_turkish_chars_and_suffixes(self):
        k1 = compute_dedup_key(
            "Adli Tıp Kurumu Başkanlığı",
            "181 Sözleşmeli Personel Alım İlanı",
            "2026-11-20",
        )
        k2 = compute_dedup_key(
            "ADLİ TIP KURUMU BAŞKANLIĞINDAN",
            "181 Sozlesmeli Personel Alimi",
            "2026-11-21",
        )
        assert k1 == k2

    def test_cross_source_deduplication_and_merge_preserves_all_3_sources(self, tmp_path):
        db_file = tmp_path / "dedup_test.db"
        database.init_db(db_path=db_file)

        items = [
            {
                "source_name": "sbb_kamuilan",
                "source_label": "SBB Kamu İlan",
                "external_id": "sbb-181",
                "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=181",
                "pdf_url": "https://kamuilan.sbb.gov.tr/dosya/181.pdf",
                "title": "181 Sözleşmeli Personel Alım İlanı",
                "institution": "Adli Tıp Kurumu Başkanlığı",
                "category": "sozlesmeli_4b",
                "city": "İstanbul",
                "cities": ["İstanbul"],
                "publish_date": "2026-11-20",
                "deadline_date": "2026-12-06",
                "quota_count": 181,
                "raw_text": "SBB metin kısa",
                "summary": "181 sözleşmeli personel alınacaktır.",
                "extracted": {
                    "kpss_types": ["P3"],
                    "min_score": 70.0,
                    "requires_kpss": True,
                    "education_levels": ["lisans"],
                    "departments": [],
                    "accepts_any_department": True,
                    "qualification_codes": ["4001"],
                    "max_age": 35,
                    "cities": ["İstanbul"],
                    "has_pdf": True,
                },
            },
            {
                "source_name": "memurlar_net",
                "source_label": "Memurlar.net İlanlar",
                "external_id": "mn-181",
                "url": "https://ilan.memurlar.net/ilan/181/adli-tip-181-personel",
                "pdf_url": None,
                "title": "Adli Tıp Kurumu 181 Sözleşmeli Personel Alıyor",
                "institution": "Adli Tip Kurumu",
                "category": "sozlesmeli_4b",
                "city": "Ankara",
                "cities": ["Ankara"],
                "publish_date": "2026-11-20",
                "deadline_date": "2026-12-06",
                "quota_count": 181,
                "raw_text": "Memurlar.net detaylı metin " + ("x" * 200),
                "summary": "Adli Tıp Kurumu 181 sözleşmeli personel ilanı.",
                "extracted": {
                    "kpss_types": ["P93", "P94"],
                    "min_score": None,
                    "requires_kpss": True,
                    "education_levels": ["onlisans", "ortaogretim"],
                    "departments": ["Büro Yönetimi"],
                    "accepts_any_department": False,
                    "qualification_codes": [],
                    "max_age": None,
                    "cities": ["Ankara"],
                    "has_pdf": False,
                },
            },
            {
                "source_name": "resmi_gazete",
                "source_label": "T.C. Resmî Gazete",
                "external_id": "rg-181",
                "url": "https://www.resmigazete.gov.tr/ilanlar/eski/2026/11/20261121-4.htm",
                "pdf_url": None,
                "title": "181 Sözleşmeli Personel Alım İlanı",
                "institution": "ADLİ TIP KURUMU BAŞKANLIĞINDAN",
                "category": "sozlesmeli_4b",
                "city": None,
                "cities": [],
                "publish_date": "2026-11-21",
                "deadline_date": "2026-12-06",
                "quota_count": 181,
                "raw_text": "Resmi Gazete tam metin.",
                "summary": "Resmi Gazete ilanı.",
                "extracted": {
                    "kpss_types": ["P3"],
                    "min_score": 70.0,
                    "requires_kpss": True,
                    "education_levels": ["lisans"],
                    "departments": [],
                    "accepts_any_department": False,
                    "qualification_codes": [],
                    "max_age": 35,
                    "cities": [],
                    "has_pdf": False,
                },
            },
        ]

        res = database.upsert_announcements(items, db_path=db_file)
        assert res["inserted"] == 1
        assert res["updated"] == 2

        rows = database.list_announcements(db_path=db_file)
        assert len(rows) == 1
        merged = rows[0]

        source_names = {s["source_name"] for s in merged["sources"]}
        assert source_names == {"sbb_kamuilan", "memurlar_net", "resmi_gazete"}
        source_urls = {s["url"] for s in merged["sources"]}
        assert "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=181" in source_urls
        assert "https://ilan.memurlar.net/ilan/181/adli-tip-181-personel" in source_urls
        assert "https://www.resmigazete.gov.tr/ilanlar/eski/2026/11/20261121-4.htm" in source_urls

        assert set(merged["extracted"]["kpss_types"]) >= {"P3", "P93", "P94"}
        assert merged["extracted"]["min_score"] == 70.0
        assert merged["extracted"]["accepts_any_department"] is True
        assert merged["extracted"]["has_pdf"] is True
        assert "İstanbul" in merged["cities"]
        assert "Ankara" in merged["cities"]

    def test_find_matching_and_merge_helpers_directly(self):
        existing = {
            "id": 42,
            "dedup_key": compute_dedup_key("Hazine ve Maliye Bakanlığı", "50 Müfettiş Yardımcısı", "2026-11-15"),
            "title": "50 Müfettiş Yardımcısı Alım İlanı",
            "institution": "Hazine ve Maliye Bakanlığı",
            "category": "kpss_a",
            "publish_date": "2026-11-15",
            "deadline_date": "2026-12-01",
            "quota_count": 50,
            "raw_text": "Kısa metin",
            "extracted": {"kpss_types": ["P48"], "min_score": 80.0},
            "sources": [
                {
                    "source_name": "sbb_kamuilan",
                    "source_label": "SBB Kamu İlan",
                    "url": "https://kamuilan.sbb.gov.tr/1",
                }
            ],
        }
        incoming = {
            "title": "Hazine ve Maliye Bakanlığı 50 Müfettiş Yardımcısı Alımı",
            "institution": "Hazine ve Maliye Bakanligi",
            "publish_date": "2026-11-16",
            "deadline_date": "2026-12-01",
            "quota_count": 50,
            "raw_text": "Detaylı metin " * 30,
            "extracted": {"kpss_types": ["P48"], "min_score": 80.0, "max_age": 35},
            "sources": [
                {
                    "source_name": "resmi_gazete",
                    "source_label": "T.C. Resmî Gazete",
                    "url": "https://www.resmigazete.gov.tr/1",
                }
            ],
        }
        matched_id = find_matching_existing_id(incoming, [existing])
        assert matched_id == 42

        merged = merge_announcement_records(existing, incoming)
        assert len(merged["sources"]) == 2
        assert merged["extracted"]["max_age"] == 35
        assert len(merged["raw_text"]) > len(existing["raw_text"])

    def test_rejects_false_merges_and_same_source_but_merges_bartin_variants(self):
        gebze = {
            "id": 1,
            "dedup_key": compute_dedup_key("Gebze Teknik Üniversitesi", "10 Sözleşmeli Personel", "2026-11-20"),
            "title": "10 Sözleşmeli Personel Alım İlanı",
            "institution": "Gebze Teknik Üniversitesi",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-05",
            "quota_count": 10,
            "sources": [{"source_name": "sbb_kamuilan", "url": "https://kamuilan.sbb.gov.tr/g"}],
        }
        erzurum = {
            "source_name": "resmi_gazete",
            "title": "10 Sözleşmeli Personel Alım İlanı",
            "institution": "Erzurum Teknik Üniversitesi",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-05",
            "quota_count": 10,
            "url": "https://www.resmigazete.gov.tr/e",
        }
        assert find_matching_existing_id(erzurum, [gebze]) is None

        bartin_sbb = {
            "id": 2,
            "dedup_key": compute_dedup_key("BARTIN ÜNİVERSİTESİ", "15 Sözleşmeli Personel", "2026-11-20"),
            "title": "15 Sözleşmeli Personel Alım İlanı",
            "institution": "BARTIN ÜNİVERSİTESİ",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-05",
            "quota_count": 15,
            "sources": [{"source_name": "sbb_kamuilan", "url": "https://kamuilan.sbb.gov.tr/b"}],
        }
        bayburt_rg = {
            "source_name": "resmi_gazete",
            "title": "15 Sözleşmeli Personel Alım İlanı",
            "institution": "Bayburt Üniversitesi",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-05",
            "quota_count": 15,
            "url": "https://www.resmigazete.gov.tr/bayburt",
        }
        assert find_matching_existing_id(bayburt_rg, [bartin_sbb]) is None

        # Same source must never merge even if institution/title match closely
        bartin_same_source = {
            "source_name": "sbb_kamuilan",
            "title": "15 Sözleşmeli Personel Alım İlanı",
            "institution": "Bartın Üniversitesi Rektörlüğü",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-05",
            "quota_count": 15,
            "url": "https://kamuilan.sbb.gov.tr/b2",
        }
        assert find_matching_existing_id(bartin_same_source, [bartin_sbb]) is None

        # Cross-source Bartın variant MUST merge
        bartin_rg = {
            "source_name": "resmi_gazete",
            "title": "15 Sözleşmeli Personel Alım İlanı",
            "institution": "Bartın Üniversitesi Rektörlüğü",
            "category": "sozlesmeli_4b",
            "publish_date": "2026-11-21",
            "deadline_date": "2026-12-05",
            "quota_count": 15,
            "url": "https://www.resmigazete.gov.tr/bartin",
        }
        assert find_matching_existing_id(bartin_rg, [bartin_sbb]) == 2

    def test_merge_deduplicates_source_name_and_protects_official_primary_data(self):
        # 1) SBB re-encrypted ?kod= URL on re-scrape keeps only 1 sbb_kamuilan badge
        ex_sbb = {
            "id": 10,
            "title": "10 Memur Alım İlanı",
            "institution": "Ticaret Bakanlığı",
            "category": "memur",
            "publish_date": "2026-11-20",
            "deadline_date": None,
            "raw_text": (
                "T.C. Ticaret Bakanlığı Resmi SBB PDF metni: 2026 yılı KPSS P3 puan türünden "
                "en az 70 puan almış olmak, 4001 herhangi bir lisans programından mezun olmak."
            ),
            "summary": "Ticaret Bakanlığı 10 memur alımı.",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 70.0,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
                "qualification_codes": ["4001"],
                "cities": ["Ankara"],
            },
            "sources": [
                {
                    "source_name": "sbb_kamuilan",
                    "source_label": "SBB Kamu İlan",
                    "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=OLD",
                    "pdf_url": "https://kamuilan.sbb.gov.tr/pdf/old.pdf",
                    "scraped_at": "2026-11-20T10:00:00",
                }
            ],
        }
        in_sbb_refresh = {
            **ex_sbb,
            "sources": [
                {
                    "source_name": "sbb_kamuilan",
                    "source_label": "SBB Kamu İlan",
                    "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=NEW",
                    "pdf_url": None,
                    "scraped_at": "2026-11-22T12:00:00",
                }
            ],
        }
        merged_sbb = merge_announcement_records(ex_sbb, in_sbb_refresh)
        assert len(merged_sbb["sources"]) == 1
        assert merged_sbb["sources"][0]["url"].endswith("kod=NEW")
        assert merged_sbb["sources"][0]["pdf_url"] == "https://kamuilan.sbb.gov.tr/pdf/old.pdf"

        # 2) Secondary aggregator (isinolsa) must NOT overwrite official SBB title/raw_text/extracted
        in_isinolsa = {
            "source_name": "isinolsa",
            "title": "Ticaret Bakanlığı 10 Memur Alımı Başvuruları Başladı! İşte Detaylar",
            "institution": "Ticaret Bakanlığı",
            "category": "memur",
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-08",
            "cities": ["İstanbul"],
            "raw_text": "İşin Olsa uzun haber metni " + ("detay " * 80),
            "summary": "Uzun haber özeti.",
            "extracted": {
                "kpss_types": ["P93"],
                "min_score": 55.0,
                "education_levels": ["onlisans"],
                "accepts_any_department": False,
                "qualification_codes": [],
                "cities": ["İstanbul"],
            },
            "sources": [
                {
                    "source_name": "isinolsa",
                    "source_label": "İşin Olsa Kamu Alımları",
                    "url": "https://www.isinolsa.com/ticaret-10-memur/",
                    "scraped_at": "2026-11-22T12:30:00",
                }
            ],
        }
        merged_sec = merge_announcement_records(ex_sbb, in_isinolsa)
        assert {s["source_name"] for s in merged_sec["sources"]} == {"sbb_kamuilan", "isinolsa"}
        assert merged_sec["title"] == "10 Memur Alım İlanı"
        assert "Resmi SBB PDF metni" in merged_sec["raw_text"]
        assert merged_sec["extracted"]["min_score"] == 70.0
        assert merged_sec["deadline_date"] == "2026-12-08"


# ---------------------------------------------------------------------------
# 3. MATCHER TESTS (Zero-Miss 3-Tier Engine)
# ---------------------------------------------------------------------------


class TestMatcher:
    def test_unconfigured_profile_returns_review_score_50(self):
        profile = {"is_configured": False}
        ann = {
            "category": "memur",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 95.0,
                "education_levels": ["ortaogretim"],
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "review"
        assert res["match_score"] == 50

    def test_eligible_when_max_age_none_and_p3_lisans_4001_match(self):
        profile = _configured_profile(
            education_level="lisans",
            scores={"P3": 84.5},
            qualification_codes=["4001"],
        )
        ann = {
            "category": "memur",
            "cities": ["Ankara"],
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
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "eligible"
        assert res["match_score"] >= 80
        statuses = {r["field"]: r["status"] for r in res["reasons"]}
        assert statuses["education"] == "pass"
        assert statuses["kpss_score"] == "pass"
        assert statuses["department"] == "pass"
        assert statuses["age"] == "pass"

    def test_missing_or_ambiguous_criteria_returns_review_never_ineligible(self):
        profile = _configured_profile()
        ann = {
            "category": "sozlesmeli_4b",
            "extracted": {
                "kpss_types": [],
                "min_score": None,
                "requires_kpss": None,
                "education_levels": [],
                "departments": [],
                "accepts_any_department": False,
                "qualification_codes": [],
                "max_age": None,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "review"
        assert all(r["status"] != "fail" for r in res["reasons"])

    def test_multi_cadre_or_pdf_department_mismatch_stays_review_zero_miss(self):
        profile = _configured_profile(
            departments=["Bilgisayar Mühendisliği"],
            qualification_codes=["4531"],
        )
        ann = {
            "category": "sozlesmeli_4b",
            "quota_count": 45,
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 70.0,
                "requires_kpss": True,
                "education_levels": ["lisans", "onlisans"],
                "departments": ["Hemşirelik", "Büro Yönetimi"],
                "accepts_any_department": False,
                "qualification_codes": [],
                "max_age": 35,
                "has_pdf": True,
                "quota_count": 45,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "review"
        dept_reason = next(r for r in res["reasons"] if r["field"] == "department")
        assert dept_reason["status"] == "warn"

    def test_ineligible_on_low_kpss_score(self):
        profile = _configured_profile(scores={"P3": 72.0})
        ann = {
            "category": "memur",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 80.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "ineligible"
        kpss_reason = next(r for r in res["reasons"] if r["field"] == "kpss_score")
        assert kpss_reason["status"] == "fail"
        assert "altında" in kpss_reason["message"]

    def test_ineligible_on_incompatible_single_education_level(self):
        profile = _configured_profile(education_level="lisans")
        ann = {
            "category": "sozlesmeli_4b",
            "extracted": {
                "kpss_types": ["P94"],
                "min_score": 65.0,
                "requires_kpss": True,
                "education_levels": ["ortaogretim"],
                "accepts_any_department": True,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "ineligible"
        edu_reason = next(r for r in res["reasons"] if r["field"] == "education")
        assert edu_reason["status"] == "fail"
        assert "Ortaöğretim" in edu_reason["message"]

    def test_ineligible_on_exceeded_age_limit(self):
        current_year = datetime.date.today().year
        profile = _configured_profile(birth_year=current_year - 34)
        ann = {
            "category": "kpss_a",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 75.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
                "max_age": 30,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "ineligible"
        age_reason = next(r for r in res["reasons"] if r["field"] == "age")
        assert age_reason["status"] == "fail"
        assert "30" in age_reason["message"]

    def test_ineligible_on_narrow_single_department_mismatch(self):
        profile = _configured_profile(
            departments=["Bilgisayar Mühendisliği"],
            qualification_codes=["4531"],
        )
        ann = {
            "category": "sozlesmeli_4b",
            "quota_count": 1,
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 70.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "departments": ["Tıp"],
                "accepts_any_department": False,
                "qualification_codes": [],
                "has_pdf": False,
                "quota_count": 1,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "ineligible"
        dept_reason = next(r for r in res["reasons"] if r["field"] == "department")
        assert dept_reason["status"] == "fail"
        assert "Tıp" in dept_reason["message"]

    def test_ineligible_when_category_excluded_in_profile(self):
        profile = _configured_profile(preferred_categories=["memur", "sozlesmeli_4b"])
        ann = {
            "category": "akademik",
            "extracted": {
                "requires_kpss": False,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
                "max_age": None,
            },
        }
        res = evaluate_match(ann, profile)
        assert res["match_status"] == "ineligible"
        cat_reason = next(r for r in res["reasons"] if r["field"] == "category")
        assert cat_reason["status"] == "fail"

    def test_onlisans_profile_marks_academic_and_kpss_a_ineligible(self):
        onlisans_profile = _configured_profile(
            education_level="onlisans",
            scores={"P3": None, "P93": 72.0},
            departments=["Dış Ticaret"],
            qualification_codes=["3001"],
        )

        # 1) Academic announcement mentioning "Meslek Yüksekokulu" -> lisans only, ineligible for onlisans
        raw_acad = _make_raw(
            title="Öğretim Üyesi ve Öğretim Görevlisi Alım İlanı",
            institution="Bartın Üniversitesi Rektörlüğü",
            category="akademik",
            raw_text="Meslek Yüksekokulu bünyesine öğretim görevlisi alınacaktır. ALES en az 70 puan.",
        )
        ext_acad = extract_criteria(raw_acad)
        res_acad = evaluate_match({"category": "akademik", "extracted": ext_acad}, onlisans_profile)
        assert res_acad["match_status"] == "ineligible"

        # 2) KPSS-A announcement ("100 Sosyal Güvenlik Denetmen Yardımcısı") -> lisans, ineligible for onlisans
        raw_kpss_a = _make_raw(
            title="100 Sosyal Güvenlik Denetmen Yardımcısı Giriş Sınavı İlanı",
            institution="Sosyal Güvenlik Kurumu Başkanlığı",
            category="kpss_a",
            raw_text="01 Ocak 1991 ve sonrası doğumlu olmak şarttır.",
        )
        ext_kpss_a = extract_criteria(raw_kpss_a)
        assert "lisans" in ext_kpss_a["education_levels"]
        res_kpss_a = evaluate_match({"category": "kpss_a", "extracted": ext_kpss_a}, onlisans_profile)
        assert res_kpss_a["match_status"] == "ineligible"


class TestScraperFiltersAndCategories:
    def test_infer_category_4b_not_merkezi_atama(self):
        cat = infer_category(
            "Adli Tıp Kurumu 181 Sözleşmeli Personel Alım İlanı",
            "4/B sözleşmeli personel pozisyonlarına alım yapılacaktır.",
        )
        assert cat == "sozlesmeli_4b"

        osym_cat = infer_category(
            "KPSS-2026/2 Tercih Kılavuzu",
            "Bazı kamu kurum ve kuruluşlarının kadro ve pozisyonlarına ÖSYM üzerinden tercih.",
        )
        assert osym_cat == "merkezi_atama"

    def test_cancellation_title_filter(self):
        assert is_cancelled_announcement_title("İPTAL İLANI") is True
        assert is_cancelled_announcement_title("ÖĞRETİM ÜYESİ ALIMI DÜZELTME & İPTAL İLANI") is True
        assert is_cancelled_announcement_title("181 Sözleşmeli Personel Alım İlanı") is False

    def test_osym_non_recruitment_filter(self):
        assert _is_relevant_osym_title("2026-KPSS Lisans Sınava Giriş Belgeleri Erişime Açıldı", "KPSS") is False
        assert _is_relevant_osym_title("2026-KPSS Soru Kitapçığı ve Cevap Anahtarı Yayımlandı", "KPSS") is False
        assert _is_relevant_osym_title("2026-KPSS Branş Bazında Sıralamalar Güncellendi", "KPSS") is False
        assert _is_relevant_osym_title("KPSS-2026/2 Tercih Kılavuzu Yayımlandı", "KPSS") is True
