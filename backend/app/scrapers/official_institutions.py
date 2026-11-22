"""Built-in network of 74 verified Turkish official ministries, agencies, metropolitan municipalities, and university personnel departments."""

from __future__ import annotations

import asyncio
import datetime
import logging
import re
import urllib.parse

from bs4 import BeautifulSoup

from app.scrapers.base import (
    HttpClient,
    RawAnnouncement,
    extract_pdf_text,
    extract_quota_from_text,
    html_to_text,
    infer_application_channel,
    infer_category,
    is_cancelled_announcement_title,
    normalize_whitespace,
    parse_turkish_date,
    stable_external_id,
    turkish_lower,
)

logger = logging.getLogger(__name__)

INSTITUTION_CONCURRENCY = 22
INSTITUTION_TIMEOUT = 8.0
MAX_PER_INSTITUTION = 5
MAX_CANDIDATE_DETAILS_PER_GROUP = 45
STALE_DAYS_LIMIT = 90

# Positive recruitment signals required on institution links
POSITIVE_RECRUITMENT_TERMS = (
    "alım ilanı",
    "personel alımı",
    "personel alım",
    "memur alımı",
    "memur alım",
    "işçi alımı",
    "işçi alım",
    "sözleşmeli personel",
    "zabıta memuru",
    "itfaiye eri",
    "uzman yardımcısı",
    "müfettiş yardımcısı",
    "denetmen yardımcısı",
    "denetçi yardımcısı",
    "kpss",
    "4/b",
    "açıktan atama",
    "personel temin",
    "memur temin",
    "sözleşmeli bilişim",
    "öğretim üyesi alım",
    "öğretim elemanı alım",
    "araştırma görevlisi alım",
)

# Strictly excluded noise signals (results, internal transfers, tenders, internships, etc.)
NEGATIVE_NOISE_TERMS = (
    "sonuç",
    "sonucu",
    "sonuçları",
    "kazanan",
    "asil",
    "yedek",
    "nihai",
    "mülakat",
    "sözlü sınav",
    "uygulamalı sınav",
    "sözlü/uygulama sınavı",
    "uygulama sınavı",
    "uygulama sınavı hk",
    "sınav tarih",
    "sınav yeri",
    "sınav yerleri",
    "evrak teslim",
    "belge teslim",
    "atamaya esas",
    "göreve başlama",
    "işe başlatılacak",
    "arşiv araştırması",
    "güvenlik soruşturması",
    "kadroya geçiş",
    "kadro geçiş",
    "görevde yükselme",
    "unvan değişikliği",
    "değerlendirme komisyonu",
    "inceleme ve değerlendirme",
    "yabancı uyruklu",
    "kurum içi",
    "naklen",
    "yer değiştirme",
    "tayin",
    "staj",
    "burs",
    "ihale",
    "satış",
    "kiralama",
    "iptal",
    "tebligat",
    "vefat",
    "taziye",
    "başsağlığı",
    "ilanen",
)

DETAIL_NEGATIVE_TERMS = (
    "yerleştirme sonuç",
    "mülakat sonuç",
    "sözlü sınav sonuç",
    "nihai başarı listesi",
    "nihai liste",
    "atama kurası sonuç",
    "görevde yükselme",
    "unvan değişikliği",
    "değerlendirme komisyonu",
    "inceleme ve değerlendirme",
    "yabancı uyruklu",
    "iptal edilmiştir",
)

