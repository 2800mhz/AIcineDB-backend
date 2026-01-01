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
def scrape_festivals_task(self, source_id=None):
    """
    Festival scraping task.
    - source_id verilirse: Sadece o kaynağı çeker
    - source_id verilmezse: Tüm aktif kaynakları çeker
    """
    import asyncio
    import httpx
    from backend.services.festival_scraper import FestivalScraper
    from backend.services.supabase_sync import SupabaseSyncService
    
    target_name = f"Source {source_id}" if source_id else "ALL Sources"
    logger.info(f"🎬 Starting festival scraping... (Target: {target_name})")
    
    start_time = datetime.now()
    job_id = None
    supabase = SupabaseSyncService()
    
    try:
        async def run_scraping():
            nonlocal job_id
            sources_to_scrape = []
            
            if not supabase.enabled:
                logger.warning("⚠️ Supabase not enabled!")
                return {"items_found": 0, "status": "supabase_disabled"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Job kaydı oluştur
                job_payload = {
                    "job_type": "festivals",
                    "status": "running",
                    "started_at": start_time.isoformat()
                }
                if source_id:
                    job_payload["source_id"] = source_id
                
                job_resp = await client.post(
                    f"{supabase.rest_url}/scraping_jobs",
                    headers={**supabase.headers, "Prefer": "return=representation"},
                    json=job_payload
                )
                if job_resp.status_code in [200, 201]:
                    job_id = job_resp.json()[0].get('id')
                
                # 2. Kaynakları veritabanından al
                if source_id:
                    # Tek kaynak
                    src_resp = await client.get(
                        f"{supabase.rest_url}/festival_sources",
                        headers=supabase.headers,
                        params={"id": f"eq.{source_id}", "select": "id,name,source_type,url,is_active"}
                    )
                else:
                    # Tüm aktif kaynaklar
                    src_resp = await client.get(
                        f"{supabase.rest_url}/festival_sources",
                        headers=supabase.headers,
                        params={"is_active": "eq.true", "select": "id,name,source_type,url,is_active"}
                    )
                
                if src_resp.status_code == 200:
                    sources_to_scrape = src_resp.json()
                
                if not sources_to_scrape:
                    logger.warning("⚠️ No festival sources found in database!")
                    return {"items_found": 0, "items_new": 0, "status": "no_sources"}
                
                logger.info(f"📋 Found {len(sources_to_scrape)} sources to scrape")
                
                # 3. Her kaynağı sırayla çek
                scraper = FestivalScraper()
                all_festivals = []
                
                for source in sources_to_scrape:
                    src_id = source['id']
                    src_name = source['name']
                    src_type = source['source_type']
                    src_url = source.get('url')  # ✅ URL'yi de al
                    
                    logger.info(f"🔄 Scraping: {src_name} ({src_type})")
                    
                    try:
                        festivals = await scraper.scrape_by_source_type(src_type, src_id, src_url)
                        all_festivals.extend(festivals)
                        
                        # ✅ last_fetched_at güncelle
                        await client.patch(
                            f"{supabase.rest_url}/festival_sources",
                            headers=supabase.headers,
                            params={"id": f"eq.{src_id}"},
                            json={
                                "last_fetched_at": datetime.now().isoformat(),
                                "last_error": None
                            }
                        )
                        logger.info(f"✅ {src_name}: {len(festivals)} festivals")
                        
                    except Exception as e:
                        # Hata durumunda last_error güncelle
                        await client.patch(
                            f"{supabase.rest_url}/festival_sources",
                            headers=supabase.headers,
                            params={"id": f"eq.{src_id}"},
                            json={
                                "last_fetched_at": datetime.now().isoformat(),
                                "last_error": str(e)[:500]
                            }
                        )
                        logger.error(f"❌ {src_name} error: {e}")
                
                logger.info(f"📊 Total festivals found: {len(all_festivals)}")
                
                if not all_festivals:
                    return {
                        "items_found": 0,
                        "items_new": 0,
                        "items_updated": 0,
                        "items_duplicates": 0
                    }
                
                # 4. Veritabanına kaydet (UPSERT ile)
                saved_count = 0
                updated_count = 0
                
                for festival in all_festivals:
                    result = await supabase.sync_discovered_festival(festival)
                    if result:
                        saved_count += 1
                
                logger.info(f"✅ Saved/Updated: {saved_count} festivals")
                
                return {
                    "items_found": len(all_festivals),
                    "items_new": saved_count,
                    "items_updated": updated_count,
                    "items_duplicates": len(all_festivals) - saved_count
                }
        
        result = asyncio.run(run_scraping())
        
        # Job durumunu güncelle
        if supabase.enabled and job_id:
            async def update_job():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase.rest_url}/scraping_jobs",
                        headers=supabase.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            "items_found": result.get("items_found", 0),
                            "items_saved": result.get("items_new", 0),
                            "items_updated": result.get("items_updated", 0),
                            "items_skipped": result.get("items_duplicates", 0)
                        }
                    )
            asyncio.run(update_job())
        
        logger.info(f"✅ Festival scraping completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Festival scraping failed: {e}", exc_info=True)
        
        if job_id:
            async def mark_failed():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.patch(
                        f"{supabase.rest_url}/scraping_jobs",
                        headers=supabase.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "failed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            "error_message": str(e)[:500]
                        }
                    )
            asyncio.run(mark_failed())
        
        raise

