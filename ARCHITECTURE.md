# KPSS Radar — Mimari ve Arayüz Sözleşmesi (Contract)

Bu belge, `backend-core`, `scrapers-and-parser` ve `frontend-ui` modüllerinin birebir uyumlu çalışması için kesin veri modellerini, Python arayüzlerini ve REST API sözleşmesini tanımlar.

---

## 1. Dizin Yapısı ve Dosya Sahipliği

```text
kpss/
├── ARCHITECTURE.md                  # (Coordinator) Mimari sözleşme
├── README.md                        # (qa-integration) Kurulum ve kullanım kılavuzu
├── start.ps1 / start.bat            # (qa-integration) Tek tıkla başlatıcı
├── backend/
│   ├── requirements.txt             # (backend-core)
│   ├── .venv/                       # (backend-core) Python 3.14 sanal ortamı
│   ├── data/                        # SQLite DB (kpss_radar.db)
│   ├── tests/                       # (qa-integration) Pytest testleri
│   └── app/
│       ├── __init__.py              # (backend-core)
│       ├── config.py                # (backend-core)
│       ├── models.py                # (backend-core) Pydantic şemaları
│       ├── database.py              # (backend-core) SQLite (WAL) veri katmanı
│       ├── nitelik_kodlari.py       # (backend-core) ÖSYM nitelik kodları sözlüğü
│       ├── scheduler.py             # (backend-core) Arka plan zamanlayıcı + tarama orkestratörü
│       ├── main.py                  # (backend-core) FastAPI uygulama girişi + tüm endpoint'ler
│       ├── scrapers/                # (scrapers-and-parser)
│       │   ├── __init__.py
│       │   ├── base.py              # RawAnnouncement, HTTPClient (Windows TLS uyumlu)
│       │   ├── sbb_kamuilan.py      # kamuilan.sbb.gov.tr (+ PDF metin çıkarıcı)
│       │   ├── memurlar_net.py      # ilan.memurlar.net (windows-1254, ?Expire=false)
│       │   ├── resmi_gazete.py      # resmigazete.gov.tr günlük Çeşitli İlanlar
│       │   ├── osym.py              # osym.gov.tr KPSS duyuru ve tercih kılavuzları
│       │   └── custom_watcher.py    # Kullanıcının eklediği özel kurum/RSS sayfaları
│       └── engine/                  # (scrapers-and-parser)
│           ├── __init__.py
│           ├── extractor.py         # Türkçe KPSS kriter çıkarıcı (NLP/Regex)
│           ├── deduplicator.py      # Kaynaklar arası tekilleştirme & birleştirme
│           ├── matcher.py           # Sıfır-Kaçırma 3 Kademeli Uygunluk Motoru
│           └── notifier.py          # Telegram Bot & Webhook bildirim gönderici
└── frontend/                        # (frontend-ui) Vite + React + TypeScript + Tailwind
    ├── package.json
    ├── vite.config.ts               # /api -> http://127.0.0.1:8000 proxy
    └── src/
        ├── types.ts                 # Backend JSON şemalarının birebir TS karşılıkları
        ├── api.ts                   # Fetch wrapper
        ├── components/              # Layout, Dashboard, AnnouncementCard, DetailDrawer, ProfilePage, SourcesPage, OnboardingModal
        └── App.tsx
```

---

## 2. Python İç Sözleşmesi (`backend-core` <-> `scrapers-and-parser`)

### 2.1 `app/scrapers/base.py`
```python
@dataclass
class RawAnnouncement:
    source_name: str           # "sbb_kamuilan" | "memurlar_net" | "resmi_gazete" | "osym" | "custom:<name>"
    source_label: str          # "SBB Kamu İlan" | "Memurlar.net" | "Resmî Gazete" | "ÖSYM" | ...
    external_id: str           # Kaynağa özgü benzersiz kimlik (veya URL hash)
    url: str                   # İlanın orijinal URL'si
    title: str                 # İlan başlığı
    institution: str           # Kurum adı
    category: str              # "memur" | "sozlesmeli_4b" | "merkezi_atama" | "kpss_a" | "isci" | "akademik" | "askeri_emniyet" | "sydv" | "engelli" | "diger"
    publish_date: str | None   # "YYYY-MM-DD" veya None
    deadline_date: str | None  # "YYYY-MM-DD" veya None
    city: str | None           # İl adı veya "Türkiye Geneli" veya None
    quota_count: int | None    # Kontenjan sayısı
    raw_text: str              # İlan tam metni (HTML'den temizlenmiş veya PDF'ten çıkarılmış)
    pdf_url: str | None = None
    application_channel: str | None = None # "Kariyer Kapısı" | "İŞKUR" | "ÖSYM AİS" | "Kurum Sitesi" | None
```

