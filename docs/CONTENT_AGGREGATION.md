# Content Aggregation System Documentation

## Overview

The AIcineDB Content Aggregation System automatically discovers film festivals and aggregates cinema news from multiple sources, using AI to filter content for relevance to AI-generated filmmaking.

## Architecture

### Components

1. **Festival Scraper** (`backend/services/festival_scraper.py`)
   - Scrapes festivals from FilmFreeway, Festhome, and RSS feeds
   - Extracts festival metadata (dates, location, fees, etc.)
   - Implements rate limiting and retry logic

2. **News Aggregator** (`backend/services/news_aggregator.py`)
   - Aggregates news from RSS feeds (Variety, THR, IndieWire, etc.)
   - Extracts articles, images, and metadata
   - Deduplicates by URL

3. **AI Filter** (`backend/services/ai_filter.py`)
   - Filters festivals for AI-film friendliness (0-100 score)
   - Filters news for AI/cinema relevance (0-100 score)
   - Calculates festival prestige scores
   - Detects duplicates using embeddings

4. **Celery Tasks** (`backend/tasks/content_tasks.py`)
   - `scrape_festivals`: Daily at 3 AM
   - `aggregate_news`: Every 6 hours
   - `cleanup_old_news`: Weekly on Sunday

5. **API Endpoints** (`backend/api/content.py`)
   - News management endpoints
   - Discovered festivals management
   - Sources configuration
   - Scraping jobs monitoring

## Database Schema

### Tables

#### `discovered_festivals`
Stores scraped festivals pending admin approval.

```sql
CREATE TABLE discovered_festivals (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    external_url TEXT,
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    submission_deadline TIMESTAMP,
    location VARCHAR(255),
    country VARCHAR(100),
    category TEXT[],
    genres TEXT[],
    entry_fee DECIMAL(10,2),
    currency VARCHAR(10),
    ai_relevance_score INTEGER,
    is_ai_film_friendly BOOLEAN,
    prestige_score INTEGER,
    embedding vector(1536),
    source VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    ...
);
```

#### `news_articles`
Stores aggregated news articles.

```sql
CREATE TABLE news_articles (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    external_url TEXT NOT NULL UNIQUE,
    image_url TEXT,
    author VARCHAR(255),
    source_name VARCHAR(255),
    category TEXT[],
    tags TEXT[],
    ai_relevance_score INTEGER,
    is_ai_cinema_relevant BOOLEAN,
    embedding vector(1536),
    published_at TIMESTAMP,
    is_archived BOOLEAN DEFAULT false,
    ...
);
```

#### `news_sources`
Configuration for news RSS feeds.

```sql
CREATE TABLE news_sources (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) DEFAULT 'rss',
    is_active BOOLEAN DEFAULT true,
    fetch_interval_hours INTEGER DEFAULT 6,
    last_fetched_at TIMESTAMP,
    ...
);
```

#### `festival_sources`
Configuration for festival scraping sources.

```sql
CREATE TABLE festival_sources (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL UNIQUE,
    source_type VARCHAR(50) DEFAULT 'scraper',
    is_active BOOLEAN DEFAULT true,
    scrape_interval_hours INTEGER DEFAULT 24,
    ...
);
```

#### `scraping_jobs`
Track scraping job history and performance.

```sql
CREATE TABLE scraping_jobs (
    id UUID PRIMARY KEY,
    job_type VARCHAR(50) NOT NULL,
    source VARCHAR(100),
    status VARCHAR(50),
    items_found INTEGER,
    items_new INTEGER,
    items_duplicates INTEGER,
    items_filtered INTEGER,
    error_message TEXT,
    duration_seconds INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    ...
);
```

## How It Works

### Festival Scraping Pipeline

1. **Scheduled Task** (Daily at 3 AM)
   ```
   scrape_festivals_task()
   ```

2. **Scraping Phase**
   - FilmFreeway: Scrapes festival listing pages
   - Festhome: Scrapes festival directory
   - RSS Feeds: Parses festival RSS feeds
   - Combines results from all sources

