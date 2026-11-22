import type { AnnouncementSource, EducationLevel, KpssScoreKey, UserProfile } from './types';

export const CATEGORY_LABELS: Record<string, string> = {
  memur: 'Memur',
  sozlesmeli_4b: '4/B Sözleşmeli',
  merkezi_atama: 'Merkezi Atama',
  kpss_a: 'KPSS A Grubu',
  isci: 'Kamu İşçisi',
  akademik: 'Akademik',
  sydv: 'SYDV',
  engelli: 'Engelli (EKPSS)',
  askeri_emniyet: 'Askeri / Emniyet',
  diger: 'Diğer',
};

export const CATEGORY_LIST: { value: string; label: string; description: string }[] = [
  { value: 'memur', label: 'Memur', description: '657 4/A kadrolu memur alımları' },
  { value: 'sozlesmeli_4b', label: '4/B Sözleşmeli', description: 'Bakanlık ve üniversite sözleşmeli personel' },
  { value: 'merkezi_atama', label: 'Merkezi Atama', description: 'ÖSYM KPSS-1 ve KPSS-2 tercih kılavuzları' },
  { value: 'kpss_a', label: 'KPSS A Grubu', description: 'Müfettiş, uzman, denetmen yardımcılığı' },
  { value: 'isci', label: 'Kamu İşçisi', description: 'İŞKUR ve sürekli kamu işçisi alımları' },
  { value: 'akademik', label: 'Akademik', description: 'Öğretim görevlisi, araştırma görevlisi' },
  { value: 'sydv', label: 'SYDV', description: 'Sosyal Yardımlaşma ve Dayanışma Vakıfları' },
  { value: 'engelli', label: 'Engelli (EKPSS)', description: 'EKPSS ve engelli memur/işçi ilanları' },
  { value: 'askeri_emniyet', label: 'Askeri / Emniyet', description: 'POMEM, PMYO, bekçi, subay/astsubay' },
  { value: 'diger', label: 'Diğer', description: 'Diğer kamu ilanları' },
];

export const SOURCE_OPTIONS: { value: string; label: string }[] = [
  { value: 'all', label: 'Tüm Kaynaklar' },
  { value: 'sbb_kamuilan', label: 'SBB Kamu İlan' },
  { value: 'memurlar_net', label: 'Memurlar.net' },
  { value: 'resmi_gazete', label: 'Resmî Gazete' },
  { value: 'osym', label: 'ÖSYM' },
  { value: 'isinolsa', label: 'İşin Olsa Kamu' },
  { value: 'bakanliklar_kurumlar', label: 'Bakanlıklar & Kamu Kurumları' },
  { value: 'kurullar_kitler', label: "Yargı, Üst Kurullar & KİT'ler" },
  { value: 'belediyeler', label: 'Büyükşehir Belediyeleri' },
  { value: 'il_belediyeleri', label: 'İl Belediyeleri (44)' },
  { value: 'universiteler', label: 'Üniversiteler (PDB)' },
];

export const EDUCATION_OPTIONS: { value: EducationLevel; label: string; subtitle: string }[] = [
  { value: 'lisans', label: 'Lisans', subtitle: '4 yıllık fakülte / yüksekokul' },
  { value: 'onlisans', label: 'Önlisans', subtitle: '2 yıllık meslek yüksekokulu' },
  { value: 'ortaogretim', label: 'Ortaöğretim / Lise', subtitle: 'Lise ve dengi okul' },
  { value: 'ilkogretim', label: 'İlköğretim', subtitle: 'İlkokul / ortaokul (işçi kadroları)' },
];

export const EDUCATION_LABELS: Record<string, string> = {
  lisans: 'Lisans',
  onlisans: 'Önlisans',
  ortaogretim: 'Ortaöğretim / Lise',
  ilkogretim: 'İlköğretim',
};

