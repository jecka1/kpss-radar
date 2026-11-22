"""Turkish KPSS recruitment criteria extractor (NLP/Regex) matching ARCHITECTURE.md Section 2.3."""

from __future__ import annotations

import datetime
import re
from typing import Any

from app.nitelik_kodlari import NITELIK_KODLARI
from app.scrapers.base import (
    RawAnnouncement,
    deduplicate_preserve_order,
    extract_quota_from_text,
    infer_application_channel,
    normalize_ascii_tr,
    normalize_whitespace,
    parse_date_range,
    parse_turkish_date,
    turkish_lower,
)

# Build lookup from known ÖSYM qualification codes
_KNOWN_CODES: dict[str, dict] = {item["code"]: item for item in NITELIK_KODLARI}

# 81 Turkish provinces (canonical name -> ASCII-folded search tokens)
TURKISH_PROVINCES: list[str] = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin",
    "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan",
    "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta",
    "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla",
    "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
    "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat",
    "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın",
    "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce",
]

# Avoid false positives on short/common province names like "Muş", "Van", "Kars", "Bolu", "Ordu", "Ağrı"
_SHORT_OR_AMBIGUOUS_PROVINCES = {"mus", "van", "kars", "bolu", "ordu", "agri", "siirt", "rize", "usak"}

_PROVINCE_PATTERNS: list[tuple[str, re.Pattern[str]]] = []
for _prov in TURKISH_PROVINCES:
    _norm = normalize_ascii_tr(_prov)
    # Require boundary; for short/ambiguous ones require capitalized in original text or explicit context
    _PROVINCE_PATTERNS.append((_prov, re.compile(rf"\b{re.escape(_norm)}\b")))

