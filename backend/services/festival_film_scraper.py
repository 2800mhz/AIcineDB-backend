"""
Festival Film Scraper Service
Scrapes films from festival websites (like AIFF, etc.)
Extracts YouTube embeds and film metadata
"""
import logging
import re
import asyncio
from typing import List, Dict, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Install with: pip install playwright && playwright install")


class FestivalFilmScraper:
    """Scrape films from festival showcase websites"""
    
    def __init__(self):
        self.timeout = 30000  # 30 seconds
        logger.info("🎬 FestivalFilmScraper initialized")
    
    async def scrape_festival_films(self, festival_url: str) -> List[Dict]:
        """
        Scrape films from a festival website
        
        Args:
            festival_url: URL of the festival showcase page
        
        Returns:
            List of film dictionaries with structure:
            {
                "title": "Film Title",
                "director": "Director Name",
                "youtube_url": "https://youtube.com/...",
                "category": "Grand Prix | Gold | Silver | Merit | Honoree",
                "description": "Film description",
                "duration": "5:30",
                "festival_source_url": "https://aiff.runwayml.com/2024"
            }
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed. Run: pip install playwright && playwright install")
        
        logger.info(f"🎬 Starting festival scraping: {festival_url}")
        
        # Detect festival type and use appropriate scraper
        if "aiff.runwayml.com" in festival_url or "runwayml.com" in festival_url:
            films = await self._scrape_aiff(festival_url)
        else:
            films = await self._scrape_generic(festival_url)
        
        logger.info(f"✅ Scraped {len(films)} films from {festival_url}")
        return films
    
    async def _scrape_aiff(self, url: str) -> List[Dict]:
        """
        Specific scraper for Runway AIFF (aiff.runwayml.com)
        Uses Playwright to handle JavaScript-rendered content
        """
        logger.info(f"🎯 Using AIFF-specific scraper for: {url}")
        
        films = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                # Navigate to page
                logger.info(f"📄 Loading page: {url}")
                await page.goto(url, wait_until='networkidle', timeout=self.timeout)
                
                # Wait for content to load
                await page.wait_for_timeout(3000)  # Wait 3 seconds for JS to render
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all YouTube iframes
                iframes = soup.find_all('iframe', src=re.compile(r'youtube\.com/embed/'))
                logger.info(f"📹 Found {len(iframes)} YouTube embeds")
                
                # Extract film data from each iframe
                for iframe in iframes:
                    try:
                        film_data = await self._extract_aiff_film_data(iframe, soup, url)
                        if film_data and film_data.get('youtube_url'):
                            films.append(film_data)
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to extract film data: {e}")
                        continue
                
            except PlaywrightTimeoutError:
                logger.error(f"❌ Timeout loading page: {url}")
            except Exception as e:
                logger.error(f"❌ Error scraping AIFF: {e}", exc_info=True)
            finally:
                await browser.close()
        
        return films
    
    async def _extract_aiff_film_data(self, iframe, soup: BeautifulSoup, source_url: str) -> Optional[Dict]:
        """Extract film metadata from AIFF page structure"""
        src = iframe.get('src', '')
        
        # Extract YouTube video ID
        youtube_url = self._extract_youtube_url(src)
        if not youtube_url:
            return None
        
        # Try to find film info near the iframe
        parent = iframe.find_parent(['div', 'section', 'article'])
        if not parent:
            parent = soup
        
        # Extract title
        title = None
        title_tags = parent.find_all(['h1', 'h2', 'h3', 'h4'], limit=5)
        for tag in title_tags:
            text = tag.get_text(strip=True)
            # Filter out category headers
            if text and not re.match(r'^(Grand Prix|Gold|Silver|Merit|Honoree)$', text, re.I):
                title = text
                break
        
        # Extract director
        director = None
        # Look for "by Director Name" or "Director: Name" patterns
        text_content = parent.get_text()
        director_match = re.search(r'(?:by|directed by|director:?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text_content, re.I)
        if director_match:
            director = director_match.group(1).strip()
        
        # Extract category (Grand Prix, Gold, Silver, Merit, Honoree)
        category = self._extract_category(parent, soup)
        
        # Extract description
        description = None
        desc_tags = parent.find_all('p', limit=3)
        for tag in desc_tags:
            text = tag.get_text(strip=True)
            if text and len(text) > 20:  # Meaningful description
                description = text
                break
        
        # Try to get duration from title or nearby text
        duration = self._extract_duration(parent.get_text())
        
        film_data = {
            "title": title or "Untitled",
            "director": director,
            "youtube_url": youtube_url,
            "category": category,
            "description": description,
            "duration": duration,
            "festival_source_url": source_url
        }
        
        logger.info(f"  ✅ Extracted: {film_data['title']} ({category or 'Unknown'})")
        return film_data
    
    def _extract_youtube_url(self, src: str) -> Optional[str]:
        """Extract and normalize YouTube URL from iframe src"""
        if not src:
            return None
        
        # Extract video ID from embed URL
        match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', src)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
    
    def _extract_category(self, parent, soup: BeautifulSoup) -> Optional[str]:
        """Extract award category from page structure"""
        # Categories we're looking for
        categories = ['Grand Prix', 'Gold', 'Silver', 'Merit', 'Honoree']
        
        # Look in parent and nearby elements
        text = parent.get_text()
        for category in categories:
            if re.search(rf'\b{category}\b', text, re.I):
                return category
        
        # Look for section headers above the film
        headers = soup.find_all(['h1', 'h2', 'h3'])
        for header in headers:
            header_text = header.get_text(strip=True)
            for category in categories:
                if category.lower() in header_text.lower():
                    return category
        
        return None
    
    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract video duration from text (e.g., '5:30', '2m 15s')"""
        # Pattern: 5:30 or 5m 30s or 5 min 30 sec
        patterns = [
            r'(\d{1,2}):(\d{2})',  # 5:30
            r'(\d{1,2})m\s*(\d{1,2})s',  # 5m 30s
            r'(\d{1,2})\s*min\s*(\d{1,2})\s*sec',  # 5 min 30 sec
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                minutes = int(match.group(1))
                # Check if second group exists and is not None
                seconds = int(match.group(2)) if match.lastindex >= 2 and match.group(2) else 0
                return f"{minutes}:{seconds:02d}"
        
        return None
    
    async def _scrape_generic(self, url: str) -> List[Dict]:
        """
        Generic scraper for other festival sites
        Looks for YouTube embeds and tries to extract metadata
        """
        logger.info(f"🌐 Using generic scraper for: {url}")
        
        films = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            try:
                logger.info(f"📄 Loading page: {url}")
                await page.goto(url, wait_until='networkidle', timeout=self.timeout)
                
                # Wait for content to load
                await page.wait_for_timeout(2000)
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all YouTube embeds (iframes)
                iframes = soup.find_all('iframe', src=re.compile(r'youtube\.com/embed/'))
                logger.info(f"📹 Found {len(iframes)} YouTube embeds")
                
                for iframe in iframes:
                    try:
                        youtube_url = self._extract_youtube_url(iframe.get('src', ''))
                        if not youtube_url:
                            continue
                        
                        # Try to find nearby metadata
                        parent = iframe.find_parent(['div', 'section', 'article'])
                        if not parent:
                            parent = soup
                        
                        # Extract title
                        title = None
                        title_tags = parent.find_all(['h1', 'h2', 'h3', 'h4'], limit=3)
                        for tag in title_tags:
                            text = tag.get_text(strip=True)
                            if text and len(text) > 3:
                                title = text
                                break
                        
                        # Extract description
                        description = None
                        desc_tags = parent.find_all('p', limit=2)
                        for tag in desc_tags:
                            text = tag.get_text(strip=True)
                            if text and len(text) > 20:
                                description = text
                                break
                        
                        film_data = {
                            "title": title or "Untitled",
                            "director": None,
                            "youtube_url": youtube_url,
                            "category": None,
                            "description": description,
                            "duration": None,
                            "festival_source_url": url
                        }
                        
                        films.append(film_data)
                        logger.info(f"  ✅ Extracted: {film_data['title']}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to extract film: {e}")
                        continue
                
            except PlaywrightTimeoutError:
                logger.error(f"❌ Timeout loading page: {url}")
            except Exception as e:
                logger.error(f"❌ Error scraping generic: {e}", exc_info=True)
            finally:
                await browser.close()
        
        return films


# Module-level function for convenience
async def scrape_festival_films(festival_url: str) -> List[Dict]:
    """
    Convenience function to scrape films from a festival URL
    
    Args:
        festival_url: URL of the festival showcase page
    
    Returns:
        List of film dictionaries
    """
    scraper = FestivalFilmScraper()
    return await scraper.scrape_festival_films(festival_url)