export const KPSS_SCORE_META: { key: KpssScoreKey; label: string; hint: string }[] = [
  { key: 'P3', label: 'KPSS P3', hint: 'Lisans B Grubu Genel (4001 / Memur / 4B)' },
  { key: 'P93', label: 'KPSS P93', hint: 'Önlisans Genel' },
  { key: 'P94', label: 'KPSS P94', hint: 'Ortaöğretim (Lise) Genel' },
  { key: 'P1', label: 'KPSS P1', hint: 'Mühendislik / İİBF A Grubu' },
  { key: 'P2', label: 'KPSS P2', hint: 'A Grubu Genel Yetenek Ağırlıklı' },
  { key: 'P10', label: 'KPSS P10', hint: 'Öğretmenlik / Eğitim' },
  { key: 'P121', label: 'KPSS P121', hint: 'ÖABT Alan Bilgisi' },
  { key: 'EKPSS', label: 'EKPSS', hint: 'Engelli Kamu Personeli Seçme Sınavı' },
  { key: 'YDS', label: 'YDS / YÖKDİL', hint: 'Yabancı Dil Puanı (0–100)' },
];

export const LISANS_DEPARTMENTS: string[] = [
  'Bilgisayar Mühendisliği',
  'Yazılım Mühendisliği',
  'Elektrik-Elektronik Mühendisliği',
  'Endüstri Mühendisliği',
  'İnşaat Mühendisliği',
  'Makine Mühendisliği',
  'İşletme',
  'İktisat',
  'Maliye',
  'Kamu Yönetimi',
  'Uluslararası İlişkiler',
  'Hukuk',
  'Hemşirelik',
  'Ebelik',
  'Sağlık Yönetimi',
  'Sosyal Hizmet',
  'Psikoloji',
  'Türk Dili ve Edebiyatı',
  'Matematik',
];

export const ONLISANS_DEPARTMENTS: string[] = [
  'Bilgisayar Programcılığı',
  'Dış Ticaret',
  'Büro Yönetimi ve Yönetici Asistanlığı',
  'Tıbbi Dokümantasyon ve Sekreterlik',
  'Adalet',
  'Mahalli İdareler',
  'Muhasebe ve Vergi Uygulamaları',
  'Anestezi',
  'İlk ve Acil Yardım',
  'Diyaliz',
  'Odyometri',
  'Lojistik',
  'Pazarlama',
  'Bankacılık ve Sigortacılık',
  'İnsan Kaynakları Yönetimi',
  'İnşaat Teknolojisi',
  'Elektrik Teknolojisi',
  'Makine Teknolojisi',
  'Harita ve Kadastro',
  'Çağrı Merkezi Hizmetleri',
];

export const ORTAOGRETIM_DEPARTMENTS: string[] = [
  'Büro Yönetimi',
  'Muhasebe ve Finansman',
  'Bilişim Teknolojileri',
  'Elektrik-Elektronik Teknolojisi',
  'Makine Teknolojisi',
  'İnşaat Teknolojisi',
  'Sağlık Hizmetleri',
  'Adalet',
  'Düz Lise / Genel Ortaöğretim',
];

export function getDepartmentsForEducation(level: EducationLevel | string): string[] {
  if (level === 'onlisans') return ONLISANS_DEPARTMENTS;
  if (level === 'ortaogretim' || level === 'ilkogretim') return ORTAOGRETIM_DEPARTMENTS;
  return LISANS_DEPARTMENTS;
}

export interface DepartmentCatalogItem {
  name: string;
  level: 'lisans' | 'onlisans' | 'ortaogretim';
}

export function normalizeTurkishForSearch(text: string): string {
  return text
    .replace(/İ/g, 'i')
    .replace(/I/g, 'i')
    .replace(/ı/g, 'i')
    .replace(/Ğ/g, 'g')
    .replace(/ğ/g, 'g')
    .replace(/Ü/g, 'u')
    .replace(/ü/g, 'u')
    .replace(/Ş/g, 's')
    .replace(/ş/g, 's')
    .replace(/Ö/g, 'o')
    .replace(/ö/g, 'o')
    .replace(/Ç/g, 'c')
    .replace(/ç/g, 'c')
    .toLowerCase()
    .trim();
}