3. **AI Filtering Phase**
   - For each festival:
     - Generate AI relevance score (0-100)
     - Calculate prestige score (0-100)
     - Generate embedding for duplicate detection
   - Filter out festivals below threshold (default: 60)

4. **Duplicate Detection**
   - Compare embeddings using cosine similarity
   - Remove duplicates (similarity >= 0.95)

5. **Storage**
   - Save to `discovered_festivals` table
   - Status: `pending` (awaits admin approval)
   - Update `scraping_jobs` table

6. **Admin Review**
   - Admin views pending festivals via API
   - Approves → Moves to `festivals` table
   - Rejects → Marks as `rejected` with reason

### News Aggregation Pipeline

1. **Scheduled Task** (Every 6 hours)
   ```
   aggregate_news_task()
   ```

2. **Aggregation Phase**
   - Fetch RSS feeds from all sources
   - Parse articles, extract metadata
   - Extract images, tags, categories
   - Deduplicate by URL

3. **AI Filtering Phase**
   - For each article:
     - Generate AI relevance score (0-100)
     - Generate embedding
   - Filter out articles below threshold (default: 70)

4. **Storage**
   - Save to `news_articles` table
   - Skip if URL already exists
   - Update `news_sources.last_fetched_at`

5. **Cleanup** (Weekly)
   - Archive articles older than 90 days
   - Set `is_archived = true`

## API Endpoints

### News Endpoints

#### List News Articles
```http
GET /api/news?is_archived=false&category=festivals&skip=0&limit=50
```

Response:
```json
[
  {
    "id": "uuid",
    "title": "AI Films Take Cannes by Storm",
    "summary": "...",
    "external_url": "https://variety.com/...",
    "image_url": "https://...",
    "source_name": "Variety",
    "ai_relevance_score": 92,
    "is_ai_cinema_relevant": true,
    "category": ["festivals", "technology"],
    "tags": ["ai", "cannes"],
    "published_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Get Single Article
```http
GET /api/news/{id}
```

#### Trigger News Aggregation (Admin)
```http
POST /api/news/refresh
Authorization: Bearer {admin_token}
```

### Discovered Festivals Endpoints

#### List Discovered Festivals (Admin)
```http
GET /api/festivals/discovered?status=pending&skip=0&limit=50
Authorization: Bearer {admin_token}
```

Response:
```json
[
  {
    "id": "uuid",
    "name": "AI Cinema Festival 2024",
    "external_url": "https://...",
    "description": "...",
    "location": "San Francisco, USA",
    "ai_relevance_score": 85,
    "is_ai_film_friendly": true,
    "prestige_score": 65,
    "status": "pending",
    "created_at": "2024-01-20T10:00:00Z"
  }
]
```

#### Get Festival Details (Admin)
```http
GET /api/festivals/discovered/{id}
Authorization: Bearer {admin_token}
```

#### Approve/Reject Festival (Admin)
```http
POST /api/festivals/discovered/{id}/approve
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "action": "approve"
}
```

Or reject:
```json
{
  "action": "reject",
  "rejection_reason": "Duplicate of existing festival"
}
```

#### Trigger Festival Scraping (Admin)
```http
POST /api/festivals/refresh
Authorization: Bearer {admin_token}
```

### Sources Endpoints

#### List News Sources
```http
GET /api/sources/news?is_active=true
```

#### Add News Source (Admin)
```http
POST /api/sources/news
Authorization: Bearer {admin_token}
Content-Type: application/json

