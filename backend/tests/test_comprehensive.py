"""Comprehensive stress-test matrix for KPSS Radar: 6 candidate profiles, deduplication, Turkish Unicode, and expired-deadline API guards."""

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
from app.engine.deduplicator import compute_dedup_key, find_matching_existing_id, merge_announcement_records  # noqa: E402
from app.engine.extractor import extract_criteria  # noqa: E402
from app.engine.matcher import evaluate_match  # noqa: E402
from app.scheduler import scheduler  # noqa: E402
from app.scrapers.base import RawAnnouncement, infer_category  # noqa: E402
from app.scrapers.isinolsa import _is_relevant_isinolsa_title  # noqa: E402
from app.scrapers.official_institutions import _is_candidate_link  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers & 6 Realistic Candidate Profiles
# ---------------------------------------------------------------------------


def _raw(
    *,
    source_name: str = "sbb_kamuilan",
    source_label: str = "SBB Kamu İlan",
    external_id: str = "comp-1",
    url: str = "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=999",
    title: str,
    institution: str,
    category: str | None = None,
    publish_date: str | None = "2026-11-20",
    deadline_date: str | None = "2026-12-10",
    city: str | None = None,
    quota_count: int | None = None,
    raw_text: str = "",
    pdf_url: str | None = None,
) -> RawAnnouncement:
    inferred_cat = category or infer_category(title, raw_text)
    return RawAnnouncement(
        source_name=source_name,
        source_label=source_label,
        external_id=external_id,
        url=url,
        title=title,
        institution=institution,
        category=inferred_cat,
        publish_date=publish_date,
        deadline_date=deadline_date,
        city=city,
        quota_count=quota_count,
        raw_text=raw_text,
        pdf_url=pdf_url,
    )


def _eval_raw(raw: RawAnnouncement, profile: dict) -> tuple[dict, dict]:
    ext = extract_criteria(raw)
    ann = {
        "category": raw.category,
        "city": raw.city,
        "cities": ext["cities"],
        "quota_count": ext["quota_count"],
        "extracted": ext,
    }
    return ext, evaluate_match(ann, profile)


PROFILES: dict[str, dict] = {
    "onlisans_dis_ticaret": {
        "is_configured": True,
        "full_name": "Önlisans Aday",
        "education_level": "onlisans",
        "scores": {"P93": 72.0},
        "departments": ["Dış Ticaret"],
        "qualification_codes": ["3001"],
        "birth_year": 2004,
        "all_cities": True,
        "preferred_cities": [],
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "kpss_a", "isci", "sydv"],
        "include_no_kpss": True,
    },
    "lisans_muhendis": {
        "is_configured": True,
        "full_name": "Mühendis Aday",
        "education_level": "lisans",
        "scores": {"P3": 84.5},
        "departments": ["Bilgisayar Mühendisliği"],
        "qualification_codes": ["4001", "4531"],
        "birth_year": 1998,
        "all_cities": True,
        "preferred_cities": [],
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "kpss_a", "isci", "sydv"],
        "include_no_kpss": True,
    },
    "lisans_iibf_kpss_a": {
        "is_configured": True,
        "full_name": "İİBF A+B Aday",
        "education_level": "lisans",
        "scores": {"P3": 81.0, "P48": 82.0, "P1": 79.0},
        "departments": ["İktisat"],
        "qualification_codes": ["4001"],
        "birth_year": 1996,
        "all_cities": True,
        "preferred_cities": [],
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "kpss_a", "isci", "sydv"],
        "include_no_kpss": True,
    },
    "ortaogretim_lise": {
        "is_configured": True,
        "full_name": "Lise Aday",
        "education_level": "ortaogretim",
        "scores": {"P94": 78.0},
        "departments": [],
        "qualification_codes": ["2001"],
        "birth_year": 2003,
        "all_cities": True,
        "preferred_cities": [],
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "isci", "sydv"],
        "include_no_kpss": True,
    },
    "ekpss_engelli": {
        "is_configured": True,
        "full_name": "EKPSS Aday",
        "education_level": "onlisans",
        "scores": {"EKPSS": 76.0},
        "departments": [],
        "qualification_codes": ["3001"],
        "birth_year": 1999,
        "all_cities": True,
        "preferred_cities": [],
        "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "engelli"],
        "include_no_kpss": True,
    },
    "kisitli_ankara_41yas": {
        "is_configured": True,
        "full_name": "Kısıtlı Aday",
        "education_level": "lisans",
        "scores": {"P3": 58.0},
        "departments": ["İşletme"],
        "qualification_codes": ["4001"],
        "birth_year": 1985,
        "all_cities": False,
        "preferred_cities": ["Ankara"],
        "preferred_categories": ["memur", "sozlesmeli_4b"],
        "include_no_kpss": False,
    },
}