export const DEPARTMENT_CATALOG: DepartmentCatalogItem[] = [
  // --- LİSANS (Mühendislik, Bilişim, Mimarlık) ---
  { name: 'Bilgisayar Mühendisliği', level: 'lisans' },
  { name: 'Yazılım Mühendisliği', level: 'lisans' },
  { name: 'Elektrik-Elektronik Mühendisliği', level: 'lisans' },
  { name: 'Elektrik Mühendisliği', level: 'lisans' },
  { name: 'Elektronik ve Haberleşme Mühendisliği', level: 'lisans' },
  { name: 'Endüstri Mühendisliği', level: 'lisans' },
  { name: 'İnşaat Mühendisliği', level: 'lisans' },
  { name: 'Makine Mühendisliği', level: 'lisans' },
  { name: 'Harita Mühendisliği', level: 'lisans' },
  { name: 'Geomatik Mühendisliği', level: 'lisans' },
  { name: 'Çevre Mühendisliği', level: 'lisans' },
  { name: 'Kimya Mühendisliği', level: 'lisans' },
  { name: 'Gıda Mühendisliği', level: 'lisans' },
  { name: 'Ziraat Mühendisliği', level: 'lisans' },
  { name: 'Orman Mühendisliği', level: 'lisans' },
  { name: 'Jeoloji Mühendisliği', level: 'lisans' },
  { name: 'Jeofizik Mühendisliği', level: 'lisans' },
  { name: 'Maden Mühendisliği', level: 'lisans' },
  { name: 'Metalurji ve Malzeme Mühendisliği', level: 'lisans' },
  { name: 'Mekatronik Mühendisliği', level: 'lisans' },
  { name: 'Otomotiv Mühendisliği', level: 'lisans' },
  { name: 'Enerji Sistemleri Mühendisliği', level: 'lisans' },
  { name: 'Biyomedikal Mühendisliği', level: 'lisans' },
  { name: 'Yapay Zeka ve Veri Mühendisliği', level: 'lisans' },
  { name: 'Bilişim Sistemleri Mühendisliği', level: 'lisans' },
  { name: 'Yönetim Bilişim Sistemleri (YBS)', level: 'lisans' },
  { name: 'Mimarlık', level: 'lisans' },
  { name: 'Şehir ve Bölge Planlama', level: 'lisans' },
  { name: 'Peyzaj Mimarlığı', level: 'lisans' },
  { name: 'İç Mimarlık', level: 'lisans' },
  // --- LİSANS (İİBF, SBF, Hukuk, İletişim) ---
  { name: 'İşletme', level: 'lisans' },
  { name: 'İktisat', level: 'lisans' },
  { name: 'Maliye', level: 'lisans' },
  { name: 'Kamu Yönetimi', level: 'lisans' },
  { name: 'Siyaset Bilimi ve Kamu Yönetimi', level: 'lisans' },
  { name: 'Uluslararası İlişkiler', level: 'lisans' },
  { name: 'Çalışma Ekonomisi ve Endüstri İlişkileri', level: 'lisans' },
  { name: 'Ekonometri', level: 'lisans' },
  { name: 'Uluslararası Ticaret ve Lojistik', level: 'lisans' },
  { name: 'Uluslararası Ticaret ve Finansman', level: 'lisans' },
  { name: 'Finans ve Bankacılık', level: 'lisans' },
  { name: 'Muhasebe ve Finans Yönetimi', level: 'lisans' },
  { name: 'İnsan Kaynakları Yönetimi', level: 'lisans' },
  { name: 'Hukuk', level: 'lisans' },
  { name: 'Halkla İlişkiler ve Tanıtım', level: 'lisans' },
  { name: 'Gazetecilik', level: 'lisans' },
  { name: 'Radyo, Televizyon ve Sinema', level: 'lisans' },
  { name: 'Sağlık Yönetimi', level: 'lisans' },
  { name: 'Turizm İşletmeciliği', level: 'lisans' },
  { name: 'Gümrük İşletme', level: 'lisans' },
  { name: 'Lojistik Yönetimi', level: 'lisans' },
  { name: 'Acil Yardım ve Afet Yönetimi', level: 'lisans' },
  // --- LİSANS (Sağlık, Fen-Edebiyat, Eğitim, İlahiyat) ---
  { name: 'Tıp', level: 'lisans' },
  { name: 'Diş Hekimliği', level: 'lisans' },
  { name: 'Eczacılık', level: 'lisans' },
  { name: 'Veteriner Hekimlik', level: 'lisans' },
  { name: 'Hemşirelik', level: 'lisans' },
  { name: 'Ebelik', level: 'lisans' },
  { name: 'Fizyoterapi ve Rehabilitasyon', level: 'lisans' },
  { name: 'Beslenme ve Diyetetik', level: 'lisans' },
  { name: 'Odyoloji', level: 'lisans' },
  { name: 'Dil ve Konuşma Terapisi', level: 'lisans' },
  { name: 'Ergoterapi', level: 'lisans' },
  { name: 'Psikoloji', level: 'lisans' },
  { name: 'Sosyal Hizmet', level: 'lisans' },
  { name: 'Sosyoloji', level: 'lisans' },
  { name: 'Felsefe', level: 'lisans' },
  { name: 'Türk Dili ve Edebiyatı', level: 'lisans' },
  { name: 'Tarih', level: 'lisans' },
  { name: 'Coğrafya', level: 'lisans' },
  { name: 'Matematik', level: 'lisans' },
  { name: 'İstatistik', level: 'lisans' },
  { name: 'Fizik', level: 'lisans' },
  { name: 'Kimya', level: 'lisans' },
  { name: 'Biyoloji', level: 'lisans' },
  { name: 'Moleküler Biyoloji ve Genetik', level: 'lisans' },
  { name: 'Arkeoloji', level: 'lisans' },
  { name: 'Sanat Tarihi', level: 'lisans' },
  { name: 'Bilgi ve Belge Yönetimi', level: 'lisans' },
  { name: 'Mütercim ve Tercümanlık (İngilizce)', level: 'lisans' },
  { name: 'İngiliz Dili ve Edebiyatı', level: 'lisans' },
  { name: 'İlahiyat', level: 'lisans' },
  { name: 'Sınıf Öğretmenliği', level: 'lisans' },
  { name: 'Okul Öncesi Öğretmenliği', level: 'lisans' },
  { name: 'Özel Eğitim Öğretmenliği', level: 'lisans' },
  { name: 'Rehberlik ve Psikolojik Danışmanlık (PDR)', level: 'lisans' },
  { name: 'İngilizce Öğretmenliği', level: 'lisans' },
  { name: 'Türkçe Öğretmenliği', level: 'lisans' },
  { name: 'İlköğretim Matematik Öğretmenliği', level: 'lisans' },
  { name: 'Fen Bilgisi Öğretmenliği', level: 'lisans' },
  { name: 'Sosyal Bilgiler Öğretmenliği', level: 'lisans' },
  { name: 'Din Kültürü ve Ahlak Bilgisi Öğretmenliği', level: 'lisans' },
  { name: 'Beden Eğitimi ve Spor Öğretmenliği', level: 'lisans' },
  { name: 'Antrenörlük Eğitimi', level: 'lisans' },
  { name: 'Spor Yöneticiliği', level: 'lisans' },
  // --- ÖNLİSANS (MYO Programları) ---
  { name: 'Bilgisayar Programcılığı', level: 'onlisans' },
  { name: 'Web Tasarımı ve Kodlama', level: 'onlisans' },
  { name: 'Bilişim Güvenliği Teknolojisi', level: 'onlisans' },
  { name: 'Bilgisayar Teknolojisi', level: 'onlisans' },
  { name: 'Dış Ticaret', level: 'onlisans' },
  { name: 'Büro Yönetimi ve Yönetici Asistanlığı', level: 'onlisans' },
  { name: 'Tıbbi Dokümantasyon ve Sekreterlik', level: 'onlisans' },
  { name: 'Tıbbi Sekreterlik', level: 'onlisans' },
  { name: 'Adalet', level: 'onlisans' },
  { name: 'Mahalli İdareler', level: 'onlisans' },
  { name: 'Yerel Yönetimler', level: 'onlisans' },
  { name: 'Muhasebe ve Vergi Uygulamaları', level: 'onlisans' },
  { name: 'İşletme Yönetimi', level: 'onlisans' },
  { name: 'Maliye (Önlisans)', level: 'onlisans' },
  { name: 'Lojistik', level: 'onlisans' },
  { name: 'Pazarlama', level: 'onlisans' },
  { name: 'Halkla İlişkiler ve Tanıtım (Önlisans)', level: 'onlisans' },
  { name: 'Bankacılık ve Sigortacılık', level: 'onlisans' },
  { name: 'İnsan Kaynakları Yönetimi (Önlisans)', level: 'onlisans' },
  { name: 'İtfaiyecilik ve Sivil Savunma', level: 'onlisans' },
  { name: 'Acil Durum ve Afet Yönetimi', level: 'onlisans' },
  { name: 'Emlak Yönetimi', level: 'onlisans' },
  { name: 'Harita ve Kadastro', level: 'onlisans' },
  { name: 'Tapu ve Kadastro', level: 'onlisans' },
  { name: 'İnşaat Teknolojisi', level: 'onlisans' },
  { name: 'Elektrik', level: 'onlisans' },
  { name: 'Elektrik Teknolojisi', level: 'onlisans' },
  { name: 'Elektronik Teknolojisi', level: 'onlisans' },
  { name: 'Elektronik Haberleşme Teknolojisi', level: 'onlisans' },
  { name: 'Makine', level: 'onlisans' },
  { name: 'Makine Teknolojisi', level: 'onlisans' },
  { name: 'Mekatronik', level: 'onlisans' },
  { name: 'Otomotiv Teknolojisi', level: 'onlisans' },
  { name: 'İklimlendirme ve Soğutma Teknolojisi', level: 'onlisans' },
  { name: 'İş Sağlığı ve Güvenliği', level: 'onlisans' },
  { name: 'Gıda Teknolojisi', level: 'onlisans' },
  { name: 'Laboratuvar Teknolojisi', level: 'onlisans' },
  { name: 'Kimya Teknolojisi', level: 'onlisans' },
  { name: 'Çağrı Merkezi Hizmetleri', level: 'onlisans' },
  { name: 'Aşçılık', level: 'onlisans' },
  { name: 'Anestezi', level: 'onlisans' },
  { name: 'Diyaliz', level: 'onlisans' },
  { name: 'İlk ve Acil Yardım (Paramedik)', level: 'onlisans' },
  { name: 'Odyometri', level: 'onlisans' },
  { name: 'Optisyenlik', level: 'onlisans' },
  { name: 'Eczane Hizmetleri', level: 'onlisans' },
  { name: 'Tıbbi Görüntüleme Teknikleri', level: 'onlisans' },
  { name: 'Tıbbi Laboratuvar Teknikleri', level: 'onlisans' },
  { name: 'Ağız ve Diş Sağlığı', level: 'onlisans' },
  { name: 'Diş Protez Teknolojisi', level: 'onlisans' },
  { name: 'Fizyoterapi (Önlisans)', level: 'onlisans' },
  { name: 'Ameliyathane Hizmetleri', level: 'onlisans' },
  { name: 'Patoloji Laboratuvar Teknikleri', level: 'onlisans' },
  { name: 'Ortopedik Protez ve Ortez', level: 'onlisans' },
  { name: 'Yaşlı Bakımı', level: 'onlisans' },
  { name: 'Evde Hasta Bakımı', level: 'onlisans' },
  { name: 'Çocuk Gelişimi', level: 'onlisans' },
  { name: 'Sosyal Güvenlik', level: 'onlisans' },
  { name: 'Sosyal Hizmetler (Önlisans)', level: 'onlisans' },
  { name: 'Özel Güvenlik ve Koruma', level: 'onlisans' },
  { name: 'Ceza İnfaz ve Güvenlik Hizmetleri', level: 'onlisans' },
  { name: 'Sivil Havacılık Kabin Hizmetleri', level: 'onlisans' },
  { name: 'Sivil Hava Ulaştırma İşletmeciliği', level: 'onlisans' },
  { name: 'Turizm ve Otel İşletmeciliği', level: 'onlisans' },
  { name: 'Radyo ve Televizyon Programcılığı', level: 'onlisans' },
  { name: 'Grafik Tasarımı', level: 'onlisans' },
  { name: 'Fotoğrafçılık ve Kameramanlık', level: 'onlisans' },
  { name: 'Basım ve Yayım Teknolojileri', level: 'onlisans' },
  { name: 'Ormancılık ve Orman Ürünleri', level: 'onlisans' },
  { name: 'Veterinerlik / Laborant ve Veteriner Sağlık', level: 'onlisans' },
  { name: 'Tarımsal İşletmecilik', level: 'onlisans' },
  { name: 'İlahiyat (Önlisans)', level: 'onlisans' },
  // --- ORTAÖĞRETİM / LİSE ---
  { name: 'Düz Lise / Anadolu Lisesi', level: 'ortaogretim' },
  { name: 'Bilişim Teknolojileri (Lise)', level: 'ortaogretim' },
  { name: 'Büro Yönetimi (Lise)', level: 'ortaogretim' },
  { name: 'Muhasebe ve Finansman (Lise)', level: 'ortaogretim' },
  { name: 'Sağlık Hizmetleri / Hemşirelik (Lise)', level: 'ortaogretim' },
  { name: 'Acil Tıp Teknisyenliği (ATT)', level: 'ortaogretim' },
  { name: 'Elektrik-Elektronik Teknolojisi (Lise)', level: 'ortaogretim' },
  { name: 'Makine Teknolojisi (Lise)', level: 'ortaogretim' },
  { name: 'Motorlu Araçlar Teknolojisi', level: 'ortaogretim' },
  { name: 'İnşaat Teknolojisi (Lise)', level: 'ortaogretim' },
  { name: 'Adalet (Lise)', level: 'ortaogretim' },
  { name: 'İmam Hatip Lisesi', level: 'ortaogretim' },
  { name: 'Yiyecek İçecek Hizmetleri', level: 'ortaogretim' },
  { name: 'Konaklama ve Seyahat Hizmetleri', level: 'ortaogretim' },
  { name: 'Gıda Teknolojisi (Lise)', level: 'ortaogretim' },
  { name: 'Tesisat Teknolojisi ve İklimlendirme', level: 'ortaogretim' },
  { name: 'Metal Teknolojisi', level: 'ortaogretim' },
  { name: 'Mobilya ve İç Mekan Tasarımı', level: 'ortaogretim' },
  { name: 'Tarım Teknolojileri', level: 'ortaogretim' },
  { name: 'Hayvan Yetiştiriciliği ve Sağlığı', level: 'ortaogretim' },
];