### 2.2 `app/scrapers/__init__.py`
Aşağıdaki fonksiyonu dışa aktarır:
```python
SCRAPER_REGISTRY: dict[str, dict] = {
    "sbb_kamuilan": {"label": "SBB Kamu İlan", "url": "https://kamuilan.sbb.gov.tr/"},
    "memurlar_net": {"label": "Memurlar.net İlanlar", "url": "https://ilan.memurlar.net/"},
    "resmi_gazete": {"label": "T.C. Resmî Gazete", "url": "https://www.resmigazete.gov.tr/"},
    "osym": {"label": "ÖSYM KPSS Duyuruları", "url": "https://www.osym.gov.tr/"},
}

async def run_scraper(source_name: str, known_external_ids: set[str] | None = None) -> list[RawAnnouncement]: ...
async def run_custom_source(name: str, url: str, keywords: list[str] | None = None) -> list[RawAnnouncement]: ...
```
> Önemli: `known_external_ids` verilirse, scraper zaten veritabanında metni dolu olan ilanların detay sayfasını/PDF'ini tekrar indirmez (hız ve nazik tarama için).

### 2.3 `app/engine/extractor.py`
```python
def extract_criteria(raw: RawAnnouncement) -> dict:
    """
    Döndürdüğü dict yapısı (extracted_json):
    {
        "kpss_types": list[str],         # örn. ["P3", "P93"] veya []
        "min_score": float | None,       # örn. 70.0 veya None
        "requires_kpss": bool | None,    # True, False (açıkça KPSS'siz), None (belirsiz)
        "education_levels": list[str],   # ["lisans", "onlisans", "ortaogretim", "ilkogretim"] alt kümesi
        "departments": list[str],        # çıkarılan bölüm adları
        "accepts_any_department": bool,  # 4001/3001/2001 veya "herhangi bir lisans/önlisans" geçiyorsa True
        "qualification_codes": list[str],# örn. ["4001", "6225"]
        "max_age": int | None,           # örn. 35
        "cities": list[str],             # örn. ["Ankara"] veya ["Türkiye Geneli"]
        "quota_count": int | None,
        "publish_date": str | None,      # "YYYY-MM-DD"
        "deadline_date": str | None,     # "YYYY-MM-DD"
        "application_channel": str | None,
        "has_pdf": bool,
        "missing_fields": list[str],     # örn. ["min_score", "departments"]
        "confidence": float,             # 0.0 - 1.0
        "summary": str                   # 1-2 cümlelik okunaklı özet
    }
    """
```

### 2.4 `app/engine/deduplicator.py`
```python
def compute_dedup_key(institution: str, title: str, publish_date: str | None = None) -> str: ...
def find_matching_existing_id(new_item: dict, existing_items: list[dict]) -> int | None: ...
def merge_announcement_records(existing: dict, incoming: dict) -> dict: ...
```