# ---------------------------------------------------------------------------
# 1. 6-PROFILE STRESS MATRIX (ZERO-MISS & ZERO-FALSE-POSITIVE)
# ---------------------------------------------------------------------------


class TestSixProfileStressMatrix:
    def test_bartin_3001_onlisans_eligible_others_ineligible(self):
        raw = _raw(
            title="1 Sözleşmeli Büro Personeli Alım İlanı",
            institution="Bartın Üniversitesi Rektörlüğü",
            category="sozlesmeli_4b",
            quota_count=1,
            raw_text=(
                "2026 KPSS P93 puan türünden en az 65 puan almış olmak. "
                "Nitelik kodu 3001: Herhangi bir önlisans programından mezun olmak. "
                "Son başvuru tarihi: 15.12.2026."
            ),
        )
        _, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        _, res_lis = _eval_raw(raw, PROFILES["lisans_muhendis"])
        _, res_lise = _eval_raw(raw, PROFILES["ortaogretim_lise"])

        assert res_onl["match_status"] == "eligible"
        assert res_lis["match_status"] == "ineligible"
        assert res_lise["match_status"] == "ineligible"

    def test_karatay_zabita_herhangi_bir_bildirim_no_false_accepts_any(self):
        raw = _raw(
            title="Zabıta Memuru Alım İlanı",
            institution="Karatay Belediye Başkanlığı",
            category="memur",
            quota_count=3,
            city="Konya",
            raw_text=(
                "Önlisans Mahalli İdareler, Yerel Yönetimler veya Pazarlama programlarından mezun olmak. "
                "KPSS P93 puan türünden en az 65 puan almış olmak. "
                "Adaylara ayrıca herhangi bir bildirimde bulunulmayacaktır."
            ),
        )
        ext, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        assert ext["accepts_any_department"] is False
        assert res_onl["match_status"] != "eligible"
        assert res_onl["match_status"] in ("review", "ineligible")

    def test_adli_tip_181_herhangi_bir_engeli_no_false_accepts_any_and_zero_miss_review(self):
        raw = _raw(
            title="181 Sözleşmeli Personel Alım İlanı",
            institution="Adli Tıp Kurumu Başkanlığı",
            quota_count=181,
            pdf_url="https://kamuilan.sbb.gov.tr/adli-tip-181.pdf",
            raw_text=(
                "2026 KPSS P3, P93 ve P94 puan türlerinden en az 70 puan almış olmak. "
                "Hafta sonları çalışmaya herhangi bir engeli olmamak şarttır. "
                "Büro Yönetimi ve Hemşirelik bölümlerinden mezun olmak."
            ),
        )
        assert raw.category == "sozlesmeli_4b"
        ext, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        _, res_lis = _eval_raw(raw, PROFILES["lisans_muhendis"])
        _, res_lise = _eval_raw(raw, PROFILES["ortaogretim_lise"])

        assert ext["accepts_any_department"] is False
        assert res_onl["match_status"] == "review"
        assert res_lis["match_status"] == "review"
        assert res_lise["match_status"] == "review"

    def test_ula_tanoba_herhangi_bir_onlisans_programi_eligible(self):
        raw = _raw(
            title="4 Sözleşmeli Tekniker ve Büro Personeli Alımı",
            institution="Ula Belediye Başkanlığı",
            category="sozlesmeli_4b",
            quota_count=4,
            city="Muğla",
            raw_text=(
                "Herhangi bir önlisans programından mezun olmak. "
                "KPSS P93 puan türünden en az 60 puan almış olmak. 35 yaşını doldurmamış olmak."
            ),
        )
        ext, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        assert ext["accepts_any_department"] is True
        assert res_onl["match_status"] == "eligible"

    def test_sahil_guvenlik_aciktan_devlet_memuru_is_memur_not_askeri_emniyet(self):
        raw = _raw(
            title="Sahil Güvenlik Komutanlığı 10 Açıktan Devlet Memuru Temin İlanı",
            institution="Sahil Güvenlik Komutanlığı",
            quota_count=10,
            raw_text=(
                "657 sayılı Devlet Memurları Kanununa tabi açıktan devlet memuru alımı yapılacaktır. "
                "4001 herhangi bir lisans programından mezun, KPSS P3 en az 70 puan."
            ),
        )
        assert raw.category == "memur"
        _, res_lis = _eval_raw(raw, PROFILES["lisans_muhendis"])
        assert res_lis["match_status"] == "eligible"

    def test_akademik_myo_ogretim_gorevlisi_lisans_only_ineligible_for_onlisans_and_lise(self):
        raw = _raw(
            title="Öğretim Üyesi ve Öğretim Görevlisi Alım İlanı",
            institution="Atatürk Üniversitesi Rektörlüğü",
            raw_text=(
                "Üniversitemiz Meslek Yüksekokulu bünyesine öğretim görevlisi alınacaktır. "
                "ALES en az 70 puan şartı aranmaktadır."
            ),
        )
        assert raw.category == "akademik"
        ext, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        _, res_lise = _eval_raw(raw, PROFILES["ortaogretim_lise"])

        assert ext["education_levels"] == ["lisans"]
        assert ext["requires_kpss"] is False
        assert res_onl["match_status"] == "ineligible"
        assert res_lise["match_status"] == "ineligible"

    def test_sgk_100_denetmen_yardimcisi_kpss_a_iibf_ok_onlisans_ineligible(self):
        raw = _raw(
            title="100 Sosyal Güvenlik Denetmen Yardımcısı Giriş Sınavı İlanı",
            institution="Sosyal Güvenlik Kurumu Başkanlığı",
            quota_count=100,
            pdf_url="https://kamuilan.sbb.gov.tr/sgk-100.pdf",
            raw_text=(
                "KPSS P48 puan türünden en az 75 puan almış olmak. "
                "İktisat, İşletme, Maliye bölümlerinden mezun olmak. "
                "01 Ocak 1991 ve sonrası doğumlu olmak şarttır."
            ),
        )
        assert raw.category == "kpss_a"
        ext, res_iibf = _eval_raw(raw, PROFILES["lisans_iibf_kpss_a"])
        _, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])

        assert "lisans" in ext["education_levels"]
        assert ext["max_age"] == datetime.date.today().year - 1991
        assert res_iibf["match_status"] in ("eligible", "review")
        assert res_onl["match_status"] == "ineligible"

    def test_kisitli_aday_low_score_age_and_city_ineligible(self):
        # 1) Score too low (58 < 70)
        raw_score = _raw(
            title="10 Memur Alım İlanı",
            institution="Ticaret Bakanlığı",
            category="memur",
            city="Ankara",
            raw_text="4001 herhangi bir lisans programından mezun, KPSS P3 en az 70 puan.",
        )
        _, r_score = _eval_raw(raw_score, PROFILES["kisitli_ankara_41yas"])
        assert r_score["match_status"] == "ineligible"

        # 2) Age exceeded (41 > 35)
        raw_age = _raw(
            title="20 Memur Alımı",
            institution="Hazine ve Maliye Bakanlığı",
            category="memur",
            city="Ankara",
            raw_text="4001 herhangi bir lisans programından mezun, KPSS P3 en az 55 puan, 35 yaşını doldurmamış olmak.",
        )
        _, r_age = _eval_raw(raw_age, PROFILES["kisitli_ankara_41yas"])
        assert r_age["match_status"] == "ineligible"

        # 3) City mismatch (İstanbul != Ankara)
        raw_city = _raw(
            title="5 Sözleşmeli Personel Alımı",
            institution="Boğaziçi Üniversitesi",
            category="sozlesmeli_4b",
            city="İstanbul",
            raw_text="4001 herhangi bir lisans programından mezun, KPSS P3 en az 55 puan. Görev yeri İstanbul.",
        )
        _, r_city = _eval_raw(raw_city, PROFILES["kisitli_ankara_41yas"])
        assert r_city["match_status"] == "ineligible"

    def test_ekpss_profile_matches_engelli_announcement(self):
        raw = _raw(
            title="EKPSS-2026 Engelli Kamu Personeli Tercih Kılavuzu",
            institution="ÖSYM Başkanlığı",
            category="engelli",
            raw_text="3001 önlisans mezunu EKPSS puanı ile engelli memur alımı.",
        )
        _, res_ekpss = _eval_raw(raw, PROFILES["ekpss_engelli"])
        _, res_kisitli = _eval_raw(raw, PROFILES["kisitli_ankara_41yas"])
        assert res_ekpss["match_status"] == "eligible"
        assert res_kisitli["match_status"] == "ineligible"

    def test_scanned_pdf_empty_raw_text_never_ineligible_across_all_profiles(self):
        raw_scanned = _raw(
            title="Kamu Kurumu Sözleşmeli Personel Alım İlanı",
            institution="Devlet Su İşleri Genel Müdürlüğü",
            category="sozlesmeli_4b",
            pdf_url="https://kamuilan.sbb.gov.tr/scanned.pdf",
            raw_text="",
        )
        for name, prof in PROFILES.items():
            _, res = _eval_raw(raw_scanned, prof)
            assert res["match_status"] == "review", f"{name} için taranmış PDF review yerine {res['match_status']} döndü"

    def test_ortaogretim_2001_matches_lise_profile_only(self):
        raw = _raw(
            title="3 Destek Personeli (Hizmetli) Alım İlanı",
            institution="Amasya Valiliği",
            category="sozlesmeli_4b",
            quota_count=3,
            city="Amasya",
            raw_text="2001 nitelik kodu ile lise ortaöğretim mezunu KPSS P94 en az 70 puan.",
        )
        _, res_lise = _eval_raw(raw, PROFILES["ortaogretim_lise"])
        _, res_lisans = _eval_raw(raw, PROFILES["lisans_muhendis"])
        assert res_lise["match_status"] == "eligible"
        assert res_lisans["match_status"] == "ineligible"

    def test_no_kpss_isci_eligible_when_enabled_ineligible_when_disabled(self):
        raw = _raw(
            title="15 Daimi İşçi Alım İlanı",
            institution="Karayolları Genel Müdürlüğü",
            category="isci",
            city="Ankara",
            raw_text="KPSS şartı aranmamaktadır. İŞKUR üzerinden başvuru yapılacaktır.",
        )
        _, res_onl = _eval_raw(raw, PROFILES["onlisans_dis_ticaret"])
        _, res_kis = _eval_raw(raw, PROFILES["kisitli_ankara_41yas"])
        assert res_onl["match_status"] == "review"
        assert res_kis["match_status"] == "ineligible"

    def test_lisans_muhendis_matches_4531_specific_code(self):
        raw = _raw(
            title="2 Bilgisayar Mühendisi Sözleşmeli Personel Alımı",
            institution="Ulaştırma ve Altyapı Bakanlığı",
            category="sozlesmeli_4b",
            quota_count=2,
            city="Ankara",
            raw_text=(
                "Nitelik kodu 4531 Bilgisayar Mühendisliği lisans programından mezun olmak. "
                "KPSS P3 en az 75 puan. 35 yaşını aşmamış olmak."
            ),
        )
        _, res_muh = _eval_raw(raw, PROFILES["lisans_muhendis"])
        _, res_iibf = _eval_raw(raw, PROFILES["lisans_iibf_kpss_a"])
        assert res_muh["match_status"] == "eligible"
        assert res_iibf["match_status"] == "ineligible"