{
  "name": "Custom Film Blog",
  "url": "https://example.com/feed.xml",
  "source_type": "rss",
  "is_active": true,
  "fetch_interval_hours": 12
}
```

#### Update News Source (Admin)
```http
PUT /api/sources/news/{id}
Authorization: Bearer {admin_token}
```

#### List Festival Sources
```http
GET /api/sources/festivals?is_active=true
```

#### Add Festival Source (Admin)
```http
POST /api/sources/festivals
Authorization: Bearer {admin_token}
```

### Scraping Jobs Endpoints

#### List Scraping Jobs
```http
GET /api/scraping-jobs?job_type=festivals&status=completed&skip=0&limit=50
```

Response:
```json
[
  {
    "id": "uuid",
    "job_type": "festivals",
    "source": "all",
    "status": "completed",
    "items_found": 150,
    "items_new": 42,
    "items_duplicates": 18,
    "items_filtered": 90,
    "duration_seconds": 245,
    "started_at": "2024-01-20T03:00:00Z",
    "completed_at": "2024-01-20T03:04:05Z"
  }
]
```

#### Get Job Details
```http
GET /api/scraping-jobs/{id}
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Scraping Configuration
SCRAPING_USER_AGENT=AICineDB Bot/1.0
SCRAPING_RATE_LIMIT_DELAY=2
SCRAPING_MAX_RETRIES=3

# AI Filtering
AI_FILTER_ENABLED=true
AI_RELEVANCE_THRESHOLD_FESTIVALS=60
AI_RELEVANCE_THRESHOLD_NEWS=70
DUPLICATE_SIMILARITY_THRESHOLD=0.95