# Comprehensive Turkish academic departments & KPSS cadre roles
DEPARTMENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Bilgisayar Mühendisliği", re.compile(r"\bbilgisayar\s+müh", re.I)),
    ("Yazılım Mühendisliği", re.compile(r"\byazılım\s+müh", re.I)),
    ("Elektrik-Elektronik Mühendisliği", re.compile(r"\belektrik[\s\-/]*elektronik\s+müh|\belektrik\s+müh|\belektronik\s+müh", re.I)),
    ("İnşaat Mühendisliği", re.compile(r"\binşaat\s+müh", re.I)),
    ("Makine Mühendisliği", re.compile(r"\bmakine\s+müh", re.I)),
    ("Endüstri Mühendisliği", re.compile(r"\bendüstri\s+müh", re.I)),
    ("Çevre Mühendisliği", re.compile(r"\bçevre\s+müh", re.I)),
    ("Harita Mühendisliği", re.compile(r"\bharita\s+müh|\bjeodezi", re.I)),
    ("Jeoloji Mühendisliği", re.compile(r"\bjeoloji\s+müh", re.I)),
    ("Maden Mühendisliği", re.compile(r"\bmaden\s+müh", re.I)),
    ("Ziraat Mühendisliği", re.compile(r"\bziraat\s+müh", re.I)),
    ("Gıda Mühendisliği", re.compile(r"\bgıda\s+müh", re.I)),
    ("Orman Mühendisliği", re.compile(r"\borman\s+müh", re.I)),
    ("Kimya Mühendisliği", re.compile(r"\bkimya\s+müh", re.I)),
    ("Mimarlık", re.compile(r"\bmimarlık|\bmimar\b", re.I)),
    ("Şehir ve Bölge Planlama", re.compile(r"\bşehir\s+ve\s+bölge\s+planlama", re.I)),
    ("İktisat", re.compile(r"\biktisat\b|\bekonomi\b", re.I)),
    ("İşletme", re.compile(r"\bişletme\b", re.I)),
    ("Maliye", re.compile(r"\bmaliye\b", re.I)),
    ("Kamu Yönetimi", re.compile(r"\bkamu\s+yönetimi", re.I)),
    ("Siyaset Bilimi", re.compile(r"\bsiyaset\s+bilimi", re.I)),
    ("Uluslararası İlişkiler", re.compile(r"\buluslararası\s+ilişkiler", re.I)),
    ("Çalışma Ekonomisi ve Endüstri İlişkileri", re.compile(r"\bçalışma\s+ekonomisi", re.I)),
    ("Ekonometri", re.compile(r"\bekonometri\b", re.I)),
    ("İİBF / SBF", re.compile(r"\biibf\b|\biktisadi\s+ve\s+idari\s+bilimler|\bsiyasal\s+bilgiler", re.I)),
    ("Hukuk", re.compile(r"\bhukuk\s+fakültesi|\bhukuk\b|\bavukat\b", re.I)),
    ("İstatistik", re.compile(r"\bistatistik\b", re.I)),
    ("Matematik", re.compile(r"\bmatematik\b", re.I)),
    ("Bilgisayar Programcılığı", re.compile(r"\bbilgisayar\s+programcılı|\bbilişim\s+sistemleri|\byönetim\s+bilişim", re.I)),
    ("Hemşirelik", re.compile(r"\bhemşirelik|\bhemşire\b", re.I)),
    ("Ebelik", re.compile(r"\bebelik\b|\bebe\b", re.I)),
    ("Tıp", re.compile(r"\btıp\s+fakültesi|\btabip\b|\bhekim\b", re.I)),
    ("Diş Hekimliği", re.compile(r"\bdiş\s+hekim", re.I)),
    ("Eczacılık", re.compile(r"\beczacı", re.I)),
    ("Fizyoterapi ve Rehabilitasyon", re.compile(r"\bfizyoterap", re.I)),
    ("Diyetisyenlik / Beslenme", re.compile(r"\bdiyetisyen|\bbeslenme\s+ve\s+diyetetik", re.I)),
    ("Psikoloji", re.compile(r"\bpsikoloji\b|\bpsikolog\b", re.I)),
    ("Sosyal Hizmet", re.compile(r"\bsosyal\s+hizmet|\bsosyal\s+çalışmacı", re.I)),
    ("Sosyoloji", re.compile(r"\bsosyoloji\b", re.I)),
    ("Çocuk Gelişimi", re.compile(r"\bçocuk\s+gelişim", re.I)),
    ("Tıbbi Sekreterlik", re.compile(r"\btıbbi\s+(?:dokümantasyon|sekreter)", re.I)),
    ("Sağlık Teknikerliği", re.compile(r"\bsağlık\s+tekniker|\bparamedik|\bacil\s+tıp|\btıbbi\s+görüntüleme|\blaborant\b|\bröntgen\b", re.I)),
    ("Veterinerlik", re.compile(r"\bveteriner", re.I)),
    ("Büro Yönetimi", re.compile(r"\bbüro\s+yönetimi|\bbüro\s+personeli|\byönetici\s+asistan", re.I)),
    ("Muhasebe", re.compile(r"\bmuhasebe\b", re.I)),
    ("Adalet / Zabıt Katipliği", re.compile(r"\badalet\b|\bzabıt\s+katib|\bmübaşir\b|\binfaz\s+ve\s+koruma", re.I)),
    ("Öğretmenlik", re.compile(r"\böğretmen|\beğitim\s+fakültesi|\brehberlik\s+ve\s+psikolojik", re.I)),
    ("İlahiyat", re.compile(r"\bilahiyat|\bdin\s+hizmetleri|\bimam[\s\-]*hatip", re.I)),
    ("Türk Dili ve Edebiyatı", re.compile(r"\btürk\s+dili\s+ve\s+edebiyat", re.I)),
    ("Tarih", re.compile(r"\btarih\s+(?:bölümü|mezun|öğretmen)", re.I)),
    ("Mütercim-Tercümanlık", re.compile(r"\bmütercim|\btercüman|\bingiliz\s+dili", re.I)),
    ("Dış Ticaret", re.compile(r"\bdış\s+ticaret\b", re.I)),
    ("Lojistik", re.compile(r"\blojistik\b", re.I)),
    ("Mahalli İdareler / Yerel Yönetimler", re.compile(r"\bmahalli\s+idareler|\byerel\s+yönetimler", re.I)),
    ("Pazarlama", re.compile(r"\bpazarlama\b", re.I)),
    ("Halkla İlişkiler ve Tanıtım", re.compile(r"\bhalkla\s+ilişkiler", re.I)),
    ("Bankacılık ve Sigortacılık", re.compile(r"\bbankacılık\b|\bsigortacılık\b", re.I)),
    ("İnsan Kaynakları Yönetimi", re.compile(r"\binsan\s+kaynakları\s+yönetim|\binsan\s+kaynakları\b", re.I)),
    ("İtfaiyecilik ve Sivil Savunma", re.compile(r"\bitfaiyecilik|\bsivil\s+savunma", re.I)),
    ("Emlak Yönetimi", re.compile(r"\bemlak\s+(?:ve\s+emlak\s+)?yönetim", re.I)),
    ("Turizm ve Otelcilik", re.compile(r"\bturizm\s+ve\s+otelcilik|\bturizm\s+işletmecili", re.I)),
    ("Harita ve Kadastro", re.compile(r"\bharita\s+ve\s+kadastro\b", re.I)),
    ("İnşaat Teknolojisi", re.compile(r"\binşaat\s+teknoloj", re.I)),
    ("Elektrik Teknolojisi", re.compile(r"\belektrik\s+teknoloj", re.I)),
    ("Makine Teknolojisi", re.compile(r"\bmakine\s+teknoloj", re.I)),
    ("Çağrı Merkezi Hizmetleri", re.compile(r"\bçağrı\s+merkezi\b", re.I)),
    ("Gıda Teknolojisi", re.compile(r"\bgıda\s+teknoloj", re.I)),
    ("Aşçılık", re.compile(r"\başçılık\b", re.I)),
    ("Anestezi", re.compile(r"\banestezi\b", re.I)),
    ("Diyaliz", re.compile(r"\bdiyaliz\b", re.I)),
    ("İlk ve Acil Yardım", re.compile(r"\bilk\s+ve\s+acil\s+yardım\b", re.I)),
    ("Odyometri", re.compile(r"\bodyometri\b", re.I)),
    ("Optisyenlik", re.compile(r"\boptisyenlik\b", re.I)),
    ("Eczane Hizmetleri", re.compile(r"\beczane\s+hizmetleri\b", re.I)),
    ("Koruma ve Güvenlik", re.compile(r"\bkoruma\s+ve\s+güvenlik|\bgüvenlik\s+görevlisi", re.I)),
    ("Şoför", re.compile(r"\bşoför\b", re.I)),
    ("Destek Personeli", re.compile(r"\bdestek\s+personeli|\btemizlik\s+(?:görevlisi|personeli)|\bhizmetli\b|\bkaloriferci\b|\bağır\s+vasıta|\başçı\b", re.I)),
    ("Tekniker / Teknisyen", re.compile(r"\btekniker\b|\bteknisyen\b", re.I)),
]

