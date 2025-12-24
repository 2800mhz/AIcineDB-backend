"""
Festival Scraper Service
Automatically scrapes film festivals from multiple sources with AI-powered filtering
"""
import os
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import httpx
import feedparser
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class FestivalScraper:
    """Scrapes film festivals from multiple sources"""
    
    def __init__(self):
        self.user_agent = os.getenv("SCRAPING_USER_AGENT", "AICineDB Bot/1.0")
        self.rate_limit_delay = float(os.getenv("SCRAPING_RATE_LIMIT_DELAY", "2"))
        self.max_retries = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
        
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    async def _fetch_with_retry(self, url: str, retry_count: int = 0) -> Optional[str]:
        """Fetch URL with retry logic"""
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                headers=self.headers,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            if retry_count < self.max_retries:
                logger.warning(f"Retry {retry_count + 1}/{self.max_retries} for {url}: {e}")
                await asyncio.sleep(self.rate_limit_delay * (retry_count + 1))
                return await self._fetch_with_retry(url, retry_count + 1)
            else:
                logger.error(f"Failed to fetch {url} after {self.max_retries} retries: {e}")
                return None
    
    async def scrape_filmfreeway(self) -> List[Dict]:
        """
        Scrape festivals from FilmFreeway
        
        Note: FilmFreeway requires authentication and has anti-scraping measures.
        This is a simplified implementation that would need to be enhanced
        with proper authentication and handling of dynamic content.
        """
        logger.info("🎬 Scraping FilmFreeway...")
        festivals = []
        
        try:
            # FilmFreeway's public festival list
            # In production, this would need proper authentication and pagination
            base_url = "https://filmfreeway.com/festivals"
            
            html = await self._fetch_with_retry(base_url)
            if not html:
                return festivals
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # This is a placeholder - actual selectors would need to be updated
            # based on FilmFreeway's current HTML structure
            festival_cards = soup.find_all('div', class_='festival-card')
            
            for card in festival_cards[:20]:  # Limit to 20 for now
                try:
                    festival = self._parse_filmfreeway_card(card)
                    if festival:
                        festivals.append(festival)
                except Exception as e:
                    logger.warning(f"Failed to parse FilmFreeway card: {e}")
                    continue
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"✓ Found {len(festivals)} festivals from FilmFreeway")
            
        except Exception as e:
            logger.error(f"❌ FilmFreeway scraping failed: {e}")
        
        return festivals
    
    def _parse_filmfreeway_card(self, card) -> Optional[Dict]:
        """Parse a FilmFreeway festival card"""
        try:
            # This is a placeholder implementation
            # Actual selectors need to be updated based on FilmFreeway's HTML
            name_elem = card.find('h3') or card.find('a', class_='festival-name')
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            url = name_elem.get('href', '')
            if url and not url.startswith('http'):
                url = f"https://filmfreeway.com{url}"
            
            description_elem = card.find('p', class_='description')
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            location_elem = card.find('span', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Extract country from location
            country = location.split(',')[-1].strip() if ',' in location else ""
            
            return {
                "name": name,
                "external_url": url,
                "description": description,
                "location": location,
                "country": country,
                "source": "filmfreeway",
                "source_url": url,
                "category": [],
                "genres": [],
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse card: {e}")
            return None
    
    async def scrape_withoutabox(self) -> List[Dict]:
        """
        Scrape festivals from Withoutabox (now part of IMDbPro)
        
        Note: Withoutabox has been integrated into IMDbPro and requires authentication.
        This is a placeholder for potential future implementation.
        """
        logger.info("🎬 Scraping Withoutabox...")
        logger.warning("⚠️ Withoutabox scraping not fully implemented (requires IMDbPro auth)")
        return []
    
    async def scrape_festhome(self) -> List[Dict]:
        """Scrape festivals from Festhome"""
        logger.info("🎬 Scraping Festhome...")
        festivals = []
        
        try:
            base_url = "https://festhome.com/en/festivals"
            
            html = await self._fetch_with_retry(base_url)
            if not html:
                return festivals
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Placeholder selectors - need to be updated based on actual HTML
            festival_items = soup.find_all('div', class_='festival-item')
            
            for item in festival_items[:20]:  # Limit to 20
                try:
                    festival = self._parse_festhome_item(item)
                    if festival:
                        festivals.append(festival)
                except Exception as e:
                    logger.warning(f"Failed to parse Festhome item: {e}")
                    continue
                
                await asyncio.sleep(self.rate_limit_delay)
            
            logger.info(f"✓ Found {len(festivals)} festivals from Festhome")
            
        except Exception as e:
            logger.error(f"❌ Festhome scraping failed: {e}")
        
        return festivals
    
    def _parse_festhome_item(self, item) -> Optional[Dict]:
        """Parse a Festhome festival item"""
        try:
            name_elem = item.find('h3') or item.find('a', class_='festival-title')
            if not name_elem:
                return None
            
            name = name_elem.get_text(strip=True)
            url = name_elem.get('href', '')
            if url and not url.startswith('http'):
                url = f"https://festhome.com{url}"
            
            description_elem = item.find('div', class_='description')
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            location_elem = item.find('span', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            country = location.split(',')[-1].strip() if ',' in location else ""
            
            # Extract deadline if available
            deadline_elem = item.find('span', class_='deadline')
            deadline = None
            if deadline_elem:
                deadline_text = deadline_elem.get_text(strip=True)
                # Try to parse date (simplified)
                try:
                    deadline = datetime.strptime(deadline_text, "%d %b %Y").isoformat()
                except:
                    pass
            
            return {
                "name": name,
                "external_url": url,
                "description": description,
                "location": location,
                "country": country,
                "submission_deadline": deadline,
                "source": "festhome",
                "source_url": url,
                "category": [],
                "genres": [],
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse item: {e}")
            return None
    
    async def scrape_rss_feed(self, url: str) -> List[Dict]:
        """
        Scrape festivals from an RSS feed
        
        Args:
            url: RSS feed URL
            
        Returns:
            List of festival dictionaries
        """
        logger.info(f"🎬 Scraping RSS feed: {url}")
        festivals = []
        
        try:
            # Fetch feed content
            html = await self._fetch_with_retry(url)
            if not html:
                return festivals
            
            # Parse with feedparser
            feed = feedparser.parse(html)
            
            for entry in feed.entries[:20]:  # Limit to 20
                try:
                    festival = {
                        "name": entry.get('title', 'Untitled Festival'),
                        "external_url": entry.get('link', ''),
                        "description": entry.get('summary', '') or entry.get('description', ''),
                        "source": "rss",
                        "source_url": url,
                        "category": [],
                        "genres": [],
                    }
                    
                    # Try to extract published date
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                        festival["submission_deadline"] = published.isoformat()
                    
                    festivals.append(festival)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse RSS entry: {e}")
                    continue
            
            logger.info(f"✓ Found {len(festivals)} festivals from RSS feed")
            
        except Exception as e:
            logger.error(f"❌ RSS feed scraping failed: {e}")
        
        return festivals
    
    async def scrape_all_sources(self) -> List[Dict]:
        """
        Scrape all configured sources concurrently
        
        Returns:
            Combined list of festivals from all sources
        """
        logger.info("🎬 Starting festival scraping from all sources...")
        
        # Run all scrapers concurrently
        results = await asyncio.gather(
            self.scrape_filmfreeway(),
            self.scrape_festhome(),
            self.scrape_withoutabox(),
            return_exceptions=True
        )
        
        # Combine results
        all_festivals = []
        for result in results:
            if isinstance(result, list):
                all_festivals.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Scraper failed: {result}")
        
        logger.info(f"✅ Total festivals found: {len(all_festivals)}")
        return all_festivals


# Convenience function
async def scrape_festivals() -> List[Dict]:
    """Convenience function to scrape festivals from all sources"""
    scraper = FestivalScraper()
    return await scraper.scrape_all_sources()


if __name__ == "__main__":
    # Test the scraper
    async def test():
        festivals = await scrape_festivals()
        print(f"\n✅ Found {len(festivals)} festivals")
        if festivals:
            print(f"\nFirst festival: {festivals[0]}")
    
    asyncio.run(test())