# ---------------------------------------------------------------------------
# 2. CROSS-SOURCE DEDUPLICATION STRESS TESTS (12+ PAIRS)
# ---------------------------------------------------------------------------


def _ex_record(
    *,
    rec_id: int,
    source_name: str,
    institution: str,
    title: str,
    category: str = "sozlesmeli_4b",
    quota_count: int | None = None,
    publish_date: str | None = "2026-11-20",
    deadline_date: str | None = "2026-12-06",
    url: str = "https://kamuilan.sbb.gov.tr/1",
) -> dict:
    return {
        "id": rec_id,
        "dedup_key": compute_dedup_key(institution, title, publish_date),
        "institution": institution,
        "title": title,
        "category": category,
        "quota_count": quota_count,
        "publish_date": publish_date,
        "deadline_date": deadline_date,
        "sources": [{"source_name": source_name, "url": url}],
    }


class TestDeduplicationStressPairs:
    @pytest.mark.parametrize(
        "existing_kwargs,incoming_kwargs",
        [
            # 1. Bartın + Bartın Rektörlüğü (with numeric suffix in RG title)
            (
                dict(
                    rec_id=101,
                    source_name="sbb_kamuilan",
                    institution="BARTIN ÜNİVERSİTESİ",
                    title="Bartın Üniversitesi 1 Sözleşmeli Personel Alacak",
                    quota_count=1,
                    url="https://kamuilan.sbb.gov.tr/bartin",
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="Bartın Üniversitesi Rektörlüğü",
                    title="Sözleşmeli Personel Alım İlanı (2026-04)",
                    quota_count=None,
                    publish_date="2026-11-21",
                    url="https://www.resmigazete.gov.tr/bartin",
                ),
            ),
            # 2. Bursa Teknik 1 Sözleşmeli + 1 Psikolog
            (
                dict(
                    rec_id=102,
                    source_name="memurlar_net",
                    institution="Bursa Teknik Üniversitesi",
                    title="Bursa Teknik Üniversitesi 1 sözleşmeli personel alacak",
                    quota_count=1,
                    url="https://ilan.memurlar.net/bursa-1",
                ),
                dict(
                    source_name="sbb_kamuilan",
                    institution="BURSA TEKNİK ÜNİVERSİTESİ REKTÖRLÜĞÜ",
                    title="1 SÖZLEŞMELİ PSİKOLOG ALIM İLANI",
                    quota_count=1,
                    url="https://kamuilan.sbb.gov.tr/bursa-1",
                ),
            ),
            # 3. Savunma Sanayii 26 Sözleşmeli + 26 Proje Bazlı
            (
                dict(
                    rec_id=103,
                    source_name="memurlar_net",
                    institution="Savunma Sanayii Başkanlığı",
                    title="Savunma Sanayii Başkanlığı 26 sözleşmeli personel alıyor",
                    quota_count=26,
                    url="https://ilan.memurlar.net/ssb-26",
                ),
                dict(
                    source_name="sbb_kamuilan",
                    institution="T.C. SAVUNMA SANAYİİ BAŞKANLIĞI",
                    title="26 PROJE BAZLI SÖZLEŞMELİ PERSONEL ALIM İLANI",
                    quota_count=26,
                    url="https://kamuilan.sbb.gov.tr/ssb-26",
                ),
            ),
            # 4. Yıldız Teknik 2 Sözleşmeli + 2 Bilişim Personeli
            (
                dict(
                    rec_id=104,
                    source_name="memurlar_net",
                    institution="Yıldız Teknik Üniversitesi",
                    title="Yıldız Teknik Üniversitesi 2 sözleşmeli personel alacak",
                    quota_count=2,
                    url="https://ilan.memurlar.net/ytu-2",
                ),
                dict(
                    source_name="sbb_kamuilan",
                    institution="YILDIZ TEKNİK ÜNİVERSİTESİ REKTÖRLÜĞÜ",
                    title="2 BİLİŞİM PERSONELİ ALIM İLANI",
                    quota_count=2,
                    url="https://kamuilan.sbb.gov.tr/ytu-2",
                ),
            ),
            # 5. Zafer Kalkınma Ajansı 2 Uzman + 2 Sözleşmeli
            (
                dict(
                    rec_id=105,
                    source_name="memurlar_net",
                    institution="Zafer Kalkınma Ajansı",
                    title="Zafer Kalkınma Ajansı 2 uzman personel alacak",
                    category="kpss_a",
                    quota_count=2,
                    url="https://ilan.memurlar.net/zafer-2",
                ),
                dict(
                    source_name="sbb_kamuilan",
                    institution="ZAFER KALKINMA AJANSI GENEL SEKRETERLİĞİ",
                    title="2 SÖZLEŞMELİ PERSONEL ALIM İLANI",
                    category="kpss_a",
                    quota_count=2,
                    url="https://kamuilan.sbb.gov.tr/zafer-2",
                ),
            ),
            # 6. Adli Tıp SBB + RG
            (
                dict(
                    rec_id=106,
                    source_name="sbb_kamuilan",
                    institution="Adli Tıp Kurumu Başkanlığı",
                    title="181 Sözleşmeli Personel Alım İlanı",
                    quota_count=181,
                    url="https://kamuilan.sbb.gov.tr/atk-181",
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="ADLİ TIP KURUMU BAŞKANLIĞINDAN",
                    title="181 Sözleşmeli Personel Alım İlanı",
                    quota_count=181,
                    url="https://www.resmigazete.gov.tr/atk-181",
                ),
            ),
        ],
    )
    def test_true_cross_source_pairs_merge(self, existing_kwargs, incoming_kwargs):
        ex = _ex_record(**existing_kwargs)
        inc = {
            "category": existing_kwargs.get("category", "sozlesmeli_4b"),
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-06",
            **incoming_kwargs,
        }
        assert find_matching_existing_id(inc, [ex]) == existing_kwargs["rec_id"]

    @pytest.mark.parametrize(
        "existing_kwargs,incoming_kwargs",
        [
            # 7. Gebze Teknik != Erzurum Teknik
            (
                dict(
                    rec_id=201,
                    source_name="sbb_kamuilan",
                    institution="Gebze Teknik Üniversitesi",
                    title="10 Sözleşmeli Personel Alım İlanı",
                    quota_count=10,
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="Erzurum Teknik Üniversitesi",
                    title="10 Sözleşmeli Personel Alım İlanı",
                    quota_count=10,
                    url="https://www.resmigazete.gov.tr/erzurum",
                ),
            ),
            # 8. Bartın != Bayburt
            (
                dict(
                    rec_id=202,
                    source_name="sbb_kamuilan",
                    institution="Bartın Üniversitesi",
                    title="15 Sözleşmeli Personel Alımı",
                    quota_count=15,
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="Bayburt Üniversitesi",
                    title="15 Sözleşmeli Personel Alımı",
                    quota_count=15,
                    url="https://www.resmigazete.gov.tr/bayburt",
                ),
            ),
            # 9. İstanbul Medeniyet != İstanbul Cerrahpaşa
            (
                dict(
                    rec_id=203,
                    source_name="sbb_kamuilan",
                    institution="İstanbul Medeniyet Üniversitesi",
                    title="5 Sözleşmeli Personel Alım İlanı",
                    quota_count=5,
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="İstanbul Üniversitesi-Cerrahpaşa Rektörlüğü",
                    title="5 Sözleşmeli Personel Alım İlanı",
                    quota_count=5,
                    url="https://www.resmigazete.gov.tr/cerrahpasa",
                ),
            ),
            # 10. Bayburt 8 Öğretim Elemanı != Bayburt 11 Öğretim Üyesi
            (
                dict(
                    rec_id=204,
                    source_name="sbb_kamuilan",
                    institution="Bayburt Üniversitesi Rektörlüğü",
                    title="8 Öğretim Elemanı Alım İlanı",
                    category="akademik",
                    quota_count=8,
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="Bayburt Üniversitesi Rektörlüğü",
                    title="11 Öğretim Üyesi Alım İlanı",
                    category="akademik",
                    quota_count=11,
                    url="https://www.resmigazete.gov.tr/bayburt-11",
                ),
            ),
            # 11. SGK Müfettiş != SGK Denetmen
            (
                dict(
                    rec_id=205,
                    source_name="sbb_kamuilan",
                    institution="Sosyal Güvenlik Kurumu Başkanlığı",
                    title="50 Müfettiş Yardımcısı Alım İlanı",
                    category="kpss_a",
                    quota_count=50,
                ),
                dict(
                    source_name="resmi_gazete",
                    institution="Sosyal Güvenlik Kurumu Başkanlığı",
                    title="50 Denetmen Yardımcısı Alım İlanı",
                    category="kpss_a",
                    quota_count=50,
                    url="https://www.resmigazete.gov.tr/sgk-denetmen",
                ),
            ),
            # 12. Same source_name must NEVER merge
            (
                dict(
                    rec_id=206,
                    source_name="memurlar_net",
                    institution="Ankara Üniversitesi",
                    title="10 Sözleşmeli Personel Alımı",
                    quota_count=10,
                    url="https://ilan.memurlar.net/ank-1",
                ),
                dict(
                    source_name="memurlar_net",
                    institution="Ankara Üniversitesi Rektörlüğü",
                    title="10 Sözleşmeli Personel Alım İlanı",
                    quota_count=10,
                    url="https://ilan.memurlar.net/ank-2",
                ),
            ),
        ],
    )
    def test_false_pairs_never_merge(self, existing_kwargs, incoming_kwargs):
        ex = _ex_record(**existing_kwargs)
        inc = {
            "category": existing_kwargs.get("category", "sozlesmeli_4b"),
            "publish_date": "2026-11-20",
            "deadline_date": "2026-12-06",
            **incoming_kwargs,
        }
        assert find_matching_existing_id(inc, [ex]) is None