VALID_KPSS_NUMBERS = {str(n) for n in range(1, 49)} | {"93", "94", "121"}


def _extract_kpss_types(text_low: str) -> list[str]:
    types: list[str] = []

    if re.search(r"\bekpss\b", text_low):
        types.append("EKPSS")

    # Explicit "KPSS P3", "KPSSP3", "KPSS-P93", "KPSSP 3"
    for m in re.finditer(r"\bkpss\s*[-]?\s*p\s*[-]?\s*(\d{1,3})\b", text_low):
        num = m.group(1)
        if num in VALID_KPSS_NUMBERS:
            types.append(f"P{num}")

    # List patterns like "P3, P93 ve P94" or "P1, P2, P3" or "P3 puan"
    for m in re.finditer(
        r"\bp\s*[-]?\s*(\d{1,3})\b(?=(?:\s*[,/veya\s]+\s*p\s*[-]?\s*\d{1,3})|\s*(?:puan|tür|grubu|veya))",
        text_low,
    ):
        num = m.group(1)
        if num in VALID_KPSS_NUMBERS:
            types.append(f"P{num}")

    # Catch "KPSS (B) grubu ... P3 / P93 / P94" or standalone P93/P94/P10/P121
    for m in re.finditer(r"\bp\s*[-]?\s*(93|94|121|10|3)\b", text_low):
        if "kpss" in text_low:
            types.append(f"P{m.group(1)}")

    return deduplicate_preserve_order(types)