OFFICIAL_INSTITUTIONS_CATALOG: list[dict] = [
    {
        "group_key": "bakanliklar",
        "group_label": "Bakanlıklar (15)",
        "source_name": "bakanliklar_kurumlar",
        "items": [
            {"name": "Adalet Bakanlığı PGM", "url": "https://pgm.adalet.gov.tr/", "city": "Ankara"},
            {"name": "Adalet Bakanlığı CTE", "url": "https://cte.adalet.gov.tr/", "city": "Ankara"},
            {"name": "Sağlık Bakanlığı YHGM", "url": "https://yhgm.saglik.gov.tr/", "city": "Ankara"},
            {"name": "Milli Eğitim Bakanlığı", "url": "https://www.meb.gov.tr/", "city": "Ankara"},
            {"name": "İçişleri Bakanlığı", "url": "https://www.icisleri.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Tarım ve Orman Bakanlığı", "url": "https://www.tarimorman.gov.tr/", "city": "Ankara"},
            {"name": "Aile ve Sosyal Hizmetler Bakanlığı", "url": "https://www.aile.gov.tr/duyurular/", "city": "Ankara"},
            {"name": "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı", "url": "https://csb.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Ulaştırma ve Altyapı Bakanlığı", "url": "https://www.uab.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Ticaret Bakanlığı", "url": "https://ticaret.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Gençlik ve Spor Bakanlığı", "url": "https://www.gsb.gov.tr/", "city": "Ankara"},
            {"name": "Kültür ve Turizm Bakanlığı", "url": "https://www.ktb.gov.tr/", "city": "Ankara"},
            {"name": "Çalışma ve Sosyal Güvenlik Bakanlığı", "url": "https://www.csgb.gov.tr/duyurular/", "city": "Ankara"},
            {"name": "Enerji ve Tabii Kaynaklar Bakanlığı", "url": "https://www.enerji.gov.tr/", "city": "Ankara"},
            {"name": "Dışişleri Bakanlığı Kariyer", "url": "https://kariyer.mfa.gov.tr/", "city": "Ankara"},
        ],
    },
    {
        "group_key": "kamu_kurumlari",
        "group_label": "Genel Müdürlükler & Başkanlıklar (22)",
        "source_name": "bakanliklar_kurumlar",
        "items": [
            {"name": "Sosyal Güvenlik Kurumu (SGK)", "url": "https://www.sgk.gov.tr/Duyuru", "city": "Ankara"},
            {"name": "AFAD", "url": "https://www.afad.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Devlet Su İşleri (DSİ)", "url": "https://www.dsi.gov.tr/", "city": "Ankara"},
            {"name": "Orman Genel Müdürlüğü (OGM)", "url": "https://www.ogm.gov.tr/tr/duyurular", "city": "Ankara"},
            {"name": "Karayolları Genel Müdürlüğü (KGM)", "url": "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Root/Duyurular.aspx", "city": "Ankara"},
            {"name": "Tapu ve Kadastro Genel Müdürlüğü", "url": "https://www.tkgm.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Diyanet İşleri Başkanlığı", "url": "https://www.diyanet.gov.tr/", "city": "Ankara"},
            {"name": "Diyanet İKGM", "url": "https://insankaynaklari.diyanet.gov.tr/", "city": "Ankara"},
            {"name": "Emniyet Genel Müdürlüğü (EGM)", "url": "https://www.egm.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Jandarma Genel Komutanlığı", "url": "https://www.jandarma.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Sahil Güvenlik Komutanlığı", "url": "https://www.sg.gov.tr/duyurular", "city": "Ankara"},
            {"name": "TÜİK", "url": "https://www.tuik.gov.tr/", "city": "Ankara"},
            {"name": "DHMİ", "url": "https://www.dhmi.gov.tr/", "city": "Ankara"},
            {"name": "TEİAŞ", "url": "https://www.teias.gov.tr/duyurular", "city": "Ankara"},
            {"name": "EÜAŞ", "url": "https://www.euas.gov.tr/tr-TR/duyurular", "city": "Ankara"},
            {"name": "BOTAŞ", "url": "https://www.botas.gov.tr/", "city": "Ankara"},
            {"name": "Nüfus ve Vatandaşlık İşleri", "url": "https://www.nvi.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Göç İdaresi Başkanlığı", "url": "https://www.goc.gov.tr/duyurular", "city": "Ankara"},
            {"name": "PTT", "url": "https://www.ptt.gov.tr/duyurular", "city": "Ankara"},
            {"name": "TÜBİTAK", "url": "https://www.tubitak.gov.tr/", "city": "Ankara"},
            {"name": "Adli Tıp Kurumu", "url": "https://www.atk.gov.tr/", "city": "İstanbul"},
            {"name": "Yükseköğretim Kurulu (YÖK)", "url": "https://www.yok.gov.tr/", "city": "Ankara"},
        ],
    },
    {
        "group_key": "yargi_kurullar",
        "group_label": "Yargı, Yasama & Üst Kurullar (13)",
        "source_name": "kurullar_kitler",
        "items": [
            {"name": "TBMM", "url": "https://www.tbmm.gov.tr/", "city": "Ankara"},
            {"name": "Sayıştay Başkanlığı", "url": "https://www.sayistay.gov.tr/", "city": "Ankara"},
            {"name": "Yargıtay Başkanlığı", "url": "https://www.yargitay.gov.tr/", "city": "Ankara"},
            {"name": "Anayasa Mahkemesi", "url": "https://www.anayasa.gov.tr/tr/duyurular/", "city": "Ankara"},
            {"name": "Hakimler ve Savcılar Kurulu (HSK)", "url": "https://www.hsk.gov.tr/", "city": "Ankara"},
            {"name": "Sermaye Piyasası Kurulu (SPK)", "url": "https://spk.gov.tr/duyurular", "city": "Ankara"},
            {"name": "EPDK", "url": "https://www.epdk.gov.tr/Detay/Icerik/1-1271/duyurular", "city": "Ankara"},
            {"name": "BTK", "url": "https://www.btk.gov.tr/duyurular", "city": "Ankara"},
            {"name": "Rekabet Kurumu", "url": "https://www.rekabet.gov.tr/tr/Duyurular", "city": "Ankara"},
            {"name": "KVKK", "url": "https://www.kvkk.gov.tr/Duyurular", "city": "Ankara"},
            {"name": "Kamu İhale Kurumu", "url": "https://www.ihale.gov.tr/", "city": "Ankara"},
            {"name": "Savunma Sanayii Başkanlığı (SSB)", "url": "https://www.ssb.gov.tr/", "city": "Ankara"},
            {"name": "Nükleer Düzenleme Kurumu (NDK)", "url": "https://www.ndk.org.tr/", "city": "Ankara"},
        ],
    },
    {
        "group_key": "kitler",
        "group_label": "KİT'ler & Kamu Kuruluşları (22)",
        "source_name": "kurullar_kitler",
        "items": [
            {"name": "İŞKUR", "url": "https://www.iskur.gov.tr/duyurular/", "city": "Ankara"},
            {"name": "TÜRASAŞ", "url": "https://www.turasas.gov.tr/duyurular", "city": "Ankara"},
            {"name": "MKE", "url": "https://www.mke.gov.tr/", "city": "Ankara"},
            {"name": "TPAO", "url": "https://www.tpao.gov.tr/", "city": "Ankara"},
            {"name": "ETİ MADEN", "url": "https://www.etimaden.gov.tr/duyurular", "city": "Ankara"},
            {"name": "TTK (Türkiye Taşkömürü)", "url": "https://www.taskomuru.gov.tr/", "city": "Zonguldak"},
            {"name": "TKİ (Türkiye Kömür İşletmeleri)", "url": "https://www.tki.gov.tr/", "city": "Ankara"},
            {"name": "TÜRKŞEKER", "url": "https://www.turkseker.gov.tr/", "city": "Ankara"},
            {"name": "TMO (Toprak Mahsulleri Ofisi)", "url": "https://www.tmo.gov.tr/", "city": "Ankara"},
            {"name": "ÇAYKUR", "url": "https://www.caykur.gov.tr/", "city": "Rize"},
            {"name": "Et ve Süt Kurumu (ESK)", "url": "https://www.esk.gov.tr/", "city": "Ankara"},
            {"name": "TİGEM", "url": "https://www.tigem.gov.tr/", "city": "Ankara"},
            {"name": "DMO (Devlet Malzeme Ofisi)", "url": "https://www.dmo.gov.tr/", "city": "Ankara"},
            {"name": "TSE", "url": "https://www.tse.org.tr/", "city": "Ankara"},
            {"name": "TÜRKPATENT", "url": "https://www.turkpatent.gov.tr/", "city": "Ankara"},
            {"name": "KOSGEB", "url": "https://www.kosgeb.gov.tr/site/tr/genel/duyurular", "city": "Ankara"},
            {"name": "TOKİ", "url": "https://www.toki.gov.tr/", "city": "Ankara"},
            {"name": "İller Bankası", "url": "https://www.ilbank.gov.tr/", "city": "Ankara"},
            {"name": "TİKA", "url": "https://www.tika.gov.tr/", "city": "Ankara"},
            {"name": "YTB", "url": "https://www.ytb.gov.tr/", "city": "Ankara"},
            {"name": "Kıyı Emniyeti Genel Müdürlüğü", "url": "https://www.kiyiemniyeti.gov.tr/", "city": "İstanbul"},
            {"name": "TRT", "url": "https://www.trt.net.tr/", "city": "Ankara"},
        ],
    },
    {
        "group_key": "belediyeler",
        "group_label": "Büyükşehir Belediyeleri (28)",
        "source_name": "belediyeler",
        "items": [
            {"name": "İstanbul Büyükşehir Belediyesi", "url": "https://www.ibb.istanbul/", "city": "İstanbul"},
            {"name": "Ankara Büyükşehir Belediyesi", "url": "https://www.ankara.bel.tr/duyurular", "city": "Ankara"},
            {"name": "İzmir Büyükşehir Belediyesi", "url": "https://www.izmir.bel.tr/tr/Duyurular/21", "city": "İzmir"},
            {"name": "Bursa Büyükşehir Belediyesi", "url": "https://www.bursa.bel.tr/", "city": "Bursa"},
            {"name": "Antalya Büyükşehir Belediyesi", "url": "https://www.antalya.bel.tr/duyurular", "city": "Antalya"},
            {"name": "Konya Büyükşehir Belediyesi", "url": "https://www.konya.bel.tr/", "city": "Konya"},
            {"name": "Adana Büyükşehir Belediyesi", "url": "https://www.adana.bel.tr/", "city": "Adana"},
            {"name": "Gaziantep Büyükşehir Belediyesi", "url": "https://www.gaziantep.bel.tr/", "city": "Gaziantep"},
            {"name": "Kocaeli Büyükşehir Belediyesi", "url": "https://www.kocaeli.bel.tr/", "city": "Kocaeli"},
            {"name": "Mersin Büyükşehir Belediyesi", "url": "https://www.mersin.bel.tr/duyurular", "city": "Mersin"},
            {"name": "Eskişehir Büyükşehir Belediyesi", "url": "https://www.eskisehir.bel.tr/duyurular", "city": "Eskişehir"},
            {"name": "Kayseri Büyükşehir Belediyesi", "url": "https://www.kayseri.bel.tr/", "city": "Kayseri"},
            {"name": "Trabzon Büyükşehir Belediyesi", "url": "https://www.trabzon.bel.tr/duyurular", "city": "Trabzon"},
            {"name": "Denizli Büyükşehir Belediyesi", "url": "https://www.denizli.bel.tr/Default.aspx?k=duyurular", "city": "Denizli"},
            {"name": "Şanlıurfa Büyükşehir Belediyesi", "url": "https://www.sanliurfa.bel.tr/", "city": "Şanlıurfa"},
            {"name": "Diyarbakır Büyükşehir Belediyesi", "url": "https://www.diyarbakir.bel.tr/", "city": "Diyarbakır"},
            {"name": "Malatya Büyükşehir Belediyesi", "url": "https://www.malatya.bel.tr/", "city": "Malatya"},
            {"name": "Erzurum Büyükşehir Belediyesi", "url": "https://www.erzurum.bel.tr/", "city": "Erzurum"},
            {"name": "Manisa Büyükşehir Belediyesi", "url": "https://www.manisa.bel.tr/", "city": "Manisa"},
            {"name": "Balıkesir Büyükşehir Belediyesi", "url": "https://www.balikesir.bel.tr/", "city": "Balıkesir"},
            {"name": "Tekirdağ Büyükşehir Belediyesi", "url": "https://www.tekirdag.bel.tr/", "city": "Tekirdağ"},
            {"name": "Aydın Büyükşehir Belediyesi", "url": "https://www.aydin.bel.tr/", "city": "Aydın"},
            {"name": "Hatay Büyükşehir Belediyesi", "url": "https://www.hatay.bel.tr/", "city": "Hatay"},
            {"name": "Kahramanmaraş Büyükşehir Belediyesi", "url": "https://www.kahramanmaras.bel.tr/", "city": "Kahramanmaraş"},
            {"name": "Van Büyükşehir Belediyesi", "url": "https://www.van.bel.tr/", "city": "Van"},
            {"name": "Mardin Büyükşehir Belediyesi", "url": "https://www.mardin.bel.tr/", "city": "Mardin"},
            {"name": "Ordu Büyükşehir Belediyesi", "url": "https://www.ordu.bel.tr/", "city": "Ordu"},
            {"name": "Samsun Büyükşehir Belediyesi", "url": "https://www.samsun.bel.tr/", "city": "Samsun"},
        ],
    },
    {
        "group_key": "il_belediyeleri",
        "group_label": "İl Belediyeleri (44)",
        "source_name": "il_belediyeleri",
        "items": [
            {"name": "Afyonkarahisar Belediyesi", "url": "https://www.afyon.bel.tr/", "city": "Afyonkarahisar"},
            {"name": "Ağrı Belediyesi", "url": "https://www.agri.bel.tr/", "city": "Ağrı"},
            {"name": "Aksaray Belediyesi", "url": "https://www.aksaray.bel.tr/", "city": "Aksaray"},
            {"name": "Amasya Belediyesi", "url": "https://www.amasya.bel.tr/", "city": "Amasya"},
            {"name": "Ardahan Belediyesi", "url": "https://www.ardahan.bel.tr/", "city": "Ardahan"},
            {"name": "Artvin Belediyesi", "url": "https://www.artvin.bel.tr/", "city": "Artvin"},
            {"name": "Bartın Belediyesi", "url": "https://www.bartin.bel.tr/", "city": "Bartın"},
            {"name": "Batman Belediyesi", "url": "https://www.batman.bel.tr/", "city": "Batman"},
            {"name": "Bayburt Belediyesi", "url": "https://www.bayburt.bel.tr/", "city": "Bayburt"},
            {"name": "Bilecik Belediyesi", "url": "https://www.bilecik.bel.tr/", "city": "Bilecik"},
            {"name": "Bingöl Belediyesi", "url": "https://www.bingol.bel.tr/", "city": "Bingöl"},
            {"name": "Bitlis Belediyesi", "url": "https://www.bitlis.bel.tr/", "city": "Bitlis"},
            {"name": "Bolu Belediyesi", "url": "https://www.bolu.bel.tr/", "city": "Bolu"},
            {"name": "Burdur Belediyesi", "url": "https://www.burdur.bel.tr/", "city": "Burdur"},
            {"name": "Çanakkale Belediyesi", "url": "https://www.canakkale.bel.tr/", "city": "Çanakkale"},
            {"name": "Çankırı Belediyesi", "url": "https://www.cankiri.bel.tr/", "city": "Çankırı"},
            {"name": "Düzce Belediyesi", "url": "https://www.duzce.bel.tr/", "city": "Düzce"},
            {"name": "Edirne Belediyesi", "url": "https://www.edirne.bel.tr/", "city": "Edirne"},
            {"name": "Erzincan Belediyesi", "url": "https://www.erzincan.bel.tr/", "city": "Erzincan"},
            {"name": "Giresun Belediyesi", "url": "https://www.giresun.bel.tr/", "city": "Giresun"},
            {"name": "Gümüşhane Belediyesi", "url": "https://www.gumushane.bel.tr/", "city": "Gümüşhane"},
            {"name": "Iğdır Belediyesi", "url": "https://www.igdir.bel.tr/", "city": "Iğdır"},
            {"name": "Isparta Belediyesi", "url": "https://www.isparta.bel.tr/", "city": "Isparta"},
            {"name": "Karabük Belediyesi", "url": "https://www.karabuk.bel.tr/", "city": "Karabük"},
            {"name": "Karaman Belediyesi", "url": "https://www.karaman.bel.tr/", "city": "Karaman"},
            {"name": "Kars Belediyesi", "url": "https://www.kars.bel.tr/", "city": "Kars"},
            {"name": "Kastamonu Belediyesi", "url": "https://www.kastamonu.bel.tr/", "city": "Kastamonu"},
            {"name": "Kırıkkale Belediyesi", "url": "https://www.kirikkale.bel.tr/", "city": "Kırıkkale"},
            {"name": "Kırklareli Belediyesi", "url": "https://www.kirklareli.bel.tr/", "city": "Kırklareli"},
            {"name": "Kırşehir Belediyesi", "url": "https://www.kirsehir.bel.tr/", "city": "Kırşehir"},
            {"name": "Kilis Belediyesi", "url": "https://www.kilis.bel.tr/", "city": "Kilis"},
            {"name": "Nevşehir Belediyesi", "url": "https://www.nevsehir.bel.tr/", "city": "Nevşehir"},
            {"name": "Niğde Belediyesi", "url": "https://www.nigde.bel.tr/", "city": "Niğde"},
            {"name": "Osmaniye Belediyesi", "url": "https://www.osmaniye.bel.tr/", "city": "Osmaniye"},
            {"name": "Rize Belediyesi", "url": "https://www.rize.bel.tr/", "city": "Rize"},
            {"name": "Siirt Belediyesi", "url": "https://www.siirt.bel.tr/", "city": "Siirt"},
            {"name": "Sinop Belediyesi", "url": "https://www.sinop.bel.tr/", "city": "Sinop"},
            {"name": "Sivas Belediyesi", "url": "https://www.sivas.bel.tr/", "city": "Sivas"},
            {"name": "Şırnak Belediyesi", "url": "https://www.sirnak.bel.tr/", "city": "Şırnak"},
            {"name": "Tokat Belediyesi", "url": "https://www.tokat.bel.tr/", "city": "Tokat"},
            {"name": "Uşak Belediyesi", "url": "https://www.usak.bel.tr/", "city": "Uşak"},
            {"name": "Yalova Belediyesi", "url": "https://www.yalova.bel.tr/", "city": "Yalova"},
            {"name": "Yozgat Belediyesi", "url": "https://www.yozgat.bel.tr/", "city": "Yozgat"},
            {"name": "Zonguldak Belediyesi", "url": "https://www.zonguldak.bel.tr/", "city": "Zonguldak"},
        ],
    },
    {
        "group_key": "universiteler",
        "group_label": "Üniversite Personel Daireleri (19)",
        "source_name": "universiteler",
        "items": [
            {"name": "Hacettepe Üniversitesi PDB", "url": "https://pdb.hacettepe.edu.tr/", "city": "Ankara"},
            {"name": "Ege Üniversitesi PDB", "url": "https://personeldb.ege.edu.tr/", "city": "İzmir"},
            {"name": "Gazi Üniversitesi PDB", "url": "https://personel.gazi.edu.tr/", "city": "Ankara"},
            {"name": "Dokuz Eylül Üniversitesi PDB", "url": "https://personel.deu.edu.tr/", "city": "İzmir"},
            {"name": "ODTÜ PDB", "url": "https://pdb.metu.edu.tr/", "city": "Ankara"},
            {"name": "Akdeniz Üniversitesi PDB", "url": "https://personel.akdeniz.edu.tr/", "city": "Antalya"},
            {"name": "Çukurova Üniversitesi PDB", "url": "https://personel.cu.edu.tr/", "city": "Adana"},
            {"name": "Bursa Uludağ Üniversitesi PDB", "url": "https://uludag.edu.tr/personel", "city": "Bursa"},
            {"name": "Karadeniz Teknik Üniversitesi PDB", "url": "https://www.ktu.edu.tr/personel", "city": "Trabzon"},
            {"name": "Atatürk Üniversitesi", "url": "https://atauni.edu.tr/", "city": "Erzurum"},
            {"name": "Yıldız Teknik Üniversitesi PDB", "url": "https://prs.yildiz.edu.tr/", "city": "İstanbul"},
            {"name": "Selçuk Üniversitesi", "url": "https://www.selcuk.edu.tr/", "city": "Konya"},
            {"name": "Ondokuz Mayıs Üniversitesi PDB", "url": "https://personel.omu.edu.tr/", "city": "Samsun"},
            {"name": "Sakarya Üniversitesi PDB", "url": "https://personel.sakarya.edu.tr/", "city": "Sakarya"},
            {"name": "Anadolu Üniversitesi", "url": "https://www.anadolu.edu.tr/", "city": "Eskişehir"},
            {"name": "Eskişehir Osmangazi Üniversitesi PDB", "url": "https://personel.ogu.edu.tr/", "city": "Eskişehir"},
            {"name": "Pamukkale Üniversitesi PDB", "url": "https://www.pau.edu.tr/personel", "city": "Denizli"},
            {"name": "Çanakkale Onsekiz Mart Üniversitesi PDB", "url": "https://personel.comu.edu.tr/", "city": "Çanakkale"},
            {"name": "Mersin Üniversitesi PDB", "url": "https://www.mersin.edu.tr/", "city": "Mersin"},
        ],
    },
]