# ---------------------------------------------------------------------------
# 3. EXPIRED DEADLINES, TURKISH UNICODE & INPUT VALIDATION API TESTS
# ---------------------------------------------------------------------------


@pytest.fixture()
def expiry_api_client(tmp_path, monkeypatch):
    temp_db = tmp_path / "test_expiry.db"
    monkeypatch.setattr(database, "DB_PATH", temp_db)
    monkeypatch.setattr(config, "DB_PATH", temp_db)

    async def _noop() -> None:
        return None

    monkeypatch.setattr(scheduler, "start", _noop)
    monkeypatch.setattr(scheduler, "stop", _noop)
    database.init_db(db_path=temp_db)

    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).isoformat()
    today_iso = today.isoformat()

    items = [
        {
            "source_name": "sbb_kamuilan",
            "source_label": "SBB Kamu İlan",
            "external_id": "exp-yesterday",
            "url": "https://kamuilan.sbb.gov.tr/exp",
            "pdf_url": None,
            "title": "Süresi Dolmuş Şırnak İlanı",
            "institution": "Şırnak Valiliği",
            "category": "memur",
            "city": "Şırnak",
            "cities": ["Şırnak"],
            "publish_date": (today - datetime.timedelta(days=15)).isoformat(),
            "deadline_date": yesterday,
            "quota_count": 2,
            "raw_text": "KPSS P3 en az 65 puan 4001 lisans.",
            "summary": "Süresi dolmuş ilan.",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 65.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
                "qualification_codes": ["4001"],
                "max_age": None,
                "cities": ["Şırnak"],
            },
        },
        {
            "source_name": "memurlar_net",
            "source_label": "Memurlar.net İlanlar",
            "external_id": "due-today",
            "url": "https://ilan.memurlar.net/today",
            "pdf_url": None,
            "title": "Bugün Son Gün İstanbul İlanı",
            "institution": "İstanbul Büyükşehir Belediyesi",
            "category": "memur",
            "city": "İstanbul",
            "cities": ["İstanbul", "Çanakkale"],
            "publish_date": (today - datetime.timedelta(days=10)).isoformat(),
            "deadline_date": today_iso,
            "quota_count": 5,
            "raw_text": "KPSS P3 en az 70 puan 4001 lisans. Çanakkale ve İstanbul.",
            "summary": "Bugün son gün.",
            "extracted": {
                "kpss_types": ["P3"],
                "min_score": 70.0,
                "requires_kpss": True,
                "education_levels": ["lisans"],
                "accepts_any_department": True,
                "qualification_codes": ["4001"],
                "max_age": None,
                "cities": ["İstanbul", "Çanakkale"],
            },
        },
    ]
    database.upsert_announcements(items, db_path=temp_db)

    with TestClient(main.app) as client:
        prof = client.get("/api/profile").json()
        prof["is_configured"] = True
        prof["education_level"] = "lisans"
        prof["scores"]["P3"] = 85.0
        prof["qualification_codes"] = ["4001"]
        prof["all_cities"] = True
        assert client.put("/api/profile", json=prof).status_code == 200
        yield client