export const POPULAR_DEPARTMENTS: string[] = Array.from(
  new Set([...LISANS_DEPARTMENTS, ...ONLISANS_DEPARTMENTS])
);

export const DRIVER_LICENSE_OPTIONS = ['B', 'A1', 'A2', 'C', 'D', 'E', 'SRC-1', 'SRC-2', 'SRC-3', 'SRC-4'];

export const TURKEY_CITIES: string[] = [
  'Adana', 'Adıyaman', 'Afyonkarahisar', 'Ağrı', 'Aksaray', 'Amasya', 'Ankara', 'Antalya',
  'Ardahan', 'Artvin', 'Aydın', 'Balıkesir', 'Bartın', 'Batman', 'Bayburt', 'Bilecik',
  'Bingöl', 'Bitlis', 'Bolu', 'Burdur', 'Bursa', 'Çanakkale', 'Çankırı', 'Çorum',
  'Denizli', 'Diyarbakır', 'Düzce', 'Edirne', 'Elazığ', 'Erzincan', 'Erzurum', 'Eskişehir',
  'Gaziantep', 'Giresun', 'Gümüşhane', 'Hakkari', 'Hatay', 'Iğdır', 'Isparta', 'İstanbul',
  'İzmir', 'Kahramanmaraş', 'Karabük', 'Karaman', 'Kars', 'Kastamonu', 'Kayseri', 'Kırıkkale',
  'Kırklareli', 'Kırşehir', 'Kilis', 'Kocaeli', 'Konya', 'Kütahya', 'Malatya', 'Manisa',
  'Mardin', 'Mersin', 'Muğla', 'Muş', 'Nevşehir', 'Niğde', 'Ordu', 'Osmaniye',
  'Rize', 'Sakarya', 'Samsun', 'Siirt', 'Sinop', 'Sivas', 'Şanlıurfa', 'Şırnak',
  'Tekirdağ', 'Tokat', 'Trabzon', 'Tunceli', 'Uşak', 'Van', 'Yalova', 'Yozgat', 'Zonguldak',
];