# In-memory per-institution health & found-count tracking for GET /api/institutions
INSTITUTION_RUN_STATS: dict[str, dict] = {}


def get_institutions_catalog_with_status() -> dict:
    """Return the 74-institution catalog enriched with live run status for the UI."""
    groups_out: list[dict] = []
    total = 0
    for grp in OFFICIAL_INSTITUTIONS_CATALOG:
        items_out: list[dict] = []
        for item in grp["items"]:
            stat = INSTITUTION_RUN_STATS.get(item["url"], {})
            items_out.append(
                {
                    "name": item["name"],
                    "url": item["url"],
                    "city": item["city"],
                    "status": stat.get("status", "idle"),
                    "found": int(stat.get("found", 0)),
                }
            )
        total += len(items_out)
        groups_out.append(
            {
                "group_key": grp["group_key"],
                "group_label": grp["group_label"],
                "source_name": grp["source_name"],
                "count": len(items_out),
                "items": items_out,
            }
        )
    return {"total": total, "groups": groups_out}


def _is_candidate_link(text: str) -> bool:
    if not text or len(text) < 20 or len(text) > 240:
        return False
    if is_cancelled_announcement_title(text):
        return False
    low = turkish_lower(text)
    if any(neg in low for neg in NEGATIVE_NOISE_TERMS):
        return False
    return any(pos in low for pos in POSITIVE_RECRUITMENT_TERMS)