def test_expired_announcement_hidden_by_default_and_excluded_from_stats_and_ics(expiry_api_client: TestClient):
    # Active radar hides yesterday's expired item, keeps today's deadline_date (days_remaining == 0)
    active = expiry_api_client.get("/api/announcements").json()
    assert active["total"] == 1
    assert active["items"][0]["institution"] == "İstanbul Büyükşehir Belediyesi"
    assert active["items"][0]["days_remaining"] == 0
    # Published 10 days ago -> is_new must be False even though first_seen_at is today
    assert active["items"][0]["is_new"] is False

    # deadline_soon=True includes days_remaining == 0
    soon = expiry_api_client.get("/api/announcements", params={"deadline_soon": True}).json()
    assert soon["total"] == 1

    # include_expired=True shows both
    with_expired = expiry_api_client.get("/api/announcements", params={"include_expired": True}).json()
    assert with_expired["total"] == 2

    # Stats exclude expired item and 10-day-old item is not counted in new_today_count
    stats = expiry_api_client.get("/api/stats").json()
    assert stats["total_active"] == 1
    assert stats["eligible_count"] == 1
    assert stats["deadline_soon_count"] == 1
    assert stats["new_today_count"] == 0
    assert stats["dismissed_count"] == 0

    # ICS includes today's event and excludes yesterday's expired event
    ics = expiry_api_client.get("/api/announcements/export/ics").content.decode("utf-8")
    assert "İstanbul Büyükşehir Belediyesi" in ics
    assert "Şırnak Valiliği" not in ics

    # Saving the expired item keeps it visible in user_status=saved even with include_expired=False
    exp_id = next(i["id"] for i in with_expired["items"] if i["institution"] == "Şırnak Valiliği")
    assert (
        expiry_api_client.patch(
            f"/api/announcements/{exp_id}/state",
            json={"status": "saved", "notes": "Arşiv"},
        ).status_code
        == 200
    )
    saved_res = expiry_api_client.get("/api/announcements", params={"user_status": "saved"}).json()
    assert saved_res["total"] == 1
    assert saved_res["items"][0]["id"] == exp_id


