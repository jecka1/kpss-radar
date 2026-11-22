"""Comprehensive Turkish ÖSYM KPSS Nitelik Kodları (Qualification Codes) dictionary and search."""

from __future__ import annotations

import unicodedata


def _normalize_tr(text: str) -> str:
    """Normalize Turkish text for case-insensitive and diacritic-tolerant search."""
    if not text:
        return ""
    replacements = {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ş": "s",
        "ş": "s",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
    }
    out = "".join(replacements.get(ch, ch) for ch in text)
    out = unicodedata.normalize("NFKD", out)
    out = "".join(ch for ch in out if not unicodedata.combining(ch))
    return out.lower().strip()


NITELIK_KODLARI: list[dict] = [
    # --- Genel Eğitim Düzeyi Kodları ---
    {
        "code": "2001",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının herhangi bir alanından mezun olmak",
        "departments": ["Herhangi Bir Ortaöğretim (Lise)"],
    },
    {
        "code": "3001",
        "level": "onlisans",
        "title": "Herhangi bir önlisans programından mezun olmak",
        "departments": ["Herhangi Bir Önlisans"],
    },
    {
        "code": "4001",
        "level": "lisans",
        "title": "Herhangi bir lisans programından mezun olmak",
        "departments": ["Herhangi Bir Lisans"],
    },
    # --- Ortaöğretim (2xxx) ---
    {
        "code": "2003",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Adalet alanı ve dallarından mezun olmak",
        "departments": ["Adalet", "Zabıt Katipliği"],
    },
    {
        "code": "2005",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının İmam Hatip Alanından mezun olmak",
        "departments": ["İmam Hatip"],
    },
    {
        "code": "2011",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Tarım Teknolojileri alanı ve dallarından mezun olmak",
        "departments": ["Tarım Teknolojileri", "Tarım"],
    },
    {
        "code": "2013",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Hayvan Sağlığı / Hayvan Yetiştiriciliği alanından mezun olmak",
        "departments": ["Hayvan Sağlığı", "Veteriner Sağlık"],
    },
    {
        "code": "2015",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Hemşirelik alanından mezun olmak",
        "departments": ["Hemşirelik"],
    },
    {
        "code": "2017",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Ebelik alanından mezun olmak",
        "departments": ["Ebelik"],
    },
    {
        "code": "2019",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Acil Sağlık Hizmetleri (Acil Tıp Teknisyenliği) alanından mezun olmak",
        "departments": ["Acil Tıp Teknisyenliği", "Acil Sağlık Hizmetleri"],
    },
    {
        "code": "2021",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Büro Yönetimi ve Sekreterlik alanından mezun olmak",
        "departments": ["Büro Yönetimi", "Sekreterlik"],
    },
    {
        "code": "2023",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Muhasebe ve Finansman alanından mezun olmak",
        "departments": ["Muhasebe", "Finansman"],
    },
    {
        "code": "2025",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Pazarlama ve Perakende alanından mezun olmak",
        "departments": ["Pazarlama", "Perakende"],
    },
    {
        "code": "2027",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Bilişim Teknolojileri alanı ve dallarından mezun olmak",
        "departments": ["Bilişim Teknolojileri", "Bilgisayar"],
    },
    {
        "code": "2029",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Ulaştırma Hizmetleri (Lojistik) alanından mezun olmak",
        "departments": ["Ulaştırma Hizmetleri", "Lojistik"],
    },
    {
        "code": "2031",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Halkla İlişkiler ve Organizasyon Hizmetleri alanından mezun olmak",
        "departments": ["Halkla İlişkiler"],
    },
    {
        "code": "2041",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Sağlık Hizmetleri Sekreterliği (Tıbbi Sekreterlik) alanından mezun olmak",
        "departments": ["Tıbbi Sekreterlik", "Sağlık Hizmetleri Sekreterliği"],
    },
    {
        "code": "2043",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Tıbbi Laboratuvar alanından mezun olmak",
        "departments": ["Tıbbi Laboratuvar"],
    },
    {
        "code": "2045",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Radyoloji Teknisyenliği alanından mezun olmak",
        "departments": ["Radyoloji"],
    },
    {
        "code": "2047",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Anestezi alanından mezun olmak",
        "departments": ["Anestezi"],
    },
    {
        "code": "2051",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Elektrik-Elektronik Teknolojisi alanından mezun olmak",
        "departments": ["Elektrik", "Elektronik", "Elektrik-Elektronik"],
    },
    {
        "code": "2055",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Endüstriyel Otomasyon Teknolojileri alanından mezun olmak",
        "departments": ["Otomasyon", "Endüstriyel Otomasyon"],
    },
    {
        "code": "2059",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Makine Teknolojisi alanı ve dallarından mezun olmak",
        "departments": ["Makine Teknolojisi", "Makine"],
    },
    {
        "code": "2061",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının İnşaat Teknolojisi alanı ve dallarından mezun olmak",
        "departments": ["İnşaat Teknolojisi", "İnşaat"],
    },
    {
        "code": "2065",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Tesisat Teknolojisi ve İklimlendirme alanından mezun olmak",
        "departments": ["Tesisat", "İklimlendirme", "Sıhhi Tesisat"],
    },
    {
        "code": "2067",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Metal Teknolojisi alanından mezun olmak",
        "departments": ["Metal Teknolojisi", "Kaynakçılık"],
    },
    {
        "code": "2071",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Motorlu Araçlar Teknolojisi alanından mezun olmak",
        "departments": ["Motorlu Araçlar", "Otomotiv"],
    },
    {
        "code": "2075",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Mobilya ve İç Mekan Tasarımı alanından mezun olmak",
        "departments": ["Mobilya ve İç Mekan Tasarımı", "Marangozluk"],
    },
    {
        "code": "2081",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Kimya Teknolojisi alanından mezun olmak",
        "departments": ["Kimya Teknolojisi"],
    },
    {
        "code": "2085",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Gıda Teknolojisi alanından mezun olmak",
        "departments": ["Gıda Teknolojisi"],
    },
    {
        "code": "2089",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Harita-Tapu-Kadastro alanından mezun olmak",
        "departments": ["Harita", "Tapu", "Kadastro"],
    },
    {
        "code": "2093",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Matbaa Teknolojisi alanından mezun olmak",
        "departments": ["Matbaa"],
    },
    {
        "code": "2101",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Konaklama ve Seyahat Hizmetleri alanından mezun olmak",
        "departments": ["Turizm", "Konaklama"],
    },
    {
        "code": "2105",
        "level": "ortaogretim",
        "title": "Ortaöğretim kurumlarının Yiyecek İçecek Hizmetleri (Aşçılık) alanından mezun olmak",
        "departments": ["Aşçılık", "Yiyecek İçecek Hizmetleri"],
    },
    # --- Önlisans (3xxx) ---
    {
        "code": "3003",
        "level": "onlisans",
        "title": "Adalet önlisans programından veya Adalet Meslek Yüksekokulundan mezun olmak",
        "departments": ["Adalet", "Hukuk Büro Yönetimi ve Sekreterliği"],
    },
    {
        "code": "3005",
        "level": "onlisans",
        "title": "Büro Yönetimi, Büro Yönetimi ve Sekreterlik / Yönetici Asistanlığı önlisans programından mezun olmak",
        "departments": ["Büro Yönetimi ve Yönetici Asistanlığı", "Büro Yönetimi ve Sekreterlik"],
    },
    {
        "code": "3007",
        "level": "onlisans",
        "title": "Halkla İlişkiler ve Tanıtım önlisans programından mezun olmak",
        "departments": ["Halkla İlişkiler ve Tanıtım", "İletişim"],
    },
    {
        "code": "3009",
        "level": "onlisans",
        "title": "Yerel Yönetimler / Mahalli İdareler önlisans programından mezun olmak",
        "departments": ["Yerel Yönetimler", "Mahalli İdareler"],
    },
    {
        "code": "3011",
        "level": "onlisans",
        "title": "Sosyal Güvenlik önlisans programından mezun olmak",
        "departments": ["Sosyal Güvenlik"],
    },
    {
        "code": "3013",
        "level": "onlisans",
        "title": "Maliye önlisans programından mezun olmak",
        "departments": ["Maliye"],
    },
    {
        "code": "3015",
        "level": "onlisans",
        "title": "Muhasebe, Bilgisayarlı Muhasebe ve Vergi Uygulamaları önlisans programından mezun olmak",
        "departments": ["Muhasebe ve Vergi Uygulamaları", "Muhasebe"],
    },
    {
        "code": "3017",
        "level": "onlisans",
        "title": "İşletme, İşletmecilik, İşletme Yönetimi önlisans programından mezun olmak",
        "departments": ["İşletme Yönetimi", "İşletme"],
    },
    {
        "code": "3019",
        "level": "onlisans",
        "title": "Bankacılık ve Sigortacılık önlisans programından mezun olmak",
        "departments": ["Bankacılık ve Sigortacılık"],
    },
    {
        "code": "3021",
        "level": "onlisans",
        "title": "Dış Ticaret / Dış Ticaret ve Avrupa Birliği önlisans programından mezun olmak",
        "departments": ["Dış Ticaret"],
    },
    {
        "code": "3023",
        "level": "onlisans",
        "title": "Lojistik / Ulaştırma ve Trafik Hizmetleri önlisans programından mezun olmak",
        "departments": ["Lojistik", "Ulaştırma"],
    },
    {
        "code": "3025",
        "level": "onlisans",
        "title": "Emlak ve Emlak Yönetimi / Gayrimenkul Yönetimi önlisans programından mezun olmak",
        "departments": ["Emlak ve Emlak Yönetimi"],
    },
    {
        "code": "3027",
        "level": "onlisans",
        "title": "İnsan Kaynakları Yönetimi önlisans programından mezun olmak",
        "departments": ["İnsan Kaynakları Yönetimi"],
    },
    {
        "code": "3029",
        "level": "onlisans",
        "title": "Çağrı Merkezi Hizmetleri önlisans programından mezun olmak",
        "departments": ["Çağrı Merkezi Hizmetleri"],
    },
    {
        "code": "3031",
        "level": "onlisans",
        "title": "Çocuk Gelişimi önlisans programından mezun olmak",
        "departments": ["Çocuk Gelişimi"],
    },
    {
        "code": "3033",
        "level": "onlisans",
        "title": "Sosyal Hizmetler önlisans programından mezun olmak",
        "departments": ["Sosyal Hizmetler"],
    },
    {
        "code": "3035",
        "level": "onlisans",
        "title": "İlahiyat (Önlisans) programından mezun olmak",
        "departments": ["İlahiyat"],
    },
    {
        "code": "3037",
        "level": "onlisans",
        "title": "Kütüphanecilik / Arşivcilik / Bilgi Yönetimi önlisans programından mezun olmak",
        "departments": ["Bilgi Yönetimi", "Arşivcilik", "Kütüphanecilik"],
    },
    {
        "code": "3043",
        "level": "onlisans",
        "title": "Tıbbi Dokümantasyon ve Sekreterlik önlisans programından mezun olmak",
        "departments": ["Tıbbi Dokümantasyon ve Sekreterlik", "Tıbbi Sekreterlik"],
    },
    {
        "code": "3045",
        "level": "onlisans",
        "title": "İlk ve Acil Yardım (Paramedik) / Ambulans ve Acil Bakım Teknikerliği önlisans programından mezun olmak",
        "departments": ["İlk ve Acil Yardım", "Paramedik"],
    },
    {
        "code": "3047",
        "level": "onlisans",
        "title": "Anestezi / Anestezi Teknikerliği önlisans programından mezun olmak",
        "departments": ["Anestezi"],
    },
    {
        "code": "3049",
        "level": "onlisans",
        "title": "Tıbbi Görüntüleme Teknikleri / Radyoloji önlisans programından mezun olmak",
        "departments": ["Tıbbi Görüntüleme Teknikleri", "Radyoloji"],
    },
    {
        "code": "3051",
        "level": "onlisans",
        "title": "Tıbbi Laboratuvar Teknikleri önlisans programından mezun olmak",
        "departments": ["Tıbbi Laboratuvar Teknikleri"],
    },
    {
        "code": "3053",
        "level": "onlisans",
        "title": "Diyaliz önlisans programından mezun olmak",
        "departments": ["Diyaliz"],
    },
    {
        "code": "3055",
        "level": "onlisans",
        "title": "Fizyoterapi önlisans programından mezun olmak",
        "departments": ["Fizyoterapi"],
    },
    {
        "code": "3057",
        "level": "onlisans",
        "title": "Ağız ve Diş Sağlığı önlisans programından mezun olmak",
        "departments": ["Ağız ve Diş Sağlığı"],
    },
    {
        "code": "3059",
        "level": "onlisans",
        "title": "Ameliyathane Hizmetleri önlisans programından mezun olmak",
        "departments": ["Ameliyathane Hizmetleri"],
    },
    {
        "code": "3061",
        "level": "onlisans",
        "title": "Eczane Hizmetleri önlisans programından mezun olmak",
        "departments": ["Eczane Hizmetleri"],
    },
    {
        "code": "3063",
        "level": "onlisans",
        "title": "Odyometri önlisans programından mezun olmak",
        "departments": ["Odyometri"],
    },
    {
        "code": "3065",
        "level": "onlisans",
        "title": "Optisyenlik önlisans programından mezun olmak",
        "departments": ["Optisyenlik"],
    },
    {
        "code": "3067",
        "level": "onlisans",
        "title": "Yaşlı Bakımı / Evde Hasta Bakımı önlisans programından mezun olmak",
        "departments": ["Yaşlı Bakımı", "Evde Hasta Bakımı"],
    },
    {
        "code": "3069",
        "level": "onlisans",
        "title": "Sağlık Kurumları İşletmeciliği önlisans programından mezun olmak",
        "departments": ["Sağlık Kurumları İşletmeciliği"],
    },
    {
        "code": "3071",
        "level": "onlisans",
        "title": "Patoloji Laboratuvar Teknikleri önlisans programından mezun olmak",
        "departments": ["Patoloji Laboratuvar Teknikleri"],
    },
    {
        "code": "3073",
        "level": "onlisans",
        "title": "Çevre Sağlığı önlisans programından mezun olmak",
        "departments": ["Çevre Sağlığı"],
    },
    {
        "code": "3075",
        "level": "onlisans",
        "title": "Laborant ve Veteriner Sağlık önlisans programından mezun olmak",
        "departments": ["Laborant ve Veteriner Sağlık"],
    },
    {
        "code": "3173",
        "level": "onlisans",
        "title": "Muhasebe, İşletme, Maliye, Büro Yönetimi gibi idari önlisans programlarından mezun olmak",
        "departments": ["Muhasebe", "İşletme", "Maliye", "Büro Yönetimi"],
    },
    {
        "code": "3179",
        "level": "onlisans",
        "title": "Özel Güvenlik ve Koruma / Savunma ve Güvenlik önlisans programından mezun olmak",
        "departments": ["Özel Güvenlik ve Koruma"],
    },
    {
        "code": "3249",
        "level": "onlisans",
        "title": "Bilgisayar Programcılığı, Bilgisayar Teknolojisi, Bilişim Güvenliği Teknolojisi önlisans programından mezun olmak",
        "departments": ["Bilgisayar Programcılığı", "Bilgisayar Teknolojisi", "Bilişim"],
    },
    {
        "code": "3251",
        "level": "onlisans",
        "title": "Web Tasarımı ve Kodlama / İnternet ve Ağ Teknolojileri önlisans programından mezun olmak",
        "departments": ["Web Tasarımı ve Kodlama", "İnternet ve Ağ Teknolojileri"],
    },
    {
        "code": "3253",
        "level": "onlisans",
        "title": "Coğrafi Bilgi Sistemleri önlisans programından mezun olmak",
        "departments": ["Coğrafi Bilgi Sistemleri"],
    },
    {
        "code": "3291",
        "level": "onlisans",
        "title": "Elektrik / Elektrik Enerjisi Üretim, İletim ve Dağıtımı önlisans programından mezun olmak",
        "departments": ["Elektrik", "Elektrik Teknikerliği"],
    },
    {
        "code": "3293",
        "level": "onlisans",
        "title": "Elektronik Teknolojisi / Elektronik Haberleşme Teknolojisi önlisans programından mezun olmak",
        "departments": ["Elektronik Teknolojisi", "Elektronik Haberleşme"],
    },
    {
        "code": "3295",
        "level": "onlisans",
        "title": "Mekatronik / Kontrol ve Otomasyon Teknolojisi önlisans programından mezun olmak",
        "departments": ["Mekatronik", "Kontrol ve Otomasyon"],
    },
    {
        "code": "3297",
        "level": "onlisans",
        "title": "Biyomedikal Cihaz Teknolojisi önlisans programından mezun olmak",
        "departments": ["Biyomedikal Cihaz Teknolojisi"],
    },
    {
        "code": "3301",
        "level": "onlisans",
        "title": "Makine / Makine Resmi ve Konstrüksiyon önlisans programından mezun olmak",
        "departments": ["Makine", "Makine Teknikerliği"],
    },
    {
        "code": "3305",
        "level": "onlisans",
        "title": "İklimlendirme ve Soğutma Teknolojisi önlisans programından mezun olmak",
        "departments": ["İklimlendirme ve Soğutma Teknolojisi"],
    },
    {
        "code": "3309",
        "level": "onlisans",
        "title": "Otomotiv Teknolojisi önlisans programından mezun olmak",
        "departments": ["Otomotiv Teknolojisi"],
    },
    {
        "code": "3313",
        "level": "onlisans",
        "title": "İnşaat Teknolojisi önlisans programından mezun olmak",
        "departments": ["İnşaat Teknolojisi", "İnşaat Teknikerliği"],
    },
    {
        "code": "3317",
        "level": "onlisans",
        "title": "Harita ve Kadastro / Tapu ve Kadastro önlisans programından mezun olmak",
        "departments": ["Harita ve Kadastro", "Tapu ve Kadastro"],
    },
    {
        "code": "3319",
        "level": "onlisans",
        "title": "Mimari Restorasyon / Yapı Ressamlığı önlisans programından mezun olmak",
        "departments": ["Mimari Restorasyon", "Yapı Ressamlığı"],
    },
    {
        "code": "3323",
        "level": "onlisans",
        "title": "Kimya Teknolojisi önlisans programından mezun olmak",
        "departments": ["Kimya Teknolojisi"],
    },
    {
        "code": "3327",
        "level": "onlisans",
        "title": "Gıda Teknolojisi önlisans programından mezun olmak",
        "departments": ["Gıda Teknolojisi"],
    },
    {
        "code": "3331",
        "level": "onlisans",
        "title": "Çevre Koruma ve Kontrol önlisans programından mezun olmak",
        "departments": ["Çevre Koruma ve Kontrol"],
    },
    {
        "code": "3335",
        "level": "onlisans",
        "title": "İş Sağlığı ve Güvenliği önlisans programından mezun olmak",
        "departments": ["İş Sağlığı ve Güvenliği"],
    },
    {
        "code": "3337",
        "level": "onlisans",
        "title": "Sivil Savunma ve İtfaiyecilik önlisans programından mezun olmak",
        "departments": ["Sivil Savunma ve İtfaiyecilik", "İtfaiyecilik"],
    },
    {
        "code": "3339",
        "level": "onlisans",
        "title": "Ormancılık ve Orman Ürünleri önlisans programından mezun olmak",
        "departments": ["Ormancılık"],
    },
    {
        "code": "3341",
        "level": "onlisans",
        "title": "Raylı Sistemler Teknolojisi / Makine / Elektrik önlisans programından mezun olmak",
        "departments": ["Raylı Sistemler"],
    },
    {
        "code": "3343",
        "level": "onlisans",
        "title": "Aşçılık önlisans programından mezun olmak",
        "departments": ["Aşçılık"],
    },
    # --- Lisans (4xxx) ---
    {
        "code": "4125",
        "level": "lisans",
        "title": "Türk Dili ve Edebiyatı / Çağdaş Türk Lehçeleri lisans programından mezun olmak",
        "departments": ["Türk Dili ve Edebiyatı"],
    },
    {
        "code": "4129",
        "level": "lisans",
        "title": "Tarih lisans programından mezun olmak",
        "departments": ["Tarih"],
    },
    {
        "code": "4131",
        "level": "lisans",
        "title": "Coğrafya lisans programından mezun olmak",
        "departments": ["Coğrafya"],
    },
    {
        "code": "4141",
        "level": "lisans",
        "title": "Bilgi ve Belge Yönetimi / Kütüphanecilik / Arşivcilik lisans programından mezun olmak",
        "departments": ["Bilgi ve Belge Yönetimi", "Kütüphanecilik"],
    },
    {
        "code": "4151",
        "level": "lisans",
        "title": "İngiliz Dili ve Edebiyatı / Mütercim-Tercümanlık (İngilizce) lisans programından mezun olmak",
        "departments": ["İngiliz Dili ve Edebiyatı", "Mütercim Tercümanlık"],
    },
    {
        "code": "4177",
        "level": "lisans",
        "title": "İlahiyat / İslami İlimler lisans programından mezun olmak",
        "departments": ["İlahiyat", "İslami İlimler"],
    },
    {
        "code": "4261",
        "level": "lisans",
        "title": "Halkla İlişkiler ve Tanıtım / Reklamcılık lisans programından mezun olmak",
        "departments": ["Halkla İlişkiler ve Tanıtım"],
    },
    {
        "code": "4265",
        "level": "lisans",
        "title": "Gazetecilik / İletişim Bilimleri lisans programından mezun olmak",
        "departments": ["Gazetecilik", "İletişim"],
    },
    {
        "code": "4269",
        "level": "lisans",
        "title": "Radyo, Televizyon ve Sinema lisans programından mezun olmak",
        "departments": ["Radyo Televizyon ve Sinema"],
    },
    {
        "code": "4301",
        "level": "lisans",
        "title": "Okul Öncesi Öğretmenliği lisans programından mezun olmak",
        "departments": ["Okul Öncesi Öğretmenliği"],
    },
    {
        "code": "4305",
        "level": "lisans",
        "title": "Rehberlik ve Psikolojik Danışmanlık (PDR) lisans programından mezun olmak",
        "departments": ["Rehberlik ve Psikolojik Danışmanlık", "PDR"],
    },
    {
        "code": "4311",
        "level": "lisans",
        "title": "Beden Eğitimi ve Spor Öğretmenliği / Antrenörlük / Spor Yöneticiliği lisans programından mezun olmak",
        "departments": ["Beden Eğitimi ve Spor", "Spor Bilimleri"],
    },
    {
        "code": "4351",
        "level": "lisans",
        "title": "Turizm İşletmeciliği / Konaklama İşletmeciliği lisans programından mezun olmak",
        "departments": ["Turizm İşletmeciliği"],
    },
    {
        "code": "4415",
        "level": "lisans",
        "title": "Hukuk lisans programından mezun olmak",
        "departments": ["Hukuk"],
    },
    {
        "code": "4419",
        "level": "lisans",
        "title": "İktisat / Ekonomi lisans programından mezun olmak",
        "departments": ["İktisat", "Ekonomi"],
    },
    {
        "code": "4421",
        "level": "lisans",
        "title": "Ekonomi, İktisat, İş İdaresi ve İktisat, Ekonomi ve Finans lisans programlarının birinden mezun olmak",
        "departments": ["İktisat", "Ekonomi", "Ekonomi ve Finans"],
    },
    {
        "code": "4426",
        "level": "lisans",
        "title": "İktisat, İşletme, Maliye, Kamu Yönetimi, Çalışma Ekonomisi veya Uluslararası İlişkiler lisans programından mezun olmak",
        "departments": [
            "İktisat",
            "İşletme",
            "Maliye",
            "Kamu Yönetimi",
            "Çalışma Ekonomisi ve Endüstri İlişkileri",
            "Uluslararası İlişkiler",
        ],
    },
    {
        "code": "4429",
        "level": "lisans",
        "title": "Çalışma Ekonomisi ve Endüstri İlişkileri lisans programından mezun olmak",
        "departments": ["Çalışma Ekonomisi ve Endüstri İlişkileri"],
    },
    {
        "code": "4431",
        "level": "lisans",
        "title": "İşletme, İşletmecilik, İş İdaresi, Yönetim ve Organizasyon lisans programından mezun olmak",
        "departments": ["İşletme", "İşletme Yönetimi"],
    },
    {
        "code": "4439",
        "level": "lisans",
        "title": "Bankacılık, Bankacılık ve Finans, Sermaye Piyasası lisans programından mezun olmak",
        "departments": ["Bankacılık ve Finans"],
    },
    {
        "code": "4443",
        "level": "lisans",
        "title": "İstatistik / İstatistik ve Bilgisayar Bilimleri lisans programından mezun olmak",
        "departments": ["İstatistik"],
    },
    {
        "code": "4445",
        "level": "lisans",
        "title": "Ekonometri lisans programından mezun olmak",
        "departments": ["Ekonometri"],
    },
    {
        "code": "4449",
        "level": "lisans",
        "title": "Uluslararası İlişkiler / Siyaset Bilimi ve Uluslararası İlişkiler lisans programından mezun olmak",
        "departments": ["Uluslararası İlişkiler"],
    },
    {
        "code": "4459",
        "level": "lisans",
        "title": "Maliye / Maliye-Muhasebe lisans programından mezun olmak",
        "departments": ["Maliye"],
    },
    {
        "code": "4463",
        "level": "lisans",
        "title": "Kamu Yönetimi / Siyaset Bilimi ve Kamu Yönetimi lisans programından mezun olmak",
        "departments": ["Kamu Yönetimi", "Siyaset Bilimi ve Kamu Yönetimi"],
    },
    {
        "code": "4471",
        "level": "lisans",
        "title": "Uluslararası Ticaret / Uluslararası Ticaret ve Lojistik lisans programından mezun olmak",
        "departments": ["Uluslararası Ticaret", "Lojistik Yönetimi"],
    },
    {
        "code": "4477",
        "level": "lisans",
        "title": "Sağlık Yönetimi / Sağlık İdaresi lisans programından mezun olmak",
        "departments": ["Sağlık Yönetimi", "Sağlık İdaresi"],
    },
    {
        "code": "4503",
        "level": "lisans",
        "title": "Hukuk, Siyasal Bilgiler, İktisat, İşletme, İktisadi ve İdari Bilimler fakültelerinden mezun olmak",
        "departments": ["Hukuk", "İktisat", "İşletme", "Maliye", "Kamu Yönetimi", "Uluslararası İlişkiler"],
    },
    {
        "code": "4507",
        "level": "lisans",
        "title": "Matematik / Uygulamalı Matematik lisans programından mezun olmak",
        "departments": ["Matematik"],
    },
    {
        "code": "4511",
        "level": "lisans",
        "title": "Fizik / Fizik Mühendisliği lisans programından mezun olmak",
        "departments": ["Fizik", "Fizik Mühendisliği"],
    },
    {
        "code": "4515",
        "level": "lisans",
        "title": "Kimya lisans programından mezun olmak",
        "departments": ["Kimya"],
    },
    {
        "code": "4519",
        "level": "lisans",
        "title": "Biyoloji / Moleküler Biyoloji ve Genetik lisans programından mezun olmak",
        "departments": ["Biyoloji", "Moleküler Biyoloji ve Genetik"],
    },
    {
        "code": "4531",
        "level": "lisans",
        "title": "Bilgisayar Mühendisliği, Bilgisayar Bilimleri Mühendisliği veya Bilgisayar ve Enformatik Mühendisliği mezunu olmak",
        "departments": ["Bilgisayar Mühendisliği", "Bilgisayar Bilimleri"],
    },
    {
        "code": "4533",
        "level": "lisans",
        "title": "Yazılım Mühendisliği lisans programından mezun olmak",
        "departments": ["Yazılım Mühendisliği"],
    },
    {
        "code": "4535",
        "level": "lisans",
        "title": "Bilişim Sistemleri Mühendisliği / Yönetim Bilişim Sistemleri lisans programından mezun olmak",
        "departments": ["Bilişim Sistemleri Mühendisliği", "Yönetim Bilişim Sistemleri"],
    },
    {
        "code": "4537",
        "level": "lisans",
        "title": "Bilgisayar, Yazılım, Elektrik-Elektronik veya Elektronik Haberleşme Mühendisliği mezunu olmak",
        "departments": [
            "Bilgisayar Mühendisliği",
            "Yazılım Mühendisliği",
            "Elektrik-Elektronik Mühendisliği",
        ],
    },
    {
        "code": "4571",
        "level": "lisans",
        "title": "Tıp Fakültesi lisans programından mezun olmak",
        "departments": ["Tıp"],
    },
    {
        "code": "4573",
        "level": "lisans",
        "title": "Diş Hekimliği lisans programından mezun olmak",
        "departments": ["Diş Hekimliği"],
    },
    {
        "code": "4575",
        "level": "lisans",
        "title": "Eczacılık lisans programından mezun olmak",
        "departments": ["Eczacılık"],
    },
    {
        "code": "4577",
        "level": "lisans",
        "title": "Veteriner Fakültesi lisans programından mezun olmak",
        "departments": ["Veterinerlik"],
    },
    {
        "code": "4587",
        "level": "lisans",
        "title": "Sosyal Hizmet / Sosyal Hizmetler lisans programından mezun olmak",
        "departments": ["Sosyal Hizmet"],
    },
    {
        "code": "4589",
        "level": "lisans",
        "title": "Psikoloji lisans programından mezun olmak",
        "departments": ["Psikoloji"],
    },
    {
        "code": "4591",
        "level": "lisans",
        "title": "Sosyoloji lisans programından mezun olmak",
        "departments": ["Sosyoloji"],
    },
    {
        "code": "4595",
        "level": "lisans",
        "title": "Odyoloji lisans programından mezun olmak",
        "departments": ["Odyoloji"],
    },
    {
        "code": "4597",
        "level": "lisans",
        "title": "Dil ve Konuşma Terapisi lisans programından mezun olmak",
        "departments": ["Dil ve Konuşma Terapisi"],
    },
    {
        "code": "4601",
        "level": "lisans",
        "title": "Hemşirelik / Sağlık Memurluğu lisans programından mezun olmak",
        "departments": ["Hemşirelik"],
    },
    {
        "code": "4603",
        "level": "lisans",
        "title": "Ebelik lisans programından mezun olmak",
        "departments": ["Ebelik"],
    },
    {
        "code": "4605",
        "level": "lisans",
        "title": "Fizyoterapi ve Rehabilitasyon lisans programından mezun olmak",
        "departments": ["Fizyoterapi ve Rehabilitasyon"],
    },
    {
        "code": "4607",
        "level": "lisans",
        "title": "Beslenme ve Diyetetik lisans programından mezun olmak",
        "departments": ["Beslenme ve Diyetetik"],
    },
    {
        "code": "4609",
        "level": "lisans",
        "title": "Çocuk Gelişimi lisans programından mezun olmak",
        "departments": ["Çocuk Gelişimi"],
    },
    {
        "code": "4611",
        "level": "lisans",
        "title": "Elektrik Mühendisliği veya Elektrik-Elektronik Mühendisliği lisans programından mezun olmak",
        "departments": ["Elektrik Mühendisliği", "Elektrik-Elektronik Mühendisliği"],
    },
    {
        "code": "4613",
        "level": "lisans",
        "title": "Elektronik Mühendisliği / Elektronik ve Haberleşme Mühendisliği lisans programından mezun olmak",
        "departments": ["Elektronik Mühendisliği", "Elektronik ve Haberleşme Mühendisliği"],
    },
    {
        "code": "4615",
        "level": "lisans",
        "title": "Kontrol ve Otomasyon Mühendisliği lisans programından mezun olmak",
        "departments": ["Kontrol ve Otomasyon Mühendisliği"],
    },
    {
        "code": "4619",
        "level": "lisans",
        "title": "Biyomedikal Mühendisliği lisans programından mezun olmak",
        "departments": ["Biyomedikal Mühendisliği"],
    },
    {
        "code": "4639",
        "level": "lisans",
        "title": "Makine Mühendisliği lisans programından mezun olmak",
        "departments": ["Makine Mühendisliği"],
    },
    {
        "code": "4645",
        "level": "lisans",
        "title": "Mekatronik Mühendisliği lisans programından mezun olmak",
        "departments": ["Mekatronik Mühendisliği"],
    },
    {
        "code": "4669",
        "level": "lisans",
        "title": "İnşaat Mühendisliği lisans programından mezun olmak",
        "departments": ["İnşaat Mühendisliği"],
    },
    {
        "code": "4673",
        "level": "lisans",
        "title": "Harita Mühendisliği / Geomatik Mühendisliği / Jeodezi ve Fotogrametri Mühendisliği mezunu olmak",
        "departments": ["Harita Mühendisliği", "Geomatik Mühendisliği"],
    },
    {
        "code": "4677",
        "level": "lisans",
        "title": "Çevre Mühendisliği lisans programından mezun olmak",
        "departments": ["Çevre Mühendisliği"],
    },
    {
        "code": "4689",
        "level": "lisans",
        "title": "Endüstri Mühendisliği lisans programından mezun olmak",
        "departments": ["Endüstri Mühendisliği"],
    },
    {
        "code": "4695",
        "level": "lisans",
        "title": "Kimya Mühendisliği lisans programından mezun olmak",
        "departments": ["Kimya Mühendisliği"],
    },
    {
        "code": "4703",
        "level": "lisans",
        "title": "Gıda Mühendisliği lisans programından mezun olmak",
        "departments": ["Gıda Mühendisliği"],
    },
    {
        "code": "4707",
        "level": "lisans",
        "title": "Ziraat Mühendisliği lisans programından mezun olmak",
        "departments": ["Ziraat Mühendisliği"],
    },
    {
        "code": "4711",
        "level": "lisans",
        "title": "Orman Mühendisliği / Orman Endüstrisi Mühendisliği lisans programından mezun olmak",
        "departments": ["Orman Mühendisliği"],
    },
    {
        "code": "4715",
        "level": "lisans",
        "title": "Jeoloji Mühendisliği lisans programından mezun olmak",
        "departments": ["Jeoloji Mühendisliği"],
    },
    {
        "code": "4719",
        "level": "lisans",
        "title": "Jeofizik Mühendisliği lisans programından mezun olmak",
        "departments": ["Jeofizik Mühendisliği"],
    },
    {
        "code": "4723",
        "level": "lisans",
        "title": "Maden Mühendisliği lisans programından mezun olmak",
        "departments": ["Maden Mühendisliği"],
    },
    {
        "code": "4727",
        "level": "lisans",
        "title": "Metalurji ve Malzeme Mühendisliği lisans programından mezun olmak",
        "departments": ["Metalurji ve Malzeme Mühendisliği"],
    },
    {
        "code": "4731",
        "level": "lisans",
        "title": "Mimarlık lisans programından mezun olmak",
        "departments": ["Mimarlık"],
    },
    {
        "code": "4733",
        "level": "lisans",
        "title": "Şehir ve Bölge Planlama lisans programından mezun olmak",
        "departments": ["Şehir ve Bölge Planlama"],
    },
    {
        "code": "4735",
        "level": "lisans",
        "title": "Peyzaj Mimarlığı lisans programından mezun olmak",
        "departments": ["Peyzaj Mimarlığı"],
    },
    {
        "code": "4737",
        "level": "lisans",
        "title": "İç Mimarlık / İç Mimarlık ve Çevre Tasarımı lisans programından mezun olmak",
        "departments": ["İç Mimarlık"],
    },
    # --- Özel Koşullar, Sertifika, Ehliyet, Yabancı Dil (1xxx, 6xxx, 7xxx) ---
    {
        "code": "1101",
        "level": "ozel",
        "title": "Cinsiyeti Erkek olmak",
        "departments": ["Özel Koşul (Erkek)"],
    },
    {
        "code": "1103",
        "level": "ozel",
        "title": "Cinsiyeti Kadın olmak",
        "departments": ["Özel Koşul (Kadın)"],
    },
    {
        "code": "6225",
        "level": "ozel",
        "title": "M.E.B.'den onaylı Bilgisayar İşletmeni Sertifikası sahibi olmak veya okulda bilgisayar dersi görmüş olmak",
        "departments": ["Bilgisayar İşletmeni Sertifikası"],
    },
    {
        "code": "6506",
        "level": "ozel",
        "title": "B sınıfı sürücü belgesine sahip olmak",
        "departments": ["B Sınıfı Ehliyet", "Şoför"],
    },
    {
        "code": "6510",
        "level": "ozel",
        "title": "C sınıfı sürücü belgesine sahip olmak",
        "departments": ["C Sınıfı Ehliyet", "Şoför"],
    },
    {
        "code": "6514",
        "level": "ozel",
        "title": "D sınıfı sürücü belgesine sahip olmak",
        "departments": ["D Sınıfı Ehliyet", "Şoför"],
    },
    {
        "code": "6518",
        "level": "ozel",
        "title": "E sınıfı (veya yeni tip D) sürücü belgesine sahip olmak",
        "departments": ["E Sınıfı Ehliyet", "Şoför"],
    },
    {
        "code": "6551",
        "level": "ozel",
        "title": "Özel Güvenlik Görevlisi Kimlik Kartına sahip olmak (Silahlı/Silahsız)",
        "departments": ["Özel Güvenlik Görevlisi", "Koruma ve Güvenlik"],
    },
    {
        "code": "6553",
        "level": "ozel",
        "title": "Silahlı Özel Güvenlik Görevlisi Kimlik Kartına sahip olmak",
        "departments": ["Silahlı Özel Güvenlik"],
    },
    {
        "code": "7111",
        "level": "ozel",
        "title": "Son 5 yıl içinde KPDS/YDS en az C düzeyinde yabancı dil belgesine sahip olmak",
        "departments": ["YDS C Düzeyi (70+)"],
    },
    {
        "code": "7113",
        "level": "ozel",
        "title": "Son 5 yıl içinde KPDS/YDS en az D düzeyinde yabancı dil belgesine sahip olmak",
        "departments": ["YDS D Düzeyi (60+)"],
    },
    {
        "code": "7115",
        "level": "ozel",
        "title": "Son 5 yıl içinde KPDS/YDS en az B düzeyinde yabancı dil belgesine sahip olmak",
        "departments": ["YDS B Düzeyi (80+)"],
    },
    {
        "code": "7117",
        "level": "ozel",
        "title": "Son 5 yıl içinde KPDS/YDS en az A düzeyinde yabancı dil belgesine sahip olmak",
        "departments": ["YDS A Düzeyi (90+)"],
    },
    {
        "code": "7225",
        "level": "ozel",
        "title": "Güvenlik tahkikatının olumlu sonuçlanması",
        "departments": ["Güvenlik Soruşturması"],
    },
    {
        "code": "7257",
        "level": "ozel",
        "title": "Seyahate ve arazide çalışmaya elverişli olmak",
        "departments": ["Arazi ve Seyahat Şartı"],
    },
    {
        "code": "7300",
        "level": "ozel",
        "title": "İlgili kadro için KPSS Tercih Kılavuzunda belirtilen özel şartları taşımak (Yaş/Vardiya/Sağlık vb.)",
        "departments": ["ÖSYM Kılavuz Özel Şartı"],
    },
    {
        "code": "7302",
        "level": "ozel",
        "title": "Vardiyalı çalışmaya engel bir durumu bulunmamak",
        "departments": ["Vardiyalı Çalışma"],
    },
    {
        "code": "7322",
        "level": "ozel",
        "title": "Daktilo veya bilgisayar dersini başarıyla tamamlamış ya da MEB onaylı sertifikaya sahip olmak",
        "departments": ["Bilgisayar / Daktilo Sertifikası"],
    },
    {
        "code": "7361",
        "level": "ozel",
        "title": "24 saat esasına göre nöbet ve vardiya usulü çalışabilecek olmak",
        "departments": ["Nöbet / 24 Saat Vardiya"],
    },
]

_NITELIK_INDEX: list[tuple[str, dict]] = [
    (
        _normalize_tr(
            f"{item['code']} {item['level']} {item['title']} {' '.join(item['departments'])}"
        ),
        item,
    )
    for item in NITELIK_KODLARI
]

NITELIK_BY_CODE: dict[str, dict] = {item["code"]: item for item in NITELIK_KODLARI}


def search_nitelik_kodlari(query: str = "", level: str | None = None, limit: int = 50) -> list[dict]:
    """Search qualification codes by code, title, or department with Turkish normalization."""
    norm_q = _normalize_tr(query)
    results: list[dict] = []

    for haystack, item in _NITELIK_INDEX:
        if level and item["level"] != level:
            continue
        if not norm_q or norm_q in haystack:
            results.append(item)
            if len(results) >= limit:
                break

    # Prioritize exact code prefix matches first when query is numeric/short
    if norm_q:
        results.sort(
            key=lambda x: (
                0 if x["code"] == norm_q else 1 if x["code"].startswith(norm_q) else 2,
                x["code"],
            )
        )
    return results