export const UNIQUE_QUICK_PORTALS = [
  {
    name: 'ÖSYM AİS',
    description: 'Merkezi KPSS tercihleri, sınav sonuçları ve yerleştirme işlemleri.',
    url: 'https://ais.osym.gov.tr/',
    badge: 'Merkezi Atama',
  },
  {
    name: 'e-Devlet Kapısı',
    description: 'Mezuniyet, askerlik, adli sicil ve SGK hizmet dökümü belgeleri.',
    url: 'https://www.turkiye.gov.tr/',
    badge: 'Resmi Belge & Giriş',
  },
];

export const SAMPLE_PROFILE: UserProfile = {
  is_configured: true,
  full_name: 'Örnek KPSS Adayı',
  kpss_year: 2026,
  education_level: 'lisans',
  scores: {
    P3: 84.5,
    P93: null,
    P94: null,
    P1: 81.2,
    P2: null,
    P10: null,
    P121: null,
    EKPSS: null,
    YDS: 72.5,
  },
  departments: ['Bilgisayar Mühendisliği'],
  qualification_codes: ['4001', '4531'],
  birth_year: 1999,
  gender: 'belirtmek_istemiyorum',
  military_status: 'muaf_veya_yapildi',
  driver_licenses: ['B'],
  certificates: [],
  preferred_cities: [],
  all_cities: true,
  preferred_categories: [
    'memur',
    'sozlesmeli_4b',
    'merkezi_atama',
    'kpss_a',
    'isci',
    'akademik',
    'sydv',
  ],
  include_no_kpss: true,
  scan_interval_minutes: 60,
  telegram_bot_token: '',
  telegram_chat_id: '',
  webhook_url: '',
};