# OpenAI (required for embeddings and AI filtering)
OPENAI_API_KEY=your_openai_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Supabase (required for content storage)
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here
```

### Celery Beat Schedule

The system runs these tasks automatically:

- **Festival Scraping**: Daily at 3:00 AM UTC
- **News Aggregation**: Every 6 hours (0:00, 6:00, 12:00, 18:00)
- **Old News Cleanup**: Weekly on Sunday at 2:00 AM UTC

To modify schedules, edit `backend/tasks/celery_app.py`:

```python
app.conf.beat_schedule = {
    'scrape-festivals-daily': {
        'task': 'scrape_festivals',
        'schedule': crontab(hour=3, minute=0),
    },
    # ...
}
```

## Adding New Sources

### Add News Source

1. **Via API (Recommended)**
   ```bash
   curl -X POST https://api.example.com/api/sources/news \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "My News Source",
       "url": "https://example.com/feed.xml",
       "source_type": "rss",
       "fetch_interval_hours": 12
     }'
   ```

2. **Via Database**
   ```sql
   INSERT INTO news_sources (name, url, source_type, is_active)
   VALUES ('My News Source', 'https://example.com/feed.xml', 'rss', true);
   ```

### Add Festival Source

1. **Via API**
   ```bash
   curl -X POST https://api.example.com/api/sources/festivals \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "My Festival Directory",
       "url": "https://example.com/festivals",
       "source_type": "scraper",
       "scrape_interval_hours": 24
     }'
   ```

2. **Via Code** (for custom scrapers)
   
   Edit `backend/services/festival_scraper.py`:
   ```python
   async def scrape_my_source(self) -> List[Dict]:
       """Scrape festivals from my custom source"""
       festivals = []
       # Implement scraping logic
       return festivals
   
   # Add to scrape_all_sources():
   async def scrape_all_sources(self):
       results = await asyncio.gather(
           self.scrape_filmfreeway(),
           self.scrape_festhome(),
           self.scrape_my_source(),  # Add here
           return_exceptions=True
       )
   ```

## Admin Workflow

### Approving Festivals

1. **View Pending Festivals**
   ```bash
   GET /api/festivals/discovered?status=pending
   ```

2. **Review Festival Details**
   ```bash
   GET /api/festivals/discovered/{id}
   ```
   
   Check:
   - AI relevance score (should be >= 60)
   - Prestige score
   - Festival description and dates
   - Duplicate check

3. **Approve**
   ```bash
   POST /api/festivals/discovered/{id}/approve
   {
     "action": "approve"
   }
   ```
   
   This moves the festival to the main `festivals` table.

4. **Reject** (if duplicate or irrelevant)
   ```bash
   POST /api/festivals/discovered/{id}/approve
   {
     "action": "reject",
     "rejection_reason": "Duplicate of Cannes Film Festival"
   }
   ```

### Monitoring Scraping Jobs

1. **View Recent Jobs**
   ```bash
   GET /api/scraping-jobs?limit=10
   ```

2. **Check Job Details**
   ```bash
   GET /api/scraping-jobs/{id}
   ```
   
   Monitor:
   - Duration
   - Items found vs. filtered
   - Duplicate count
   - Error messages

## Troubleshooting

### Issue: No Festivals Being Found

**Possible Causes:**
- Website structure changed
- Rate limiting or blocking
- Network issues

**Solutions:**
1. Check scraping job error messages:
   ```bash
   GET /api/scraping-jobs?status=failed
   ```

2. Test scraper manually:
   ```python
   python backend/services/festival_scraper.py
   ```

3. Check source accessibility:
   ```bash
   curl -A "AICineDB Bot/1.0" https://filmfreeway.com/festivals
   ```

### Issue: AI Filtering Not Working

**Possible Causes:**
- Missing OpenAI API key
- Invalid API key
- API quota exceeded

**Solutions:**
1. Check environment variables:
   ```bash
   echo $OPENAI_API_KEY
   ```

2. Test OpenAI connection:
   ```python
   from backend.services.ai_filter import AIFilter
   import asyncio
   
   async def test():
       ai_filter = AIFilter()
       print(f"AI Filter enabled: {ai_filter.enabled}")
   
   asyncio.run(test())
   ```

3. Check API usage at https://platform.openai.com/usage

### Issue: Too Many Duplicates

**Possible Causes:**
- Low similarity threshold
- Poor embedding quality

**Solutions:**
1. Adjust threshold in `.env`:
   ```bash
   DUPLICATE_SIMILARITY_THRESHOLD=0.98  # Increase (more strict)
   ```

2. Review duplicate festivals manually and reject appropriately

### Issue: Celery Tasks Not Running

**Possible Causes:**
- Celery worker not running
- Celery beat not running
- Redis connection issues

**Solutions:**
1. Check Celery worker status:
   ```bash
   celery -A backend.tasks.celery_app inspect active
   ```

2. Check Celery beat status:
   ```bash
   celery -A backend.tasks.celery_app inspect scheduled
   ```

3. Check Redis connection:
   ```bash
   redis-cli ping
   ```

4. Restart services:
   ```bash
   celery -A backend.tasks.celery_app worker --loglevel=info
   celery -A backend.tasks.celery_app beat --loglevel=info
   ```

## Performance Metrics

### Expected Performance

- **Festival Scraping**: 50-100 festivals per day
- **News Aggregation**: 100-200 articles per day
- **AI Filter Reduction**: 70%+ noise reduction
- **Duplicate Detection**: 95%+ accuracy
- **Admin Approval Time**: <2 minutes per festival

### Monitoring

Track these metrics:
- Items found vs. filtered ratio
- Duplicate detection accuracy
- Scraping job duration
- API response times
- Error rates

## Security Considerations

1. **Rate Limiting**: Respect source website rate limits
2. **User Agent**: Use identifiable user agent
3. **API Keys**: Store securely in environment variables
4. **Admin Only**: Restrict manual triggers to admins
5. **Input Validation**: Validate all external data
6. **Error Handling**: Don't expose internal errors

## Maintenance

### Regular Tasks

- **Weekly**: Review approved festivals
- **Monthly**: Check source configurations
- **Quarterly**: Update scrapers for website changes
- **As Needed**: Add new sources

### Updating Scrapers

When a source website changes structure:

1. Update selectors in scraper code
2. Test scraper manually
3. Deploy update
4. Trigger manual scrape to verify
5. Monitor for errors

## Support

For issues or questions:
- Check logs: `backend/tasks/content_tasks.py`
- Review API documentation: `/docs`
- Test services manually using test scripts