def _extract_requires_kpss(text_low: str, kpss_types: list[str], min_score: float | None) -> bool | None:
    no_kpss_patterns = (
        r"kpss\s+(?:puan\s+)?şartı\s+aranma(?:maktadır|z)",
        r"kpss\s+(?:puanı\s+)?aranma(?:z|maktadır)",
        r"kpss\s+şartı\s+(?:yok|yoktur|bulunmamaktadır)",
        r"kpss['’]?siz",
        r"kpss\s+aranmaksızın",
        r"merkezi\s+sınav\s+şartı\s+aranmaksızın",
    )
    for pat in no_kpss_patterns:
        if re.search(pat, text_low):
            return False

    if kpss_types or min_score is not None:
        return True

    if re.search(
        r"\bkpss\b.*?(?:puan|sınav|en\s+az|taban|belge|sonuç|2024|2025|2026)",
        text_low,
        re.S,
    ):
        return True

    return None


def _parse_float(raw_num: str) -> float | None:
    try:
        val = float(raw_num.replace(",", "."))
        if 40.0 <= val <= 100.0:
            return round(val, 2)
    except ValueError:
        pass
    return None


def _extract_min_score(text_low: str, kpss_types: list[str]) -> float | None:
    # Only extract scores in KPSS/puan context within [40, 100]
    if "kpss" not in text_low and not kpss_types:
        return None
    if "puan" not in text_low and "kpss" not in text_low:
        return None

    scores: list[float] = []
    patterns = (
        r"(?:en\s+az|asgari|minimum|taban\s+puan[ıi]?)\s*[:\-]?\s*(\d{2}(?:[.,]\d{1,2})?)\s*(?:\([^)]+\))?\s*(?:ve\s+(?:üzeri|yukarısı))?\s*puan",
        r"(?:kpss(?:\s*[-]?\s*p\d{1,3})?|puan\s+türünden|puan\s+türlerinden)\s*(?:en\s+az\s*)?(\d{2}(?:[.,]\d{1,2})?)\s*(?:\([^)]+\))?\s*(?:ve\s+üzeri|puan)?",
        r"(\d{2}(?:[.,]\d{1,2})?)\s*(?:\([^)]+\))?\s*(?:ve\s+(?:üzeri|yukarısı)|veya\s+daha\s+yüksek)\s*puan",
        r"(\d{2}(?:[.,]\d{1,2})?)\s*taban\s+puan",
        r"en\s+az\s+(\d{2}(?:[.,]\d{1,2})?)\s*(?:kpss\s*)?puan",
    )
    for pat in patterns:
        for m in re.finditer(pat, text_low):
            prefix_ctx = text_low[max(0, m.start() - 45) : m.start()]
            if re.search(r"\b(?:ales|yds|yökdil|dil\s+puan|yabancı\s+dil|tus|dus)\b", prefix_ctx):
                continue
            val = _parse_float(m.group(1))
            if val is not None and 50.0 <= val <= 99.0:
                scores.append(val)

    if not scores:
        # Fallback: "KPSS ... 70 puan" within short window
        for m in re.finditer(r"kpss.{0,60}?\b([5-9]\d(?:[.,]\d{1,2})?)\b.{0,20}?puan", text_low):
            val = _parse_float(m.group(1))
            if val is not None:
                scores.append(val)

    # Zero-miss principle: if multiple thresholds (e.g. 60 for one cadre, 70 for another), keep lowest
    return min(scores) if scores else None


def _extract_qualification_codes(text: str, text_low: str) -> list[str]:
    codes: list[str] = []

    # 1. Explicit "nitelik kodu: 4001" or "kodu 4531"
    for m in re.finditer(r"(?:nitelik\s*kod\w*|aranan\s+kod\w*|kod\w*)\s*[:\-]?\s*([1-9]\d{3})\b", text_low):
        code = m.group(1)
        if not (1950 <= int(code) <= 2035 and code != "2001"):
            codes.append(code)

    # 2. Known codes from ÖSYM dictionary appearing in text (avoiding years 2002-2035)
    for m in re.finditer(r"\b([23467]\d{3})\b", text):
        code = m.group(1)
        if code in _KNOWN_CODES:
            # Guard 2001/2003 etc. against accidental year hits unless in nitelik/ortaöğretim context
            if code.startswith("20") and code != "2001":
                window = text_low[max(0, m.start() - 40) : m.end() + 40]
                if "nitelik" not in window and "kod" not in window:
                    continue
            codes.append(code)

    return deduplicate_preserve_order(codes)