export function formatRelativeDateTime(iso: string | null | undefined): string {
  if (!iso) return 'Henüz taranmadı';
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  const diffMs = Date.now() - dt.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Az önce';
  if (diffMin < 60) return `${diffMin} dk önce`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour} saat önce`;
  return dt.toLocaleString('tr-TR', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatTurkishDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Tarih detayda';
  const parsed = new Date(dateStr.includes('T') ? dateStr : `${dateStr}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return dateStr;
  return parsed.toLocaleDateString('tr-TR', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
}

function normalizeLinkUrl(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

/**
 * Kaynak listesini URL bazında tekilleştirir ve kaynak URL'lerinden farklı olan
 * en öncelikli (Resmî Gazete / SBB) tek bir Resmi PDF bağlantısı döndürür.
 */
export function deduplicateAnnouncementLinks(sources: AnnouncementSource[]): {
  uniqueSources: AnnouncementSource[];
  primaryPdfUrl: string | null;
} {
  const seenUrls = new Set<string>();
  const uniqueSources: AnnouncementSource[] = [];

  for (const src of sources) {
    const rawUrl = src.url?.trim();
    if (!rawUrl) continue;
    const norm = normalizeLinkUrl(rawUrl);
    if (seenUrls.has(norm)) continue;
    seenUrls.add(norm);
    uniqueSources.push(src);
  }

  const priorityRank = (sourceName: string): number => {
    if (sourceName === 'resmi_gazete') return 0;
    if (sourceName === 'sbb_kamuilan') return 1;
    if (sourceName === 'osym') return 2;
    return 3;
  };

  const sortedForPdf = [...sources].sort(
    (a, b) => priorityRank(a.source_name) - priorityRank(b.source_name)
  );

  let primaryPdfUrl: string | null = null;
  for (const src of sortedForPdf) {
    const pdf = src.pdf_url?.trim();
    if (!pdf) continue;
    const normPdf = normalizeLinkUrl(pdf);
    if (!seenUrls.has(normPdf)) {
      primaryPdfUrl = pdf;
      break;
    }
  }

  return { uniqueSources, primaryPdfUrl };
}