### 2.5 `app/engine/matcher.py`
```python
def evaluate_match(announcement: dict, profile: dict) -> dict:
    """
    SIFIR KAÇIRMA GARANTİLİ 3 KADEMELİ EŞLEŞTİRME:
    Döndürür:
    {
        "match_status": "eligible" | "review" | "ineligible",
        "match_score": int, # 0 - 100
        "headline": str,    # Kısa Türkçe özet (örn. "KPSS P3 ve Lisans şartlarına tam uyuyor")
        "reasons": [
            {
                "field": "education" | "kpss_score" | "department" | "age" | "city" | "category",
                "label": str,    # örn. "KPSS Puanı"
                "status": "pass" | "warn" | "fail" | "unknown",
                "message": str
            }
        ]
    }
    """
```
**Sıfır-Kaçırma Kuralı:**
- Profil henüz doldurulmamışsa (`profile.is_configured == False`): tüm ilanlar `review` (score 50) döner.
- Bir kritere ait veri ilandan çıkarılamamışsa (`unknown` / `warn`), bu ASLA `fail` olmaz; en kötü ihtimalle ilanı `review` ("İnceleme Gerekli") statüsüne taşır.
- Sadece **kesin çelişki** (örn. ilanda açıkça `en az 80 KPSS P3` yazıyor ve kullanıcının P3 puanı `74.2`; veya ilan sadece `Ortaöğretim` istiyor ve kullanıcı `Lisans`; veya ilanda açıkça `30 yaş` sınırı var ve kullanıcı `34` yaşında; veya ilan sadece `Tıp Fakültesi` istiyor ve kullanıcı `Bilgisayar Mühendisliği` mezunu ve `accepts_any_department == False`) `ineligible` yapar!

### 2.6 `app/engine/notifier.py`
```python
async def send_notifications(profile: dict, announcements: list[dict]) -> dict:
    """Telegram Bot API ve/veya Webhook'a yeni uygun ilanları gönderir. {"sent": bool, "channel": str, "error": str | None}"""

async def send_test_notification(profile: dict) -> dict: ...
```

---

## 3. REST API Sözleşmesi (`backend-core` <-> `frontend-ui`)

Base URL: `http://127.0.0.1:8000/api`

### 3.1 Profil (`GET /api/profile`, `PUT /api/profile`)
```json
{
  "is_configured": true,
  "full_name": "Aday",
  "kpss_year": 2026,
  "education_level": "lisans",
  "scores": {
    "P3": 84.5,
    "P93": null,
    "P94": null,
    "P1": null,
    "P2": null,
    "P10": null,
    "P121": null,
    "EKPSS": null,
    "YDS": 72.5
  },
  "departments": ["Bilgisayar Mühendisliği"],
  "qualification_codes": ["4001", "4531"],
  "birth_year": 1999,
  "gender": "belirtmek_istemiyorum",
  "military_status": "muaf_veya_yapildi",
  "driver_licenses": ["B"],
  "certificates": [],
  "preferred_cities": [],
  "all_cities": true,
  "preferred_categories": ["memur", "sozlesmeli_4b", "merkezi_atama", "kpss_a", "isci", "akademik", "sydv"],
  "include_no_kpss": true,
  "scan_interval_minutes": 60,
  "telegram_bot_token": "",
  "telegram_chat_id": "",
  "webhook_url": ""
}
```
> Not: `education_level` değerleri: `"lisans" | "onlisans" | "ortaogretim" | "ilkogretim"`.

### 3.2 İlan Listesi (`GET /api/announcements`)
Query parametreleri:
- `match_status`: `all | eligible | review | eligible_or_review | ineligible` (varsayılan `all`)
- `category`: kategori kodu veya `all`
- `source`: kaynak kodu (`sbb_kamuilan`, `memurlar_net`, `resmi_gazete`, `osym`) veya `all`
- `city`: şehir adı veya `all`
- `user_status`: `all | saved | applied | dismissed | active` (varsayılan `active` -> `dismissed` hariç)
- `deadline_soon`: `true | false` (kalan gün <= 5)
- `q`: serbest metin araması
- `sort`: `match_score | deadline | newest` (varsayılan `match_score`)
- `page`: int (varsayılan `1`), `page_size`: int (varsayılan `30`)