def _extract_education_levels(
    text_low: str,
    kpss_types: list[str],
    qual_codes: list[str],
) -> list[str]:
    levels: list[str] = []

    # Order matters: detect "önlisans" / "meslek yüksekokulu" before generic "yüksekokul"
    has_onlisans = bool(
        re.search(r"\bön\s*lisans\b|\bönlisans\b|\bmeslek\s+yüksekokul|\bmyo\b|\b2\s+yıllık", text_low)
    )
    # Remove "ön lisans" / "önlisans" / "meslek yüksekokul" before checking "lisans" / "yüksekokul"
    scrubbed = re.sub(r"\bön\s*lisans\b|\bönlisans\b|\bmeslek\s+yüksekokul\w*", " ", text_low)
    has_lisans = bool(
        re.search(
            r"\blisans\b|\bfakülte|\byüksekokul|\bmühendis|\böğretim\s+(?:üyesi|elemanı|görevlisi)|"
            r"\baraştırma\s+görevlisi|\bmüfettiş\s+yardımcısı|\buzman\s+yardımcısı|\bkaymakam\s+adayı",
            scrubbed,
        )
    )
    has_ortaogretim = bool(
        re.search(r"\bortaöğretim\b|\blise\b|\bmeslek\s+lisesi|\bimam\s+hatip\s+lisesi", text_low)
    )
    has_ilkogretim = bool(
        re.search(r"\bilköğretim\b|\bilkokul\b|\bortaokul\b", text_low)
    )

    if has_lisans:
        levels.append("lisans")
    if has_onlisans:
        levels.append("onlisans")
    if has_ortaogretim:
        levels.append("ortaogretim")
    if has_ilkogretim:
        levels.append("ilkogretim")

    # Infer from KPSS score types if still missing or complementary
    for kt in kpss_types:
        if kt == "P93" and "onlisans" not in levels:
            levels.append("onlisans")
        elif kt == "P94" and "ortaogretim" not in levels:
            levels.append("ortaogretim")
        elif kt.startswith("P") and kt not in ("P93", "P94") and "lisans" not in levels:
            levels.append("lisans")

    # Infer from ÖSYM qualification codes
    for code in qual_codes:
        meta = _KNOWN_CODES.get(code)
        if meta and meta["level"] not in levels:
            levels.append(meta["level"])

    return levels


def _extract_departments(text: str, text_low: str, qual_codes: list[str]) -> tuple[list[str], bool]:
    accepts_any = False
    if any(c in ("4001", "3001", "2001") for c in qual_codes):
        accepts_any = True
    if re.search(
        r"herhangi\s+bir\s+(?:ön\s*lisans|önlisans|lisans|ortaöğretim|lise|yükseköğretim|yüksekokul)\s*(?:program|bölüm|alan|fakülte)|"
        r"(?:ön\s*lisans|önlisans|lisans|ortaöğretim|lise)\s+programlarının\s+herhangi\s+birinden\s+mezun|"
        r"tüm\s+(?:ön\s*lisans|önlisans|lisans|ortaöğretim|lise)\s+(?:program|bölüm|mezun)|"
        r"bölüm\s+şartı\s+aranmaksızın",
        text_low,
    ):
        accepts_any = True

    depts: list[str] = []
    for dept_name, pat in DEPARTMENT_PATTERNS:
        if pat.search(text_low):
            depts.append(dept_name)

    for code in qual_codes:
        meta = _KNOWN_CODES.get(code)
        if meta:
            for d in meta.get("departments", []):
                if "Herhangi Bir" not in d:
                    depts.append(d)

    return deduplicate_preserve_order(depts), accepts_any


