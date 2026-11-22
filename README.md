# KPSS Radar — Kamu Personel Alım Takip ve Sıfır-Kaçırma Eşleştirme Sistemi

**KPSS Radar**, Türkiye'deki kamu kurumlarının personel alım ilanlarını resmi ve canlı kaynaklardan otomatik olarak toplayan, Türkçe KPSS kriterlerini (puan türü, taban puan, eğitim düzeyi, ÖSYM nitelik kodları, bölüm, yaş sınırı, şehir, son başvuru tarihi) ayrıştıran ve aday profilinize göre **"Sıfır-Kaçırma Garantili 3 Kademeli"** uygunluk analizi sunan yerel bir takip uygulamasıdır.

---

## Hangi Problemi Çözer?

Kamu alım ilanları farklı portallara dağılmış durumdadır ve çoğu ilan karmaşık metinler veya PDF tabloları içinde yayınlanır. Klasik filtreleme araçları:
- Aynı ilanın birden fazla sitede tekrar görünmesine neden olur,
- Puan veya bölüm bilgisini metinden okuyamadığı ilanları gizleyerek **fırsat kaçırmaya** yol açar.

KPSS Radar ise:
1. İlanları **tekilleştirir (deduplication)**: Aynı alım ilanı SBB, Memurlar.net ve Resmî Gazete'de geçse bile tek kartta birleştirir ve tüm kaynak bağlantılarını korur.
2. **Sıfır-Kaçırma Garantisi** uygular: Emin olmadığı veya çok kadrolu PDF içeriklerinde ilanı asla elemez; **"İnceleme Gerekli"** katmanına alır.
3. Tamamı bilgisayarınızda (`127.0.0.1:8000`) ve yerel SQLite veritabanında (`backend/data/kpss_radar.db`) çalışır; verileriniz dış sunuculara gönderilmez.

---

## Taranan Canlı Resmi ve Kamu Kaynakları

Uygulama hiçbir sahte/statik veri kullanmaz; **10 yerleşik canlı kaynak grubunu** ve **163 resmi kurum duyuru sayfasını** otomatik olarak tarar:

| Kaynak Kodu | Kaynak Adı | Adres / Kapsam | Açıklama |
|---|---|---|---|
| `sbb_kamuilan` | **SBB Kamu İlan** | `https://kamuilan.sbb.gov.tr/` | T.C. Strateji ve Bütçe Başkanlığı kamu alım ilanları ve ek PDF belgeleri |
| `memurlar_net` | **Memurlar.net İlanlar** | `https://ilan.memurlar.net/` | KPSS-B, 4/B, Mahalli, KPSS-A, İşçi, SYDV, Engelli ve genel alımlar |
| `resmi_gazete` | **T.C. Resmî Gazete** | `https://www.resmigazete.gov.tr/` | Son 14 günün Resmî Gazete "Çeşitli İlanlar" bölümü |
| `osym` | **ÖSYM KPSS Duyuruları** | `https://www.osym.gov.tr/` | Merkezi yerleştirme (KPSS/EKPSS) tercih ve kılavuz duyuruları |
| `isinolsa` | **İşin Olsa Kamu Alımları** | `https://www.isinolsa.com/` | 6 uzman kategori (Kamu, İŞKUR, Belediye, Memur, Sözleşmeli, SYDV) |
| `bakanliklar_kurumlar` | **Bakanlıklar & Kamu Kurumları (37)** | 15 Bakanlık + 22 Genel Müdürlük / Başkanlık | Resmî bakanlık, SGK, TÜBİTAK, Merkez Bankası, BDDK vb. duyuru sayfaları |
| `kurullar_kitler` | **Yargı, Üst Kurullar & KİT'ler (35)** | 13 Yargı/Yasama/Üst Kurul + 22 KİT | Danıştay, Sayıştay, RTÜK, KVKK, İŞKUR, TÜRASAŞ, MKE, TPAO, Eti Maden vb. |
| `belediyeler` | **Büyükşehir Belediyeleri (28)** | Yerleşik 28 Büyükşehir Belediyesi | Büyükşehir belediyelerinin resmi personel/duyuru sayfaları |
| `il_belediyeleri` | **İl Belediyeleri (44)** | Yerleşik 44 İl Belediyesi | İl belediyelerinin resmi personel ve duyuru sayfaları |
| `universiteler` | **Üniversite Personel Daireleri (19)** | 19 Üniversite PDB (+ SBB/RG tüm 208 üniversite) | Doğrudan üniversite personel daire başkanlığı duyuru sayfaları |
| `custom:<ad>` | **Özel Kurum İzleyicisi** | Kullanıcı tanımlı | İsteğe bağlı eklediğiniz kurum kariyer sayfaları veya RSS bağlantıları |

> **e-Devlet / WAF Korumalı Portallar İçin Akıllı İçe Aktarma:** Kariyer Kapısı, İŞKUR e-Şube ve SYDV gibi e-Devlet/bot korumalı portallarda tarayıcınızda gördüğünüz herhangi bir ilan metnini veya İŞKUR Kurumdışı PDF dosyasını **Kaynaklar** sayfasındaki **Akıllı PDF / Metin İçe Aktarma** aracıyla (`POST /api/announcements/import` ve `POST /api/announcements/import-pdf`) anında analiz edip profil uygunluğunuza ekleyebilirsiniz.

