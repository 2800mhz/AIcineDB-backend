# Festival Film Scraper Implementation - Summary

## ✅ Implementation Complete

This feature allows admins to automatically scrape films from festival showcase websites (like AIFF/Runway AI Film Festival) and import them into the AIcineDB database.

## What Was Implemented

### 1. Core Scraper Service
**File**: `backend/services/festival_film_scraper.py`

- `FestivalFilmScraper` class with async support
- AIFF-specific scraper (Runway AI Film Festival)
- Generic scraper for other festival sites
- YouTube embed extraction from iframes
- Metadata extraction (title, director, category, description, duration)
- Category detection (Grand Prix, Gold, Silver, Merit, Honoree)
- Robust error handling

### 2. API Endpoint
**File**: `backend/api/festivals.py`

- **Endpoint**: `POST /festivals/scrape-films`
- **Access**: Admin only (requires admin authentication)
- **Features**:
  - Request validation
  - Duplicate detection (by YouTube URL)
  - Automatic title creation in Supabase
  - Festival linking via PostgreSQL
  - Comprehensive error reporting

### 3. Database Migrations

**PostgreSQL Migration** (`006_add_title_id_to_festival_submissions.sql`):
- Added `title_id UUID` for Supabase titles
- Added `is_winner BOOLEAN` for award tracking
- Made `film_id` nullable
- Added check constraint (film_id OR title_id required)

**Supabase Migration** (`007_add_festival_fields_to_supabase_titles.sql`):
- Added `festival_source_url TEXT`
- Added `festival_category VARCHAR(100)`
- Added `is_festival_film BOOLEAN`
- Created indexes

### 4. Request/Response Schemas
**File**: `backend/models/schemas.py`

- `FestivalFilmScrapeRequest`: Input schema
- `FestivalFilmScrapeResponse`: Output schema
- `ScrapedFilmData`: Film data structure

### 5. Documentation & Examples
- `FESTIVAL_FILM_SCRAPER.md`: Comprehensive Turkish documentation
- `examples/festival_scraper_examples.py`: Usage examples
- `validate_festival_scraper.py`: Code validation script

## How It Works

```
1. Admin enters festival URL (e.g., https://aiff.runwayml.com/2024)
   ↓
2. Backend scrapes the website using Playwright
   ↓
3. Extracts YouTube embeds and metadata
   ↓
4. For each film:
   - Check if exists (by YouTube URL)
   - Create new title in Supabase (if not exists)
   - Link to festival in PostgreSQL (if festival_id provided)
   ↓
5. Return statistics (found, imported, skipped)
```

## API Usage

### Request
```bash
POST /festivals/scrape-films
Authorization: Bearer {ADMIN_TOKEN}
Content-Type: application/json

{
  "festival_url": "https://aiff.runwayml.com/2024",
  "festival_name": "Runway AI Film Festival 2024",
  "festival_id": "uuid-optional"
}
```

### Response
```json
{
  "films_found": 15,
  "films_imported": 12,
  "films_skipped": 3,
  "films": [
    {
      "title": "The Last Frame",
      "director": "John Doe",
      "youtube_url": "https://youtube.com/watch?v=...",
      "category": "Grand Prix",
      "description": "A stunning AI film...",
      "duration": "5:30",
      "festival_source_url": "https://aiff.runwayml.com/2024"
    }
  ],
  "errors": []
}
```

## Installation

1. **Install Playwright**:
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **Run PostgreSQL migration**:
   ```bash
   psql -d your_db -f backend/database/migrations/006_add_title_id_to_festival_submissions.sql
   ```

3. **Run Supabase migration**:
   - Open Supabase SQL Editor
   - Run `backend/database/migrations/007_add_festival_fields_to_supabase_titles.sql`

4. **Test the endpoint** with admin credentials

## Security Features

✅ Admin-only access (requires admin JWT token)  
✅ Input validation (Pydantic schemas)  
✅ Duplicate prevention (check by YouTube URL)  
✅ Error handling (comprehensive logging)  
✅ Database layer separation (Supabase + PostgreSQL)

## Code Quality

✅ All syntax validated  
✅ Code review completed and issues fixed  
✅ Comprehensive documentation  
✅ Usage examples provided  
✅ Validation script included

## Files Changed/Added

**New Files**:
- `backend/services/festival_film_scraper.py` (432 lines)
- `backend/database/migrations/006_add_title_id_to_festival_submissions.sql`
- `backend/database/migrations/007_add_festival_fields_to_supabase_titles.sql`
- `FESTIVAL_FILM_SCRAPER.md`
- `validate_festival_scraper.py`
- `examples/festival_scraper_examples.py`

**Modified Files**:
- `requirements.txt` (added playwright)
- `backend/api/festivals.py` (added endpoint)
- `backend/models/schemas.py` (added schemas)

## Testing

Run validation:
```bash
python3 validate_festival_scraper.py
```

Expected output:
```
✅ All tests passed! (9/9)
```

## Future Enhancements (Optional)

- [ ] Celery task for background scraping
- [ ] Support more festival websites
- [ ] Scraping cache system
- [ ] Web UI for admin management
- [ ] Scheduled/periodic scraping
- [ ] Bulk export/import

## Support

For detailed documentation, see:
- `FESTIVAL_FILM_SCRAPER.md` - Full feature documentation
- `examples/festival_scraper_examples.py` - Code examples

## Status

**Implementation Status**: ✅ COMPLETE  
**Code Review Status**: ✅ APPROVED  
**Ready for Merge**: ✅ YES

---

**Implementation Date**: January 2, 2026  
**Developer**: GitHub Copilot  
**Repository**: 2800mhz/AIcineDB-backend