def _extract_max_age(text_low: str) -> int | None:
    patterns = (
        r"\b([2-5]\d)\s+yaşını\s+(?:doldurmamış|aşmamış|geçmemiş|bitirmemiş)",
        r"\b([2-5]\d)\s+yaşından\s+(?:gün\s+almamış|büyük\s+olmamak|küçük)",
        r"(?:yaş\s+sınırı|üst\s+yaş|azami\s+yaş)\s*[:\-]?\s*([2-5]\d)\b",
    )
    ages: list[int] = []
    for pat in patterns:
        for m in re.finditer(pat, text_low):
            age = int(m.group(1))
            if 20 <= age <= 65:
                ages.append(age)
    # Word forms for 30/35
    if not ages:
        if re.search(r"otuz\s*beş\s+yaşını\s+(?:doldurmamış|aşmamış)", text_low):
            ages.append(35)
        elif re.search(r"otuz\s+yaşını\s+(?:doldurmamış|aşmamış)", text_low):
            ages.append(30)
    # Birth-year cutoff expressions: "01 Ocak 1991 ve sonrası doğumlu olmak", "01.01.1991 ve daha sonra doğan"
    current_year = datetime.date.today().year
    for m in re.finditer(
        r"(?:\b\d{1,2}[./-]\d{1,2}[./-]|\b\d{1,2}\s+[a-zçğıöşü]+\s+)?(19[6-9]\d|200\d)\s*"
        r"(?:tarih\w*\s+)?(?:ve\s+(?:sonrası|sonrasında|daha\s+sonra|sonra)\s+)?(?:doğumlu|doğanlar|doğmuş)",
        text_low,
    ):
        approx_age = current_year - int(m.group(1))
        if 20 <= approx_age <= 65:
            ages.append(approx_age)
    # Zero-miss: if multiple positions have different age caps, take max
    return max(ages) if ages else None


_ANKARA_HQ_INSTITUTIONS = (
    "sayıştay",
    "tbmm",
    "yargıtay",
    "danıştay",
    "anayasa mahkemesi",
    "hsk",
    "yök",
    "yükseköğretim kurulu",
    "sgk",
    "sosyal güvenlik kurumu",
    "afad",
    "botaş",
    "savunma sanayii",
    "tapu ve kadastro",
    "göç idaresi",
    "diyanet",
    "emniyet genel",
    "jandarma",
    "sahil güvenlik",
    "tüik",
    "spk",
    "epdk",
    "btk",
    "kvkk",
    "rekabet kurumu",
    "kamu ihale",
    "nükleer düzenleme",
    "ytb",
    "tika",
    "türkpatent",
    "tse",
    "kosgeb",
    "toki",
    "tübitak",
    "bakanlığı",
    "genel müdürlüğü",
    "başkanlığı",
)

_TURKISH_MONTH_NAMES = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


def _extract_cities(raw: RawAnnouncement, text: str, text_low: str) -> list[str]:
    cities: list[str] = []
    if raw.city:
        cities.append(raw.city)

    if any(
        k in text_low
        for k in (
            "türkiye geneli",
            "81 il",
            "tüm iller",
            "taşra teşkilatı",
            "yurt genelinde",
            "merkez ve taşra",
            "bölge müdürlükleri",
        )
    ):
        cities.append("Türkiye Geneli")

    # Search institution + title first, then body
    priority_chunk = f"{raw.institution} {raw.title}"
    priority_norm = normalize_ascii_tr(priority_chunk)
    body_norm = normalize_ascii_tr(text[:12000])

    for prov, pat in _PROVINCE_PATTERNS:
        norm = normalize_ascii_tr(prov)
        if pat.search(priority_norm):
            cities.append(prov)
        elif norm not in _SHORT_OR_AMBIGUOUS_PROVINCES and pat.search(body_norm):
            cities.append(prov)
        elif norm in _SHORT_OR_AMBIGUOUS_PROVINCES and re.search(rf"\b{re.escape(prov)}\b", f"{raw.institution} {raw.title} {text[:6000]}"):
            cities.append(prov)

    deduped = deduplicate_preserve_order(cities)
    if not deduped:
        inst_low = turkish_lower(raw.institution or "")
        is_local = any(
            loc in inst_low
            for loc in ("belediye", "üniversite", "ilçe", "kaymakam", "valili", "il özel idare")
        )
        if not is_local and any(hq in inst_low for hq in _ANKARA_HQ_INSTITUTIONS):
            deduped = ["Ankara"]

    if "Türkiye Geneli" in deduped and len(deduped) > 1:
        # Keep Türkiye Geneli first if explicit
        deduped = ["Türkiye Geneli"] + [c for c in deduped if c != "Türkiye Geneli"]
    return deduped[:8]


