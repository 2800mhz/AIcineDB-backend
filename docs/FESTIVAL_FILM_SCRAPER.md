# Festival Film Scraper

Otomatik olarak festival sitelerinden (örn: AIFF, Runway AI Film Festival) film bilgilerini çeker ve veritabanına kaydeder.

## Özellikler

- **JavaScript destekli scraping**: Playwright kullanarak JS ile render edilen siteleri scrape eder
- **YouTube embed çıkarma**: Festival sitelerindeki YouTube iframe'lerini otomatik bulur
- **Metadata çıkarma**: Film başlığı, yönetmen, kategori, açıklama, süre bilgilerini çıkarır
- **AIFF özel desteği**: Runway AI Film Festival için optimize edilmiş scraper
- **Genel scraper**: Diğer festival siteleri için genel amaçlı scraper
- **Veritabanı entegrasyonu**: Filmleri otomatik olarak `titles` tablosuna kaydeder ve festivale bağlar

## Kurulum

### 1. Playwright Kurulumu

```bash
pip install playwright
playwright install chromium
```

### 2. Database Migration'ları Çalıştırın

**PostgreSQL (festival_submissions için):**
```bash
psql -d your_database -f backend/database/migrations/006_add_title_id_to_festival_submissions.sql
```

**Supabase SQL Editor'da (titles tablosu için):**
```sql
-- backend/database/migrations/007_add_festival_fields_to_supabase_titles.sql dosyasının içeriğini çalıştırın
```

## Kullanım

### API Endpoint

**POST `/festivals/scrape-films`** (Admin only)

**Request Body:**
```json
{
  "festival_url": "https://aiff.runwayml.com/2024",
  "festival_name": "Runway AI Film Festival 2024",
  "festival_id": "uuid-of-festival"  // optional
}
```

**Response:**
```json
{
  "films_found": 15,
  "films_imported": 12,
  "films_skipped": 3,
  "films": [
    {
      "title": "The Last Frame",
      "director": "John Doe",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "category": "Grand Prix",
      "description": "A stunning AI-generated film about...",
      "duration": "5:30",
      "festival_source_url": "https://aiff.runwayml.com/2024"
    }
  ],
  "errors": []
}
```

### Python Servisi Olarak Kullanım

```python
from backend.services.festival_film_scraper import FestivalFilmScraper

# Initialize scraper
scraper = FestivalFilmScraper()

# Scrape films from festival
films = await scraper.scrape_festival_films("https://aiff.runwayml.com/2024")

# Process films
for film in films:
    print(f"Title: {film['title']}")
    print(f"YouTube: {film['youtube_url']}")
    print(f"Category: {film['category']}")
```

## İş Akışı

1. **Admin festival URL'sini girer** (örn: aiff.runwayml.com/2024)
2. **Backend siteyi scrape eder**:
   - Playwright ile sayfayı yükler
   - YouTube embed'lerini bulur
   - Her film için metadata çıkarır (başlık, yönetmen, kategori)
3. **Her film için**:
   - YouTube URL'si ile `titles` tablosunda arama yapar
   - Yoksa yeni kayıt oluşturur:
     ```sql
     INSERT INTO titles (
       title,
       trailer_youtube_url,
       director,
       description,
       festival_source_url,
       is_festival_film,
       status
     ) VALUES (...)
     ```
   - `festival_id` verilmişse `festival_submissions` ile festival bağlantısı kurar:
     ```sql
     INSERT INTO festival_submissions (
       festival_id,
       title_id,
       category,
       status,
       is_winner
     ) VALUES (...)
     ```
4. **Frontend'de gösterim**:
   - `is_festival_film = true` olan filmler festival badge'i ile gösterilir
   - `festival_source_url` kaynak linki olarak gösterilir
   - `category` kategorisi gösterilir (Grand Prix, Gold, Silver, vb.)

## Desteklenen Festival Siteleri

### AIFF (Runway AI Film Festival)
- ✅ URL formatı: `https://aiff.runwayml.com/2024`
- ✅ Özel scraper ile optimize edilmiş
- ✅ Kategoriler: Grand Prix, Gold, Silver, Merit, Honoree
- ✅ YouTube embed desteği

### Diğer Festival Siteleri
- ✅ Genel scraper ile desteklenir
- ✅ YouTube embed içeren herhangi bir festival sitesi
- ⚠️ Metadata çıkarma daha sınırlı olabilir

## Database Şeması

### titles tablosu (Supabase)
```sql
-- Yeni eklenen alanlar:
festival_source_url TEXT           -- Festival sitesi URL'si
festival_category VARCHAR(100)     -- Kategori (Grand Prix, Gold, vb.)
is_festival_film BOOLEAN           -- Festival filmi mi?
```