def _is_stale_date(date_str: str | None, today: datetime.date) -> bool:
    if not date_str:
        return False
    try:
        dt = datetime.date.fromisoformat(date_str[:10])
        return (today - dt).days > STALE_DAYS_LIMIT
    except ValueError:
        return False


def _has_old_archive_year(text: str, today: datetime.date) -> bool:
    """Detect clearly old archive announcements (e.g. 2021-2024) lacking current year."""
    years = [int(y) for y in re.findall(r"(?<!\d)(20\d{2})(?!\d)", text[:2500])]
    if not years:
        return False
    return max(years) < today.year - 1


def _extract_date_from_url(url: str) -> str | None:
    """Extract embedded DD-MM-YYYY, YYYY-MM-DD, or DDMMYYYY date from institution URLs."""
    m = re.search(r"/(0?[1-9]|[12]\d|3[01])[-_.](0?[1-9]|1[0-2])[-_.](20\d{2})(?:/|$|\?)", url)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    m = re.search(r"/(20\d{2})[-_/](0?[1-9]|1[0-2])[-_/](0?[1-9]|[12]\d|3[01])(?:/|$|\?)", url)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except ValueError:
            pass
    m = re.search(r"/(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(20\d{2})(?:/|$|\?)", url)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    return None


def _extract_parent_context(a_tag) -> str:
    parent = a_tag.find_parent(["li", "tr", "article", "div"])
    if parent is None:
        return ""
    txt = normalize_whitespace(parent.get_text(" ", strip=True))
    return txt[:400] if len(txt) <= 600 else ""