def _extract_dates(raw: RawAnnouncement, text_low: str) -> tuple[str | None, str | None]:
    pub = raw.publish_date
    deadline = raw.deadline_date
    ref = datetime.date.fromisoformat(pub) if pub else datetime.date.today()

    if not deadline:
        # 1. Explicit "son başvuru tarihi: ..."
        for pat in (
            r"son\s+başvuru\s+tarihi\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]20\d{2}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|[^\n.;]{4,40})",
            r"başvuruların\s+sona\s+ereceği\s+tarih\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]20\d{2}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|[^\n.;]{4,40})",
            r"(\d{1,2}[./]\d{1,2}[./]20\d{2})\s*(?:tarihine\s+kadar|mesai\s+bitimine\s+kadar)",
        ):
            m = re.search(pat, text_low[:8000])
            if m:
                parsed = parse_turkish_date(m.group(1), reference_date=ref)
                if parsed:
                    deadline = parsed
                    break

    if not deadline:
        # 2. Range: "20 Kasım - 5 Aralık 2026 tarihleri arasında"
        m = re.search(
            r"(\d{1,2}(?:[./]\d{1,2}[./]20\d{2}|\s+[a-zçğıöşü]+(?:\s+20\d{2})?)\s*[-–—]\s*"
            r"\d{1,2}(?:[./]\d{1,2}[./]20\d{2}|\s+[a-zçğıöşü]+(?:\s+20\d{2})?))\s+tarihleri",
            text_low[:8000],
        )
        if m:
            s_d, e_d = parse_date_range(m.group(1), reference_date=ref)
            if e_d:
                deadline = e_d
            if not pub and s_d:
                pub = s_d

    if not deadline and pub:
        # 3. Relative: "yayımlandığı tarihten itibaren 15 gün içinde"
        m = re.search(
            r"(?:yayım|ilan|yayın)\w*\s+tarih\w*\s+(?:itibaren|takip\s+eden)\s+(\d{1,2})\s*(?:(\(\s*\d+\s*\))?\s*)?(?:iş\s+)?gün\s+içinde",
            text_low[:8000],
        )
        if m:
            days = int(m.group(1))
            if 1 <= days <= 60:
                deadline = (datetime.date.fromisoformat(pub) + datetime.timedelta(days=days)).isoformat()

    return pub, deadline


def _format_turkish_date_readable(date_iso: str) -> str:
    try:
        dt = datetime.date.fromisoformat(date_iso[:10])
        return f"{dt.day} {_TURKISH_MONTH_NAMES[dt.month]} {dt.year}"
    except ValueError:
        return date_iso


def _build_summary(
    raw: RawAnnouncement,
    kpss_types: list[str],
    min_score: float | None,
    requires_kpss: bool | None,
    edu_levels: list[str],
    quota_count: int | None,
    deadline_date: str | None,
) -> str:
    parts: list[str] = []
    if requires_kpss is False:
        parts.append("KPSS şartı aranmamaktadır")
    elif kpss_types or min_score is not None:
        kt_str = "/".join(kpss_types[:3]) if kpss_types else "KPSS"
        if min_score is not None:
            parts.append(f"{kt_str} en az {min_score:g} puan")
        else:
            parts.append(f"{kt_str} puanı ile")

    edu_labels = {
        "lisans": "Lisans",
        "onlisans": "Önlisans",
        "ortaogretim": "Ortaöğretim",
        "ilkogretim": "İlköğretim",
    }
    if edu_levels:
        parts.append(", ".join(edu_labels[e] for e in edu_levels if e in edu_labels))

    inst_clean = normalize_whitespace(raw.institution or "")
    title_clean = normalize_whitespace(raw.title or "")
    title_already_has_inst = bool(
        inst_clean and turkish_lower(title_clean).startswith(turkish_lower(inst_clean))
    )
    title_already_has_quota = bool(
        quota_count and re.search(rf"(?<!\d){quota_count}(?!\d)", title_clean)
    )

    if title_already_has_inst:
        head = title_clean
        if quota_count and not title_already_has_quota:
            head += f" ({quota_count} kişilik)"
    else:
        head = f"{inst_clean} tarafından"
        if quota_count and not title_already_has_quota:
            head += f" {quota_count} kişilik"
        head += f" {title_clean}"

    if parts:
        summary = f"{head} ({' • '.join(parts)})."
    else:
        summary = f"{head}."

    if deadline_date:
        summary += f" Son başvuru: {_format_turkish_date_readable(deadline_date)}."
    return normalize_whitespace(summary)[:320]