def test_turkish_unicode_search_and_city_filtering(expiry_api_client: TestClient):
    # Search with ASCII lowercase 'istanbul' / 'canakkale' / 'buyuksehir' matches Turkish Unicode
    for query in ("istanbul", "büyükşehir", "BUYUKSEHIR", "Çanakkale"):
        res = expiry_api_client.get("/api/announcements", params={"q": query}).json()
        assert res["total"] == 1, f"q={query!r} eşleşmedi"

    city_res = expiry_api_client.get("/api/announcements", params={"city": "canakkale"}).json()
    assert city_res["total"] == 1


def test_invalid_inputs_return_400_or_422(expiry_api_client: TestClient):
    # Invalid custom source URL scheme -> 400
    bad_url = expiry_api_client.post(
        "/api/custom-sources",
        json={"name": "Bad", "url": "ftp://example.com/feed", "keywords": []},
    )
    assert bad_url.status_code == 400

    # Negative page -> 422
    bad_page = expiry_api_client.get("/api/announcements", params={"page": -1})
    assert bad_page.status_code == 422

    # Invalid user state status -> 422
    bad_state = expiry_api_client.patch(
        "/api/announcements/1/state",
        json={"status": "invalid_status", "notes": ""},
    )
    assert bad_state.status_code == 422