async def _scrape_institution_group(
    source_name: str,
    source_label: str,
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    known = known_external_ids or set()
    targets: list[dict] = []
    for grp in OFFICIAL_INSTITUTIONS_CATALOG:
        if grp["source_name"] == source_name:
            targets.extend(grp["items"])

    if not targets:
        return []

    client = HttpClient(timeout=INSTITUTION_TIMEOUT, max_retries=0)
    semaphore = asyncio.Semaphore(INSTITUTION_CONCURRENCY)
    today = datetime.date.today()

    candidates: list[dict] = []
    seen_urls: set[str] = set()

    async def _fetch_institution_page(inst: dict) -> None:
        async with semaphore:
            url = inst["url"]
            try:
                html = await client.get_text(url, timeout=INSTITUTION_TIMEOUT)
                soup = BeautifulSoup(html, "lxml")
                found_here = 0
                for a in soup.select("a[href]"):
                    if found_here >= MAX_PER_INSTITUTION:
                        break
                    href = a.get("href", "").strip()
                    if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                        continue
                    text = normalize_whitespace(a.get("title") or a.get_text(" ", strip=True))
                    if not _is_candidate_link(text):
                        continue

                    full_url = urllib.parse.urljoin(url, href).split("#")[0]
                    if full_url in seen_urls:
                        continue

                    parent_ctx = _extract_parent_context(a)
                    combined_hint = f"{text} {parent_ctx}".strip()
                    pub_hint = _extract_date_from_url(full_url) or parse_turkish_date(combined_hint, reference_date=today)
                    if _is_stale_date(pub_hint, today) or _has_old_archive_year(combined_hint, today):
                        continue

                    seen_urls.add(full_url)
                    ext_id = stable_external_id(source_name, full_url)
                    candidates.append(
                        {
                            "external_id": ext_id,
                            "url": full_url,
                            "title": text,
                            "institution": inst["name"],
                            "city": inst["city"],
                            "pub_hint": pub_hint,
                            "inst_url": url,
                        }
                    )
                    found_here += 1

                INSTITUTION_RUN_STATS[url] = {"status": "ok", "found": found_here}
            except Exception as exc:
                logger.debug("Institution fetch failed (%s): %s", url, exc)
                INSTITUTION_RUN_STATS[url] = {"status": "error", "found": 0}

    await asyncio.gather(*(_fetch_institution_page(inst) for inst in targets), return_exceptions=True)

    if not candidates:
        logger.info("%s: 0 active recruitment links across %d institutions", source_label, len(targets))
        return []

    # Fetch detail HTML/PDF for unseen candidate links
    detail_texts: dict[str, tuple[str, str | None]] = {}
    unseen = [c for c in candidates if c["external_id"] not in known][:MAX_CANDIDATE_DETAILS_PER_GROUP]

    async def _fetch_detail(cand: dict) -> None:
        async with semaphore:
            try:
                if cand["url"].lower().endswith(".pdf"):
                    pdf_bytes, _ = await client.get_bytes(cand["url"], timeout=INSTITUTION_TIMEOUT)
                    txt = await asyncio.to_thread(extract_pdf_text, pdf_bytes, 4)
                    detail_texts[cand["external_id"]] = (txt, cand["pub_hint"])
                else:
                    det_html = await client.get_text(cand["url"], timeout=INSTITUTION_TIMEOUT)
                    det_text = html_to_text(det_html)
                    # Try parsing meta published_time or top lines date
                    soup = BeautifulSoup(det_html, "lxml")
                    meta_pub = soup.select_one("meta[property='article:published_time']")
                    pub_d = (
                        parse_turkish_date(meta_pub["content"][:10], reference_date=today)
                        if meta_pub and meta_pub.get("content")
                        else parse_turkish_date(det_text[:1500], reference_date=today)
                    )
                    detail_texts[cand["external_id"]] = (det_text[:15000], pub_d or cand["pub_hint"])
            except Exception as exc:
                logger.debug("Institution detail failed (%s): %s", cand["url"], exc)

    if unseen:
        await asyncio.gather(*(_fetch_detail(c) for c in unseen), return_exceptions=True)

    results: list[RawAnnouncement] = []
    for cand in candidates:
        ext_id = cand["external_id"]
        det_text, det_pub = detail_texts.get(ext_id, ("", cand["pub_hint"]))
        pub_date = det_pub or cand["pub_hint"]

        if _is_stale_date(pub_date, today):
            continue
        if det_text:
            low_det = turkish_lower(det_text[:2000])
            if any(neg in low_det for neg in DETAIL_NEGATIVE_TERMS):
                continue
            if _has_old_archive_year(f"{cand['title']} {det_text[:800]}", today) and not pub_date:
                continue
        elif _has_old_archive_year(cand["title"], today):
            continue

        # Also update INSTITUTION_RUN_STATS found count after filtering
        raw_text = det_text if det_text else f"{cand['institution']} — {cand['title']}\nResmi Sayfa: {cand['url']}"
        category = infer_category(f"{cand['institution']} {cand['title']}", raw_text, default="memur")
        quota = extract_quota_from_text(cand["title"], raw_text)
        channel = infer_application_channel(raw_text) or "Kurum Sitesi"

        results.append(
            RawAnnouncement(
                source_name=source_name,
                source_label=source_label,
                external_id=ext_id,
                url=cand["url"],
                title=cand["title"],
                institution=cand["institution"],
                category=category,
                publish_date=pub_date,
                deadline_date=None,
                city=cand["city"],
                quota_count=quota,
                raw_text=raw_text,
                pdf_url=cand["url"] if cand["url"].lower().endswith(".pdf") else None,
                application_channel=channel,
            )
        )

    logger.info(
        "%s scraped %d announcements across %d institutions (%d details fetched)",
        source_label,
        len(results),
        len(targets),
        len(detail_texts),
    )
    return results


async def scrape_bakanliklar_kurumlar(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape all 37 built-in ministries and public agencies/KİT sites."""
    return await _scrape_institution_group(
        source_name="bakanliklar_kurumlar",
        source_label="Bakanlıklar & Kamu Kurumları",
        known_external_ids=known_external_ids,
    )


async def scrape_kurullar_kitler(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape all 35 built-in judicial, regulatory boards, and state enterprise (KİT) sites."""
    return await _scrape_institution_group(
        source_name="kurullar_kitler",
        source_label="Yargı, Üst Kurullar & KİT'ler",
        known_external_ids=known_external_ids,
    )


async def scrape_belediyeler(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape all 28 built-in metropolitan municipalities."""
    return await _scrape_institution_group(
        source_name="belediyeler",
        source_label="Büyükşehir Belediyeleri",
        known_external_ids=known_external_ids,
    )


async def scrape_il_belediyeleri(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape all 44 built-in provincial municipalities."""
    return await _scrape_institution_group(
        source_name="il_belediyeleri",
        source_label="İl Belediyeleri",
        known_external_ids=known_external_ids,
    )


async def scrape_universiteler(
    known_external_ids: set[str] | None = None,
) -> list[RawAnnouncement]:
    """Scrape all 10 built-in state university personnel departments."""
    return await _scrape_institution_group(
        source_name="universiteler",
        source_label="Üniversiteler (PDB)",
        known_external_ids=known_external_ids,
    )