Response:
```json
{
  "total": 124,
  "page": 1,
  "page_size": 30,
  "items": [
    {
      "id": 1,
      "title": "181 Sözleşmeli Personel Alım İlanı",
      "institution": "Adli Tıp Kurumu Başkanlığı",
      "category": "sozlesmeli_4b",
      "city": "İstanbul",
      "cities": ["İstanbul", "Ankara"],
      "publish_date": "2026-11-20",
      "deadline_date": "2026-12-06",
      "days_remaining": 14,
      "quota_count": 181,
      "summary": "KPSS P3/P93/P94 en az 70 puan ile 181 sözleşmeli personel alınacaktır.",
      "extracted": {
        "kpss_types": ["P3", "P93", "P94"],
        "min_score": 70.0,
        "requires_kpss": true,
        "education_levels": ["lisans", "onlisans", "ortaogretim"],
        "departments": ["Büro Yönetimi", "Hemşirelik"],
        "accepts_any_department": true,
        "qualification_codes": ["4001"],
        "max_age": 35,
        "application_channel": "Kariyer Kapısı",
        "has_pdf": true,
        "missing_fields": [],
        "confidence": 0.88
      },
      "sources": [
        {
          "source_name": "sbb_kamuilan",
          "source_label": "SBB Kamu İlan",
          "url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=...",
          "pdf_url": "https://kamuilan.sbb.gov.tr/ilanDetay.aspx?kod=...",
          "scraped_at": "2026-11-22T15:55:00"
        }
      ],
      "match": {
        "match_status": "eligible",
        "match_score": 92,
        "headline": "KPSS P3 (84.5 ≥ 70) ve Lisans şartlarına tam uyuyor",
        "reasons": [
          {"field": "education", "label": "Eğitim Düzeyi", "status": "pass", "message": "Lisans düzeyi destekleniyor"},
          {"field": "kpss_score", "label": "KPSS Puanı", "status": "pass", "message": "P3 puanınız (84.5) taban puandan (70) yüksek"}
        ]
      },
      "user_state": {
        "status": "none",
        "notes": ""
      },
      "first_seen_at": "2026-11-22T15:55:00",
      "is_new": true
    }
  ]
}
```

### 3.3 İlan Detayı (`GET /api/announcements/{id}`)
Yukarıdaki item yapısının aynısı + `"raw_text": "..."`.

### 3.4 Kullanıcı İlan Durumu (`PATCH /api/announcements/{id}/state`)
Body: `{"status": "none" | "saved" | "applied" | "dismissed", "notes": "..."}`
Response: `{"id": 1, "status": "saved", "notes": "..."}`

### 3.5 Özet İstatistikler (`GET /api/stats`)
```json
{
  "total_active": 124,
  "eligible_count": 28,
  "review_count": 64,
  "ineligible_count": 32,
  "deadline_soon_count": 9,
  "new_today_count": 15,
  "saved_count": 4,
  "applied_count": 1,
  "is_scanning": false,
  "last_scan_at": "2026-11-22T15:55:00",
  "categories": {"sozlesmeli_4b": 45, "memur": 20, "isci": 30},
  "sources": [
    {
      "source_name": "sbb_kamuilan",
      "source_label": "SBB Kamu İlan",
      "url": "https://kamuilan.sbb.gov.tr/",
      "status": "success",
      "items_found": 90,
      "items_new": 12,
      "last_run_at": "2026-11-22T15:55:00",
      "error_message": null
    }
  ]
}
```

### 3.6 Tarama & Diğer Endpoint'ler
- `POST /api/scrape/trigger` — body opsiyonel `{"source": "all" | "sbb_kamuilan" | ...}` -> `{"started": true, "message": "..."}`
- `GET /api/scrape/status` -> `{"is_scanning": bool, "current_source": str | None, "last_scan_at": str | None, "runs": [...]}`
- `GET /api/nitelik-kodlari?q=4001` -> `[{"code": "4001", "level": "lisans", "title": "Herhangi bir lisans programından mezun olmak", "departments": ["Herhangi Bir Lisans"]}]`
- `GET /api/custom-sources`, `POST /api/custom-sources` (`{"name": "...", "url": "...", "keywords": ["KPSS", "alım"]}`), `DELETE /api/custom-sources/{id}`
- `POST /api/notifications/test` -> `{"sent": bool, "channel": str, "error": str | None}`
- `GET /api/announcements/export/ics` -> `text/calendar` dosyası (`kpss-radar-takvim.ics`)