def test_sbb_url_refresh_keeps_single_source_badge():
    existing = {
        "id": 501,
        "title": "10 Memur Alım İlanı",
        "institution": "Ticaret Bakanlığı",
        "category": "memur",
        "publish_date": "2026-11-20",
        "raw_text": "T.C. Ticaret Bakanlığı resmi SBB ilan metni: KPSS P3 en az 70 puan, 4001 lisans mezunu.",
        "extracted": {"kpss_types": ["P3"], "min_score": 70.0, "education_levels": ["lisans"]},
        "sources": [
            {
                "source_name": "sbb_kamuilan",
                "source_label": "SBB Kamu İlan",
                "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=AAA111",
                "pdf_url": "https://kamuilan.sbb.gov.tr/pdf/1.pdf",
                "scraped_at": "2026-11-21T10:00:00",
            }
        ],
    }
    refreshed = {
        **existing,
        "sources": [
            {
                "source_name": "sbb_kamuilan",
                "source_label": "SBB Kamu İlan",
                "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=BBB222",
                "pdf_url": None,
                "scraped_at": "2026-11-22T12:00:00",
            }
        ],
    }
    merged = merge_announcement_records(existing, refreshed)
    assert len(merged["sources"]) == 1
    assert merged["sources"][0]["source_name"] == "sbb_kamuilan"
    assert merged["sources"][0]["url"].endswith("kod=BBB222")