def extract_criteria(raw: RawAnnouncement) -> dict[str, Any]:
    """Extract structured KPSS eligibility criteria from a RawAnnouncement."""
    full_text = f"{raw.institution}\n{raw.title}\n{raw.raw_text or ''}"
    text_slice = full_text[:40000]
    text_low = turkish_lower(text_slice)
    title_low = turkish_lower(raw.title or "")

    kpss_types = _extract_kpss_types(text_low)
    min_score = _extract_min_score(text_low, kpss_types)
    requires_kpss = _extract_requires_kpss(text_low, kpss_types, min_score)
    qual_codes = _extract_qualification_codes(text_slice, text_low)
    edu_levels = _extract_education_levels(text_low, kpss_types, qual_codes)

    is_akademik = raw.category == "akademik" or any(
        t in title_low
        for t in (
            "öğretim üyesi",
            "öğretim elemanı",
            "öğretim görevlisi",
            "araştırma görevlisi",
            "profesör",
            "doçent",
            "doktor öğretim",
        )
    )
    if is_akademik:
        edu_levels = ["lisans"]
        requires_kpss = False
        kpss_types = []
        min_score = None
    elif raw.category == "kpss_a" or any(
        t in title_low
        for t in (
            "denetmen yardımcısı",
            "denetçi yardımcısı",
            "müfettiş yardımcısı",
            "uzman yardımcısı",
            "kontrolör",
            "kaymakam adayı",
            "kalkınma ajansı",
        )
    ):
        if "lisans" not in edu_levels:
            edu_levels.insert(0, "lisans")

    departments, accepts_any = _extract_departments(text_slice, text_low, qual_codes)
    max_age = _extract_max_age(text_low)
    cities = _extract_cities(raw, text_slice, text_low)
    publish_date, deadline_date = _extract_dates(raw, text_low)
    quota_count = raw.quota_count or extract_quota_from_text(raw.title, raw.raw_text or "")
    channel = raw.application_channel or infer_application_channel(text_slice)
    has_pdf = bool(raw.pdf_url)

    missing_fields: list[str] = []
    if requires_kpss is None:
        missing_fields.append("requires_kpss")
    if requires_kpss is not False and min_score is None:
        missing_fields.append("min_score")
    if not edu_levels:
        missing_fields.append("education_levels")
    if not departments and not accepts_any:
        missing_fields.append("departments")
    if not deadline_date:
        missing_fields.append("deadline_date")

    # Confidence heuristic (0.0 .. 1.0)
    signals = [
        bool(raw.raw_text and len(raw.raw_text.strip()) > 150),
        requires_kpss is not None,
        bool(kpss_types) or requires_kpss is False,
        min_score is not None or requires_kpss is False,
        bool(edu_levels),
        bool(departments) or accepts_any,
        bool(deadline_date),
        bool(cities),
    ]
    confidence = round(sum(1 for s in signals if s) / len(signals), 2)

    summary = _build_summary(
        raw=raw,
        kpss_types=kpss_types,
        min_score=min_score,
        requires_kpss=requires_kpss,
        edu_levels=edu_levels,
        quota_count=quota_count,
        deadline_date=deadline_date,
    )

    return {
        "kpss_types": kpss_types,
        "min_score": min_score,
        "requires_kpss": requires_kpss,
        "education_levels": edu_levels,
        "departments": departments,
        "accepts_any_department": accepts_any,
        "qualification_codes": qual_codes,
        "max_age": max_age,
        "cities": cities,
        "quota_count": quota_count,
        "publish_date": publish_date,
        "deadline_date": deadline_date,
        "application_channel": channel,
        "has_pdf": has_pdf,
        "missing_fields": missing_fields,
        "confidence": confidence,
        "summary": summary,
    }