@shared_task(name="aggregate_news", bind=True)
def aggregate_news_task(self, source_id=None):
    """
    Fetch news. 
    If source_id is provided, fetches ONLY that source (Manual Trigger).
    If no source_id, fetches ALL active sources from DB (Scheduled).
    """
    import asyncio
    import httpx
    from backend.services.news_aggregator import NewsAggregator
    from backend.services.supabase_sync import SupabaseSyncService
    
    target_name = f"Source {source_id}" if source_id else "ALL Active Sources"
    logger.info(f"📰 Starting news aggregation... (Target: {target_name})")
    
    start_time = datetime.now()
    job_id = None
    supabase = SupabaseSyncService()
    
    try:
        async def run_aggregation():
            nonlocal job_id
            sources_to_scrape = []
            
            # 1. Kaynakları Veritabanından Seç
            if supabase.enabled:
                async with httpx.AsyncClient() as client:
                    # Job kaydı oluştur
                    job_payload = {
                        "job_type": "news",
                        "status": "running",
                        "started_at": start_time.isoformat()
                    }
                    
                    if source_id:
                        job_payload["source_id"] = source_id
                    
                    # Job'ı başlat
                    job_resp = await client.post(
                        f"{supabase.rest_url}/scraping_jobs",
                        headers=supabase.headers,
                        json=job_payload
                    )
                    if job_resp.status_code in [200, 201]:
                        job_id = job_resp.json()[0].get('id')

                    # --- KAYNAK SEÇİMİ (KRİTİK BÖLÜM) ---
                    if source_id:
                        # DURUM A: Tek bir kaynağı çek (Butona basıldıysa)
                        logger.info(f"🎯 Fetching specific source ID: {source_id}")
                        src_resp = await client.get(
                            f"{supabase.rest_url}/news_sources",
                            headers=supabase.headers,
                            # ✅ type alanını da çekiyoruz ki Scraper mı RSS mi bilelim
                            params={"id": f"eq.{source_id}", "select": "name,url,id,source_type"}
                        )
                        if src_resp.status_code == 200:
                            sources_to_scrape = src_resp.json()
                    else:
                        # DURUM B: Tüm aktif kaynakları çek (Otomatik zamanlama)
                        logger.info("🔄 Fetching ALL active sources from DB")
                        src_resp = await client.get(
                            f"{supabase.rest_url}/news_sources",
                            headers=supabase.headers,
                            params={"is_active": "eq.true", "select": "name,url,id,source_type"}
                        )
                        if src_resp.status_code == 200:
                            sources_to_scrape = src_resp.json()

            # Kaynak bulunamadıysa işlem yapma
            if not sources_to_scrape:
                logger.warning("⚠️ No sources found in database to scrape!")
                return {"items_found": 0, "status": "no_sources"}

            logger.info(f"🚀 Processing {len(sources_to_scrape)} sources: {[s['name'] for s in sources_to_scrape]}")

            # 2. Aggregator'ı Başlat (Veritabanından gelen kaynak listesiyle)
            aggregator = NewsAggregator(sources=sources_to_scrape)
            articles = await aggregator.fetch_and_deduplicate()
            
            logger.info(f"📊 Found {len(articles)} relevant articles")
            
            # 3. Veritabanına Kaydet
            saved_count = 0
            for article in articles:
                # sync_news_article zaten akıllı etiketleme yapıyor
                res = await supabase.sync_news_article(article)
                if res: saved_count += 1
            
            logger.info(f"✅ Saved {saved_count} articles to database")
            
            return {
                "items_found": len(articles),
                "items_new": saved_count,
                "items_filtered": 0,
                "items_duplicates": len(articles) - saved_count
            }

        # Async fonksiyonu çalıştır
        result = asyncio.run(run_aggregation())
        
        # Job durumunu güncelle (Başarılı)
        if supabase.enabled and job_id:
            async def update_success():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{supabase.rest_url}/scraping_jobs",
                        headers=supabase.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "completed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            **result
                        }
                    )
            asyncio.run(update_success())
            
        return result

    except Exception as e:
        logger.error(f"❌ News aggregation failed: {e}", exc_info=True)
        # Job durumunu güncelle (Hata)
        if job_id:
            async def update_fail():
                import httpx
                duration = int((datetime.now() - start_time).total_seconds())
                async with httpx.AsyncClient() as client:
                    await client.patch(
                        f"{supabase.rest_url}/scraping_jobs",
                        headers=supabase.headers,
                        params={"id": f"eq.{job_id}"},
                        json={
                            "status": "failed",
                            "completed_at": datetime.now().isoformat(),
                            "duration_seconds": duration,
                            "error_message": str(e)
                        }
                    )
            asyncio.run(update_fail())
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