### festival_submissions tablosu (PostgreSQL)
```sql
-- Yeni/güncellenmiş alanlar:
title_id UUID                      -- Supabase titles referansı (YENI)
film_id INTEGER                    -- Alternatif: Local films referansı
is_winner BOOLEAN                  -- Ödül kazandı mı?
category VARCHAR(100)              -- Kategori
```

## Örnek Kullanım Senaryoları

### 1. AIFF 2024 Filmlerini İçe Aktarma

**cURL:**
```bash
curl -X POST "https://your-api.com/festivals/scrape-films" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "festival_url": "https://aiff.runwayml.com/2024",
    "festival_name": "Runway AI Film Festival 2024"
  }'
```

**Python:**
```python
import httpx

response = httpx.post(
    "https://your-api.com/festivals/scrape-films",
    headers={"Authorization": "Bearer YOUR_ADMIN_TOKEN"},
    json={
        "festival_url": "https://aiff.runwayml.com/2024",
        "festival_name": "Runway AI Film Festival 2024"
    }
)
print(response.json())
```

### 2. Mevcut Festival'e Film Bağlama

```python
# Önce festival oluştur
festival_response = httpx.post(
    "https://your-api.com/festivals",
    headers={"Authorization": "Bearer YOUR_ADMIN_TOKEN"},
    json={
        "name": "Runway AI Film Festival 2024",
        "slug": "aiff-2024",
        "start_date": "2024-12-01T00:00:00Z",
        "end_date": "2024-12-15T00:00:00Z",
        "location": "Online"
    }
)
festival_id = festival_response.json()["id"]

# Sonra filmleri scrape et ve festivale bağla
scrape_response = httpx.post(
    "https://your-api.com/festivals/scrape-films",
    headers={"Authorization": "Bearer YOUR_ADMIN_TOKEN"},
    json={
        "festival_url": "https://aiff.runwayml.com/2024",
        "festival_id": festival_id
    }
)
```

## Hata Yönetimi

Scraper şu durumlarda hata döner:

- **Playwright kurulu değil**: `RuntimeError: Playwright is not installed`
- **Sayfa yüklenemedi**: Timeout hatası, response içinde `errors` listesinde gösterilir
- **YouTube embed bulunamadı**: Boş film listesi döner
- **Database hatası**: Film oluşturma/güncelleme başarısız, `errors` listesinde gösterilir

Her film için ayrı ayrı hata yönetimi yapılır, bir film başarısız olsa bile diğerleri işlenmeye devam eder.

## Performans

- **AIFF scraping**: ~5-10 saniye (15 film için)
- **Generic scraping**: ~3-8 saniye (site yapısına göre)
- **Database import**: Film başına ~100-200ms

## Güvenlik

- ✅ **Admin-only endpoint**: Sadece admin kullanıcılar scraping yapabilir
- ✅ **Duplicate kontrolü**: Aynı YouTube URL'si ile birden fazla film oluşturmaz
- ✅ **Input validation**: Pydantic ile URL ve data validasyonu
- ✅ **Error handling**: Tüm hatalar yakalanır ve loglanır

## Sınırlamalar

- **JavaScript gereksinimi**: Playwright chromium kurulumu gerektirir (~170MB)
- **Rate limiting**: Aşırı kullanımda festival sitesinden ban yiyebilirsiniz
- **Site yapısı değişiklikleri**: Festival siteleri yapısını değiştirirse scraper güncellemesi gerekebilir
- **Metadata doğruluğu**: Özellikle genel scraper ile metadata %100 doğru olmayabilir

## Gelecek Geliştirmeler

- [ ] Celery task ile background scraping
- [ ] Daha fazla festival sitesi desteği
- [ ] Otomatik periyodik scraping (günlük/haftalık)
- [ ] Scraping önbelleği (cache) sistemi
- [ ] Web UI for admin scraping kontrolü
- [ ] Film metadata iyileştirme (AI ile)
- [ ] Bulk import/export desteği

## Sorun Giderme

### Playwright yükleme hatası
```bash
# Linux/Mac
pip install playwright
playwright install chromium

# Windows
pip install playwright
playwright install chromium

# Docker
RUN playwright install chromium --with-deps
```

### "No module named 'playwright'" hatası
```bash
pip install playwright>=1.40.0
```

### Chromium browser bulunamadı
```bash
playwright install chromium
```

### Database migration hatası
```sql
-- PostgreSQL'de migration durumunu kontrol edin:
SELECT * FROM schema_migrations;

-- Manuel olarak çalıştırın:
\i backend/database/migrations/006_add_title_id_to_festival_submissions.sql
```

## Lisans

Bu proje AIcineDB Backend projesinin bir parçasıdır.
