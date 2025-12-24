"""
Content Aggregation Celery Tasks
Automated tasks for periodic festival scraping and news aggregation
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="scrape_festivals", bind=True)
def scrape_festivals_task(self):
    """
    Run daily at 3 AM to scrape festivals from all sources
    
    Process:
    1. Fetch from all sources (FilmFreeway, Festhome, RSS)
    2. AI filter (relevance >= 60)
    3. Generate embeddings
    4. Detect duplicates
    5. Save to discovered_festivals table
    6. Update scraping_jobs table
    """
    import asyncio
    from backend.services.festival_scraper import FestivalScraper
    from backend.services.ai_filter import AIFilter
    from backend.services.supabase_sync import SupabaseSyncService
    
    logger.info("🎬 Starting festival scraping task...")
    
    job_id = None
    start_time = datetime.now()
    
    try:
        # Create scraping job record
        supabase_service = SupabaseSyncService()
        
        # Run async scraping
        async def run_scraping():
            nonlocal job_id
            
            # Create job record
            if supabase_service.enabled:
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        json={
                            "job_type": "festivals",
                            "source": "all",
                            "status": "running",
                            "started_at": start_time.isoformat()
                        }
                    )
                    if response.status_code in [200, 201]:
                        result = response.json()
                        if result and len(result) > 0:
                            job_id = result[0].get('id')
            
            # 1. Scrape festivals
            scraper = FestivalScraper()
            festivals = await scraper.scrape_all_sources()
            logger.info(f"📊 Found {len(festivals)} festivals")
            
            if not festivals:
                return {
                    "items_found": 0,
                    "items_new": 0,
                    "items_filtered": 0,
                    "items_duplicates": 0
                }
            
            # 2. AI filter
            ai_filter = AIFilter()
            filtered_festivals = await ai_filter.filter_festivals(festivals)
            logger.info(f"✓ {len(filtered_festivals)} festivals passed AI filter")
            
            # 3. Detect duplicates
            unique_festivals = await ai_filter.detect_duplicates(filtered_festivals)
            logger.info(f"✓ {len(unique_festivals)} unique festivals")
            
            # 4. Save to Supabase
            saved_count = 0
            for festival in unique_festivals:
                festival_id = await supabase_service.sync_discovered_festival(festival)
                if festival_id:
                    saved_count += 1
            
            logger.info(f"✅ Saved {saved_count} festivals to database")
            
            return {
                "items_found": len(festivals),
                "items_new": saved_count,
                "items_filtered": len(festivals) - len(filtered_festivals),
                "items_duplicates": len(filtered_festivals) - len(unique_festivals)
            }
        
        # Run the async function
        result = asyncio.run(run_scraping())
        
        # Update job status
        if supabase_service.enabled and job_id:
            async def update_job():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            **result
                        }
                    )
            
            asyncio.run(update_job())
        
        logger.info(f"✅ Festival scraping completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Festival scraping failed: {e}", exc_info=True)
        
        # Update job as failed
        if job_id:
            async def mark_failed():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "failed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            "error_message": str(e)
                        }
                    )
            
            asyncio.run(mark_failed())
        
        raise


@shared_task(name="aggregate_news", bind=True)
def aggregate_news_task(self):
    """
    Run every 6 hours to fetch news from RSS feeds
    
    Process:
    1. Fetch from RSS feeds
    2. AI filter (relevance >= 70)
    3. Generate embeddings
    4. Deduplicate by URL
    5. Save to news_articles table
    6. Update news_sources.last_fetched_at
    """
    import asyncio
    from backend.services.news_aggregator import NewsAggregator
    from backend.services.ai_filter import AIFilter
    from backend.services.supabase_sync import SupabaseSyncService
    
    logger.info("📰 Starting news aggregation task...")
    
    job_id = None
    start_time = datetime.now()
    
    try:
        supabase_service = SupabaseSyncService()
        
        async def run_aggregation():
            nonlocal job_id
            
            # Create job record
            if supabase_service.enabled:
                import httpx
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        json={
                            "job_type": "news",
                            "source": "all",
                            "status": "running",
                            "started_at": start_time.isoformat()
                        }
                    )
                    if response.status_code in [200, 201]:
                        result = response.json()
                        if result and len(result) > 0:
                            job_id = result[0].get('id')
            
            # 1. Aggregate news
            aggregator = NewsAggregator()
            articles = await aggregator.fetch_and_deduplicate()
            logger.info(f"📊 Found {len(articles)} unique articles")
            
            if not articles:
                return {
                    "items_found": 0,
                    "items_new": 0,
                    "items_filtered": 0,
                    "items_duplicates": 0
                }
            
            # 2. AI filter
            ai_filter = AIFilter()
            filtered_articles = await ai_filter.filter_news(articles)
            logger.info(f"✓ {len(filtered_articles)} articles passed AI filter")
            
            # 3. Save to Supabase
            saved_count = 0
            for article in filtered_articles:
                article_id = await supabase_service.sync_news_article(article)
                if article_id:
                    saved_count += 1
            
            logger.info(f"✅ Saved {saved_count} articles to database")
            
            return {
                "items_found": len(articles),
                "items_new": saved_count,
                "items_filtered": len(articles) - len(filtered_articles),
                "items_duplicates": 0  # Already deduplicated
            }
        
        result = asyncio.run(run_aggregation())
        
        # Update job status
        if supabase_service.enabled and job_id:
            async def update_job():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            **result
                        }
                    )
            
            asyncio.run(update_job())
        
        logger.info(f"✅ News aggregation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ News aggregation failed: {e}", exc_info=True)
        
        # Update job as failed
        if job_id:
            async def mark_failed():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase_service.rest_url}/scraping_jobs",
                        headers=supabase_service.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "failed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            "error_message": str(e)
                        }
                    )
            
            asyncio.run(mark_failed())
        
        raise


@shared_task(name="cleanup_old_news")
def cleanup_old_news_task():
    """
    Run weekly to archive old news (>90 days)
    
    Marks news articles older than 90 days as archived
    """
    import asyncio
    from backend.services.supabase_sync import SupabaseSyncService
    
    logger.info("🗑️ Starting old news cleanup task...")
    
    try:
        supabase_service = SupabaseSyncService()
        
        async def run_cleanup():
            if not supabase_service.enabled:
                logger.warning("Supabase not enabled, skipping cleanup")
                return 0
            
            import httpx
            
            # Calculate cutoff date (90 days ago)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Update old articles to archived
                update_url = f"{supabase_service.rest_url}/news_articles"
                response = await client.patch(
                    update_url,
                    headers=supabase_service.headers,
                    params={
                        "published_at": f"lt.{cutoff_date.isoformat()}",
                        "is_archived": "eq.false"
                    },
                    json={
                        "is_archived": True,
                        "archived_at": datetime.now().isoformat()
                    }
                )
                
                # Note: Supabase doesn't return affected rows count by default
                logger.info(f"✅ Archived news articles older than {cutoff_date.date()}")
                return 0  # We don't have the count
        
        count = asyncio.run(run_cleanup())
        logger.info(f"✅ Cleanup completed")
        return {"archived_count": count}
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        raise