def test_isinolsa_does_not_overwrite_official_sbb_data():
    official_sbb = {
        "id": 502,
        "title": "181 Sözleşmeli Personel Alım İlanı",
        "institution": "Adli Tıp Kurumu Başkanlığı",
        "category": "sozlesmeli_4b",
        "publish_date": "2026-11-20",
        "deadline_date": None,
        "raw_text": "Adli Tıp Kurumu Başkanlığı resmi PDF metni: KPSS P3/P93/P94 en az 70 puan şartı aranır.",
        "summary": "Adli Tıp Kurumu 181 sözleşmeli personel ilanı.",
        "extracted": {
            "kpss_types": ["P3", "P93", "P94"],
            "min_score": 70.0,
            "education_levels": ["lisans", "onlisans", "ortaogretim"],
            "accepts_any_department": False,
        },
        "sources": [
            {
                "source_name": "sbb_kamuilan",
                "source_label": "SBB Kamu İlan",
                "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=ATK",
                "scraped_at": "2026-11-21T09:00:00",
            }
        ],
    }
    isinolsa_item = {
        "source_name": "isinolsa",
        "title": "Adli Tıp Kurumu 181 Personel Alımı Başvuruları Başladı! Detaylar Burada",
        "institution": "Adli Tıp Kurumu",
        "category": "sozlesmeli_4b",
        "deadline_date": "2026-12-06",
        "raw_text": "İşin Olsa haber metni " + ("detay " * 80),
        "extracted": {
            "kpss_types": ["P93"],
            "min_score": 50.0,
            "education_levels": ["onlisans"],
            "accepts_any_department": True,
        },
        "sources": [
            {
                "source_name": "isinolsa",
                "source_label": "İşin Olsa Kamu Alımları",
                "url": "https://www.isinolsa.com/adli-tip-181/",
                "scraped_at": "2026-11-22T10:00:00",
            }
        ],
    }
    merged = merge_announcement_records(official_sbb, isinolsa_item)
    assert {s["source_name"] for s in merged["sources"]} == {"sbb_kamuilan", "isinolsa"}
    assert merged["title"] == "181 Sözleşmeli Personel Alım İlanı"
    assert merged["institution"] == "Adli Tıp Kurumu Başkanlığı"
    assert "Adli Tıp Kurumu Başkanlığı resmi PDF metni" in merged["raw_text"]
    assert merged["extracted"]["min_score"] == 70.0
    assert merged["extracted"]["accepts_any_department"] is False
    assert merged["deadline_date"] == "2026-12-06"


def test_isinolsa_private_sector_speculation_and_institution_commission_filtered():
    for noisy in (
        "6 Zincir Market A101 ŞOK BİM Personel Alımı",
        "Denizbank 72 İlan ile Personel Alacak",
        "TBMM Bütçe Görüşmesi ve Kadro Talepleri",
        "POMEM Bekleniyor: Yeni İlan Ne Zaman?",
    ):
        assert _is_relevant_isinolsa_title(noisy) is False, f"{noisy!r} filtrelenmedi"

    assert _is_relevant_isinolsa_title("Sağlık Bakanlığı 3500 Sözleşmeli Personel Alımı Başvuruları") is True
    assert _is_candidate_link("Yabancı Uyruklu Değerlendirme Komisyonu Personel Alımı İlanı") is False
    assert _is_candidate_link("2026 Yılı 4/B Sözleşmeli Personel Alım İlanı") is True