---

## Sıfır-Kaçırma 3 Kademeli Eşleştirme Sistemi

Aday profiliniz doldurulduktan sonra (`Profilim` sayfası), her ilan dinamik olarak üç katmandan birine yerleştirilir:

1. **Tam Uygun (`eligible`)**
   - Eğitim düzeyiniz ilan şartını karşılıyor,
   - KPSS puanınız belirtilen taban puanın üzerinde (veya KPSS'siz alım aktif),
   - Bölümünüz / ÖSYM nitelik kodunuz (ör. `4001`, `3001`, `2001`, `4531`) eşleşiyor,
   - Yaş sınırı ve şehir tercihinizle tam uyum sağlanıyor.

2. **İnceleme Gerekli (`review`) — Sıfır Kaçırma Katmanı**
   - Profil henüz doldurulmamışsa tüm ilanlar burada listelenir (skor: `50`).
   - İlandan taban puan, eğitim düzeyi veya bölüm bilgisi otomatik çıkarılamadıysa **asla elenmez**, `unknown` / `warn` gerekçesiyle burada gösterilir.
   - Çok kadrolu veya PDF ekli büyük alımlarda bölümünüz PDF'in sonraki sayfalarında yer alabileceğinden ilan elenmez; manuel kontrol için `review` katmanında tutulur.

3. **Uygun Değil (`ineligible`)**
   - Yalnızca **kesin çelişki** varsa bu katmana düşer ve açık Türkçe neden gösterilir:
     - KPSS puanınızın taban puanın altında kalması,
     - İlanın yalnızca farklı bir tek eğitim düzeyi istemesi (ör. sadece Ortaöğretim),
     - Üst yaş sınırının aşılması,
     - Dar ve tek meslek/bölüm odaklı bir ilanın bölümünüzle çelişmesi (ör. yalnızca Tıp Fakültesi).

---

## Tek Tıkla Başlatma (Windows)

### Gereksinimler
- **Python 3.11+** (`python` veya `py` komutunun PATH'te olması)
- **Node.js (LTS)** (`frontend/dist` henüz derlenmemişse otomatik derleme için)

### Çalıştırma
Proje kök dizinindeki **`start.bat`** dosyasına çift tıklayın (veya PowerShell'de `.\start.ps1` çalıştırın):

```powershell
.\start.ps1
```

Başlatıcı otomatik olarak şunları yapar:
1. `backend/.venv` sanal ortamı yoksa oluşturur ve `backend/requirements.txt` paketlerini kurar.
2. `frontend/dist` derlemesi yoksa `npm.cmd install` ve `npm.cmd run build` ile arayüzü derler.
3. FastAPI sunucusunu `http://127.0.0.1:8000` adresinde başlatır ve 2 saniye sonra varsayılan tarayıcınızda açar.

> **Not:** İlk açılışta veritabanı boşsa arka planda canlı kaynak taraması otomatik olarak başlatılır. İlanların son başvuru tarihlerini **`.ics` Takvim Dosyası** olarak dışa aktarabilirsiniz (`GET /api/announcements/export/ics`).

---

## Geliştirme Modu (Development)

Backend ve frontend'i ayrı terminallerde sıcak yenileme (hot-reload) ile çalıştırmak için:

### 1. Backend (Port 8000)
```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 2. Frontend (Port 5173, `/api` proxy aktif)
```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```
Ardından tarayıcıda `http://127.0.0.1:5173` adresini açın.

### Testleri Çalıştırma
Proje kök dizininden tüm birim ve API uçtan uca testlerini çalıştırmak için:
```powershell
backend\.venv\Scripts\pytest.exe -v
```

---

## Telegram Bot Bildirim Kurulumu

Yeni uygun (`eligible` veya yüksek skorlu `review`) ilanlar yakalandığında telefonunuza anında bildirim almak için:

1. Telegram'da **`@BotFather`** ile sohbet başlatın ve `/newbot` komutunu gönderin.
2. Botunuz için bir ad ve kullanıcı adı belirleyin. BotFather size bir **Bot Token** verecektir (ör. `123456789:ABCdef...`).
3. Oluşturduğunuz bota Telegram'dan girip **Başlat (Start)** veya herhangi bir mesaj gönderin.
4. **Chat ID** numaranızı öğrenmek için Telegram'da **`@userinfobot`**'a mesaj atın veya tarayıcıdan `https://api.telegram.org/bot<BOT_TOKEN>/getUpdates` adresindeki `chat.id` değerini alın.
5. KPSS Radar arayüzünde **Profilim** sayfasına gidin, **Telegram Bot Token** ve **Telegram Chat ID** alanlarını doldurup profili kaydedin.
6. **Test Bildirimi Gönder** butonuna basarak bağlantıyı doğrulayın.

*(İsterseniz Webhook URL alanına kendi Discord/Slack/n8n webhook adresinizi de ekleyebilirsiniz.)*
