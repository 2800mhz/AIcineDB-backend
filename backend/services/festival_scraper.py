"""
Festival Scraper Service - V8.0 IMPROVED
- Slug'dan akıllı isim çıkarma (CamelCase ayırma)
- Geliştirilmiş anti-bot bypass
- Daha iyi fotoğraf çekme
- Retry mekanizması iyileştirmesi
"""
import os
import asyncio
import logging
import re
import hashlib
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import random

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from curl_cffi.requests import AsyncSession
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False
    try:
        import httpx
        HTTPX_AVAILABLE = True
    except ImportError:
        HTTPX_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

MAJOR_FESTIVALS = {
    'cannes', 'sundance', 'berlin', 'berlinale', 'venice', 'toronto', 'tiff',
    'tribeca', 'sxsw', 'telluride', 'locarno', 'san sebastian', 'rotterdam',
    'karlovy vary', 'annecy', 'clermont-ferrand', 'busan', 'tokyo', 'hong kong',
    'shanghai', 'mar del plata', 'sitges', 'fantasia', 'raindance', 'bfi',
    'london film', 'new york film', 'los angeles film', 'chicago film',
    'austin film', 'seattle film', 'palm springs', 'hot docs', 'idfa',
    'sheffield doc', 'cphdox', 'docaviv', 'visions du réel'
}

BLACKLIST_SLUGS = {
    'sign_up', 'signup', 'login', 'signin', 'register',
    'help', 'about', 'pricing', 'contact', 'privacy', 'terms',
    'settings', 'profile', 'account', 'logout', 'password',
    'browse', 'search', 'festivals', 'projects', 'submit',
    'godigital', 'pro', 'gold', 'subscribe', 'upgrade',
    'blog', 'press', 'careers', 'jobs', 'faq', 'support',
    'api', 'developers', 'partners', 'advertise',
    'curated', 'trending', 'popular', 'featured',
    'deals', 'offers', 'promotions'
}

AI_FESTIVAL_INDICATORS = [
    'ai film', 'ai cinema', 'ai movie', 'a.i. film', 'a.i film',
    'artificial intelligence film', 'ai-generated', 'ai generated',
    'generative film', 'generative cinema', 'ai festival',
    'ai awards', 'ai short', 'ai feature', 'ai animation',
    'ai international', 'international ai', 'ai media',
    'ai art', 'ai creative', 'ai storytelling',
]

AI_FRIENDLY_CATEGORIES = [
    'experimental', 'animation', 'digital', 'new media',
    'avant-garde', 'avantgarde', 'vr', 'virtual reality',
    'mixed reality', 'xr', 'immersive', 'interactive',
    'web series', 'tech', 'technology', 'innovative',
    'emerging', 'hybrid', 'transmedia', 'cross-platform',
    'music video', 'motion graphics', 'visual effects', 'vfx',
    'cgi', '3d', 'motion capture', 'performance capture',
    'sci-fi', 'science fiction', 'futuristic'
]

AI_FRIENDLY_PHRASES = [
    'ai welcome', 'ai accepted', 'ai films accepted', 'ai films welcome',
    'accepts ai', 'including ai', 'ai-generated welcome',
    'all formats accepted', 'any format', 'all types of films',
    'experimental welcome', 'experimental films accepted',
    'new technologies', 'emerging technologies', 'innovative formats',
    'digital submissions welcome', 'animation accepted',
    'open to all genres', 'open to all formats',
    'no restrictions on format', 'format agnostic',
]

ONLINE_KEYWORDS = [
    'online', 'virtual', 'global', 'worldwide', 'international online',
    'remote', 'digital only', 'streaming', 'web-based', 'global / online'
]

KNOWN_LOCATIONS = {
    'CA': 'California, USA', 'NY': 'New York, USA', 'TX': 'Texas, USA',
    'FL': 'Florida, USA', 'IL': 'Illinois, USA', 'PA': 'Pennsylvania, USA',
    'OH': 'Ohio, USA', 'GA': 'Georgia, USA', 'NC': 'North Carolina, USA',
    'MI': 'Michigan, USA', 'NJ': 'New Jersey, USA', 'VA': 'Virginia, USA',
    'WA': 'Washington, USA', 'AZ': 'Arizona, USA', 'MA': 'Massachusetts, USA',
    'TN': 'Tennessee, USA', 'IN': 'Indiana, USA', 'MO': 'Missouri, USA',
    'MD': 'Maryland, USA', 'WI': 'Wisconsin, USA', 'CO': 'Colorado, USA',
    'MN': 'Minnesota, USA', 'SC': 'South Carolina, USA', 'AL': 'Alabama, USA',
    'LA': 'Louisiana, USA', 'KY': 'Kentucky, USA', 'OR': 'Oregon, USA',
    'OK': 'Oklahoma, USA', 'CT': 'Connecticut, USA', 'UT': 'Utah, USA',
    'NV': 'Nevada, USA', 'RI': 'Rhode Island, USA',
    'ON': 'Ontario, Canada', 'QC': 'Quebec, Canada', 'BC': 'British Columbia, Canada',
    'AB': 'Alberta, Canada', 'MB': 'Manitoba, Canada', 'SK': 'Saskatchewan, Canada',
    'USA': 'United States', 'US': 'United States', 'UK': 'United Kingdom',
    'GB': 'United Kingdom', 'DE': 'Germany', 'FR': 'France', 'IT': 'Italy',
    'ES': 'Spain', 'PT': 'Portugal', 'NL': 'Netherlands', 'BE': 'Belgium',
    'AT': 'Austria', 'CH': 'Switzerland', 'SE': 'Sweden', 'NO': 'Norway',
    'DK': 'Denmark', 'FI': 'Finland', 'PL': 'Poland', 'CZ': 'Czech Republic',
    'GR': 'Greece', 'TR': 'Turkey', 'RU': 'Russia', 'JP': 'Japan',
    'KR': 'South Korea', 'CN': 'China', 'TW': 'Taiwan', 'HK': 'Hong Kong',
    'AU': 'Australia', 'NZ': 'New Zealand', 'MX': 'Mexico',
    'BR': 'Brazil', 'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia',
    'IN': 'India', 'TH': 'Thailand', 'SG': 'Singapore', 'MY': 'Malaysia',
    'ID': 'Indonesia', 'PH': 'Philippines', 'VN': 'Vietnam',
    'EG': 'Egypt', 'ZA': 'South Africa', 'NG': 'Nigeria', 'KE': 'Kenya',
    'AE': 'UAE', 'IL': 'Israel', 'SA': 'Saudi Arabia',
}

INVALID_LOCATION_WORDS = {
    'film', 'festival', 'award', 'awards', 'cinema', 'movie', 'short', 'feature',
    'documentary', 'animation', 'music', 'video', 'international', 'global', 'online',
    'virtual', 'digital', 'ai', 'artificial', 'intelligence', 'new', 'media',
    'experimental', 'independent', 'indie', 'underground', 'avant-garde', 'art',
    'submission', 'deadline', 'entry', 'submit', 'call', 'entries', 'now', 'open',
    'closed', 'early', 'late', 'regular', 'extended', 'final', 'bird',
    'other', 'festivals', 'you', 'us', 'we', 'our', 'your', 'the', 'and', 'or',
    'for', 'with', 'from', 'about', 'more', 'info', 'information', 'details',
    'website', 'instagram', 'facebook', 'twitter', 'linkedin', 'youtube', 'vimeo',
    'telegram', 'group', 'channel', 'page', 'link', 'url', 'click', 'here',
    'best', 'top', 'first', 'world', 'premiere', 'official', 'selection',
    'winner', 'nominee', 'laurel', 'prize', 'grant', 'cash', 'money',
}

RSS_SOURCES = [
    {
        "name": "FilmFreeway Blog",
        "url": "https://filmfreeway.com/blog/feed",
        "type": "rss",
        "priority": 1
    },
    {
        "name": "Film Festival Today",
        "url": "https://filmfestivaltoday.com/feed/",
        "type": "rss",
        "priority": 2
    },
    {
        "name": "MovieMaker Magazine",
        "url": "https://www.moviemaker.com/feed/",
        "type": "rss",
        "priority": 3
    },
    {
        "name": "IndieWire",
        "url": "https://www.indiewire.com/feed/",
        "type": "rss",
        "priority": 4
    },
]

# Bilinen kısaltmalar - büyük harf kalması gerekenler
KNOWN_ACRONYMS = {
    'AI', 'VR', 'XR', 'AR', 'VFX', 'CGI', '3D', '2D', 
    'UK', 'USA', 'US', 'NYC', 'LA', 'SF', 'DC',
    'LGBTQ', 'LGBT', 'BIPOC', 'POC',
    'SCI', 'FI', 'DOC', 'DOCS',
    'HKUST', 'MIT', 'UCLA', 'USC', 'NYU',
    'IFF', 'IFFS', 'FF', 'MFF', 'NIFF', 'SIFF', 'BIFF', 'TIFF',
}


# ============================================================================
# HYBRID FESTIVAL SCRAPER V8.0
# ============================================================================

class HybridFestivalScraper:
    """
    Hibrit Festival Scraper - V8.0 IMPROVED
    
    Yenilikler:
    - Akıllı slug → isim dönüşümü (CamelCase, kısaltmalar)
    - Geliştirilmiş anti-bot bypass
    - Daha fazla impersonation seçeneği
    - Retry arası bekleme süreleri artırıldı
    """
    
    def __init__(self, cache_hours: int = 24):
        self.cache_hours = cache_hours
        self.rate_limit_delay = float(os.getenv("SCRAPING_RATE_LIMIT_DELAY", "2.0"))
        self.detail_delay = float(os.getenv("SCRAPING_DETAIL_DELAY", "1.5"))
        self.max_pages = int(os.getenv("SCRAPING_MAX_PAGES", "20"))
        self.fetch_details = os.getenv("SCRAPING_FETCH_DETAILS", "true").lower() == "true"
        self.timeout = 45.0  # Artırıldı
        
        self._cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Daha fazla impersonation seçeneği
        self.impersonations = [
            "chrome120", "chrome119", "chrome118", "chrome117", "chrome116",
            "safari17_0", "safari16_0", "safari15_5", "safari15_3",
            "edge120", "edge119", "edge101", "edge99",
            "firefox120", "firefox115",
        ]
        
        logger.info(f"🚀 Hybrid Festival Scraper V8.0 initialized (Cache: {cache_hours}h)")
    
    # ========================================================================
    # YENİ: AKILLI İSİM DÖNÜŞÜMÜ
    # ========================================================================
    
    def _slug_to_readable_name(self, slug: str) -> str:
        """
        URL slug'ını okunabilir festival ismine dönüştür
        
        Örnekler:
        - BerlinSciFiFilmfest → Berlin Sci-Fi Film Fest
        - AIinternationalFilmFestival → AI International Film Festival
        - HollywoodAIShortFilmAwards → Hollywood AI Short Film Awards
        - HKUST-AI-Film → HKUST AI Film
        - niff2026 → NIFF 2026
        """
        if not slug:
            return ''
        
        # 1. Tire ve alt çizgileri boşlukla değiştir
        name = slug.replace('-', ' ').replace('_', ' ')
        
        # 2. CamelCase'i ayır: BerlinSciFi → Berlin Sci Fi
        # Küçük harf + Büyük harf = boşluk ekle
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        
        # 3. Ardışık büyük harfleri ayır: AIFilm → AI Film, VFXAwards → VFX Awards
        # Birden fazla büyük harf + küçük harfle başlayan kelime
        name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
        
        # 4. Sayıları ayır: Festival2025 → Festival 2025, 3DAnimation → 3D Animation
        name = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', name)
        name = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', name)
        
        # 5. Çift boşlukları temizle
        name = re.sub(r'\s+', ' ', name).strip()
        
        # 6. Her kelimeyi işle
        words = name.split()
        result = []
        
        for word in words:
            upper_word = word.upper()
            
            # Bilinen kısaltma mı?
            if upper_word in KNOWN_ACRONYMS:
                result.append(upper_word)
            # Tamamen büyük harf ve 2-5 karakter arası (muhtemelen kısaltma)
            elif word.isupper() and 2 <= len(word) <= 5:
                result.append(word)
            # Sci-Fi gibi özel durumlar
            elif upper_word == 'SCIFI' or upper_word == 'SCI FI':
                result.append('Sci-Fi')
            # Normal kelime
            else:
                result.append(word.capitalize())
        
        final_name = ' '.join(result)
        
        # 7. Bazı düzeltmeler
        # "Film Fest" → düzgün bırak
        # "Filmfest" → "Film Fest" (eğer ayrılmamışsa)
        final_name = re.sub(r'\bFilmfest\b', 'Film Fest', final_name, flags=re.I)
        final_name = re.sub(r'\bFilmfestival\b', 'Film Festival', final_name, flags=re.I)
        final_name = re.sub(r'\bCinefest\b', 'Cine Fest', final_name, flags=re.I)
        
        # 8. Yıl varsa düzelt (2025, 2026 etc.)
        final_name = re.sub(r'\s*(20\d{2})\s*$', r' \1', final_name)
        
        return final_name.strip()
    
    # ========================================================================
    # PHASE 1: RSS DISCOVERY
    # ========================================================================
    
    async def discover_from_rss(self) -> List[Dict]:
        """RSS kaynaklarından festival keşfet"""
        if not FEEDPARSER_AVAILABLE:
            logger.warning("⚠️ feedparser not available, skipping RSS discovery")
            return []
        
        if not AIOHTTP_AVAILABLE:
            logger.warning("⚠️ aiohttp not available, skipping RSS discovery")
            return []
        
        all_festivals = []
        
        for source in RSS_SOURCES:
            try:
                logger.info(f"📡 RSS fetching: {source['name']}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        source['url'],
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        if response.status == 200:
                            content = await response.text()
                            feed = feedparser.parse(content)
                            
                            parsed_count = 0
                            for entry in feed.entries[:50]:
                                festival = self._parse_rss_entry(entry, source)
                                if festival:
                                    all_festivals.append(festival)
                                    parsed_count += 1
                            
                            logger.info(f"  ✅ {source['name']}: {parsed_count} festivals found")
                        else:
                            logger.warning(f"  ⚠️ {source['name']}: HTTP {response.status}")
                            
            except asyncio.TimeoutError:
                logger.warning(f"  ⚠️ {source['name']}: Timeout")
            except Exception as e:
                logger.warning(f"  ⚠️ {source['name']}: {str(e)[:50]}")
                continue
        
        logger.info(f"📡 RSS Discovery complete: {len(all_festivals)} festivals")
        return all_festivals
    
    def _parse_rss_entry(self, entry: Dict, source: Dict) -> Optional[Dict]:
        """RSS entry'sini festival formatına çevir"""
        try:
            link = entry.get('link', '')
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            
            if 'filmfreeway.com' in link:
                parsed = urlparse(link)
                path_parts = parsed.path.strip('/').split('/')
                
                if path_parts and len(path_parts[0]) > 2:
                    slug = path_parts[0]
                    
                    if slug.lower() not in BLACKLIST_SLUGS:
                        # Akıllı isim dönüşümü
                        name = title if title else self._slug_to_readable_name(slug)
                        
                        return {
                            "external_url": f"https://filmfreeway.com/{slug}",
                            "name": name,
                            "description": self._clean_html(summary)[:500] if summary else '',
                            "source": "rss",
                            "rss_source": source['name'],
                            "discovered_at": datetime.now().isoformat(),
                            "needs_detail_fetch": True,
                            "priority": source.get('priority', 5)
                        }
            
            return None
            
        except Exception as e:
            logger.debug(f"RSS parse error: {e}")
            return None
    
    def _clean_html(self, text: str) -> str:
        """HTML tag'lerini temizle"""
        if not text:
            return ''
        
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    # ========================================================================
    # PHASE 2: FILMFREEWAY LISTING DISCOVERY
    # ========================================================================
    
    async def discover_from_filmfreeway_listing(
        self,
        search_query: str = "ai",
        max_festivals: int = 100,
        call_for_entries: bool = True
    ) -> List[Dict]:
        """FilmFreeway liste sayfasından festival URL'leri çek"""
        
        base_url = "https://filmfreeway.com/festivals"
        params = {
            "q": search_query,
            "call_for_entries": "1" if call_for_entries else "0"
        }
        
        all_urls = []
        page = 1
        max_pages = min(self.max_pages, 10)
        
        logger.info(f"🔍 FilmFreeway listing: '{search_query}' (max {max_festivals})")
        
        while len(all_urls) < max_festivals and page <= max_pages:
            params['page'] = str(page)
            page_url = f"{base_url}?{urlencode(params)}"
            
            html = await self._fetch_url(page_url)
            if not html:
                logger.warning(f"  ⚠️ Page {page}: Failed to fetch")
                break
            
            urls = self._extract_festival_urls_from_listing(html)
            if not urls:
                logger.info(f"  ✅ Page {page}: No more results")
                break
            
            new_count = 0
            for url in urls:
                if url not in [x['external_url'] for x in all_urls]:
                    slug = urlparse(url).path.strip('/').split('/')[0]
                    # Akıllı isim dönüşümü kullan
                    name = self._slug_to_readable_name(slug)
                    
                    all_urls.append({
                        "external_url": url,
                        "name": name,
                        "source": "filmfreeway_listing",
                        "search_query": search_query,
                        "discovered_at": datetime.now().isoformat(),
                        "needs_detail_fetch": True
                    })
                    new_count += 1
            
            logger.info(f"  Page {page}: {new_count} new ({len(all_urls)} total)")
            
            if new_count == 0:
                break
            
            page += 1
            await asyncio.sleep(self.rate_limit_delay)
        
        logger.info(f"🔍 Listing complete: {len(all_urls)} festivals for '{search_query}'")
        return all_urls
    
    def _extract_festival_urls_from_listing(self, html: str) -> List[str]:
        """Liste HTML'inden festival URL'lerini çıkar"""
        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        seen_slugs = set()
        
        selectors = [
            'div.BrowseFestivals__item a',
            'div.SearchFestival a',
            'div.festival-card a',
            'a.BrowseFestivals__link',
            'div[data-festival-id] a',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if href:
                    url = self._normalize_festival_url(href)
                    if url:
                        slug = urlparse(url).path.strip('/').split('/')[0].lower()
                        if slug not in seen_slugs:
                            seen_slugs.add(slug)
                            urls.append(url)
        
        if not urls:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                url = self._normalize_festival_url(href)
                if url:
                    slug = urlparse(url).path.strip('/').split('/')[0].lower()
                    if slug not in seen_slugs:
                        seen_slugs.add(slug)
                        urls.append(url)
        
        return urls[:50]
    
    def _normalize_festival_url(self, href: str) -> Optional[str]:
        """Festival URL'ini normalize et ve validate et"""
        if not href:
            return None
        
        if href.startswith('/'):
            url = f"https://filmfreeway.com{href}"
        elif href.startswith('https://filmfreeway.com'):
            url = href
        elif href.startswith('http://filmfreeway.com'):
            url = href.replace('http://', 'https://')
        else:
            return None
        
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path or '/' in path:
            return None
        
        slug = path.split('?')[0].lower()
        
        if slug in BLACKLIST_SLUGS:
            return None
        
        if len(slug) < 3 or slug.isdigit():
            return None
        
        if any(slug.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.gif', '.svg', '.ico']):
            return None
        
        return f"https://filmfreeway.com/{path.split('?')[0]}"
    
    # ========================================================================
    # PHASE 3: DETAIL ENRICHMENT
    # ========================================================================
    
    async def enrich_festival_details(
        self,
        festivals: List[Dict],
        force_refresh: bool = False,
        max_concurrent: int = 3  # Azaltıldı - daha az agresif
    ) -> List[Dict]:
        """Festival listesini detaylarla zenginleştir"""
        
        enriched = []
        scrape_count = 0
        cache_count = 0
        skip_count = 0
        
        total = len(festivals)
        logger.info(f"🔬 Enriching {total} festivals...")
        
        for i, festival in enumerate(festivals, 1):
            url = festival.get('external_url', '')
            
            if not url:
                skip_count += 1
                continue
            
            if not force_refresh and self._is_cached(url):
                cached = self._get_cached(url)
                if cached:
                    enriched.append(cached)
                    cache_count += 1
                    continue
            
            try:
                detailed = await self._fetch_festival_details(festival)
                
                if detailed:
                    detailed = self._enrich_festival_data(detailed)
                    self._cache_festival(url, detailed)
                    enriched.append(detailed)
                    scrape_count += 1
                else:
                    # Detay çekilemese bile akıllı isim dönüşümü uygula
                    if festival.get('name'):
                        # İsim slug'dan mı geliyor kontrol et
                        slug = urlparse(url).path.strip('/').split('/')[0]
                        if festival['name'].lower().replace(' ', '') == slug.lower().replace('-', '').replace('_', ''):
                            festival['name'] = self._slug_to_readable_name(slug)
                    
                    basic = self._enrich_festival_data(festival)
                    enriched.append(basic)
                    skip_count += 1
                    
            except Exception as e:
                logger.debug(f"Enrich error for {url}: {e}")
                basic = self._enrich_festival_data(festival)
                enriched.append(basic)
                skip_count += 1
            
            if i % 10 == 0:
                logger.info(f"  Progress: {i}/{total} (Scraped: {scrape_count}, Cached: {cache_count}, Skipped: {skip_count})")
            
            # Daha uzun bekleme
            await asyncio.sleep(self.detail_delay + random.uniform(0.5, 1.5))
        
        logger.info(f"🔬 Enrichment complete: {len(enriched)} festivals")
        logger.info(f"  📊 Scraped: {scrape_count}, Cached: {cache_count}, Skipped: {skip_count}")
        
        return enriched
    
    async def _fetch_festival_details(self, festival: Dict) -> Optional[Dict]:
        """Festival detay sayfasından bilgileri çek"""
        url = festival.get('external_url', '')
        if not url:
            return festival
        
        html = await self._fetch_url(url)
        if not html:
            logger.debug(f"Failed to fetch: {url}")
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        if not self._is_valid_festival_page(soup):
            logger.debug(f"Not a valid festival page: {url}")
            return None
        
        result = festival.copy()
        
        # İsim çıkar
        name = self._extract_name(soup)
        if name:
            result['name'] = name
        elif result.get('name'):
            # Mevcut ismi akıllı dönüşümden geçir
            slug = urlparse(url).path.strip('/').split('/')[0]
            if result['name'].lower().replace(' ', '') == slug.lower().replace('-', '').replace('_', ''):
                result['name'] = self._slug_to_readable_name(slug)
        
        description = self._extract_description(soup)
        if description:
            result['description'] = description
        
        location_data = self._extract_location(soup, description or '')
        result['location'] = location_data.get('full', 'Global / Online')
        result['city'] = location_data.get('city', '')
        result['state'] = location_data.get('state', '')
        result['country'] = location_data.get('country', '')
        result['is_online'] = location_data.get('is_online', False)
        
        event_dates = self._extract_event_dates(soup)
        if event_dates:
            result['event_start_date'] = event_dates.get('start')
            result['event_end_date'] = event_dates.get('end')
            result['event_dates_raw'] = event_dates.get('raw', '')
        
        deadlines = self._extract_deadlines(soup)
        if deadlines:
            result['deadlines'] = deadlines
            next_dl = self._get_next_deadline(deadlines)
            if next_dl:
                result['submission_deadline'] = next_dl['date']
                result['deadline_type'] = next_dl.get('type', 'General')
                if next_dl.get('fee') is not None:
                    result['current_fee'] = next_dl['fee']
                
                dl_info = self._calculate_deadline_info(next_dl['date'])
                result['deadline_status'] = dl_info['status']
                result['deadline_days_left'] = dl_info['days_left']
                result['deadline_display'] = dl_info['display']
        
        entry_fee = self._extract_entry_fee(soup)
        if entry_fee:
            result['entry_fee'] = entry_fee
        
        categories = self._extract_categories(soup)
        if categories:
            result['category'] = categories
        
        awards = self._extract_awards(soup)
        if awards:
            result['awards'] = awards
        
        # Fotoğraf çekme - geliştirildi
        cover_photo = self._extract_cover_photo(soup)
        if cover_photo:
            result['logo_url'] = cover_photo
            result['cover_photo'] = cover_photo
            result['banner_url'] = cover_photo
        
        photos = self._extract_gallery_photos(soup)
        if photos:
            result['photos'] = photos
            # İlk fotoğrafı banner olarak da kullan (eğer cover yoksa)
            if not result.get('banner_url') and photos:
                result['banner_url'] = photos[0]
        
        website = self._extract_website(soup)
        if website:
            result['website'] = website
        
        years = self._extract_years_running(soup)
        if years:
            result['years_running'] = years
        
        social = self._extract_social_links(soup)
        if social:
            result['social_media'] = social
        
        result['needs_detail_fetch'] = False
        result['details_fetched_at'] = datetime.now().isoformat()
        
        return result
    
    def _is_valid_festival_page(self, soup: BeautifulSoup) -> bool:
        """Sayfanın gerçek bir festival sayfası olup olmadığını kontrol et"""
        positive_indicators = [
            soup.find(class_=lambda x: x and 'festival' in x.lower() if x else False),
            soup.find('meta', property='og:type', content=lambda x: x and 'festival' in str(x).lower() if x else False),
            soup.find(string=re.compile(r'submit|deadline|entry fee|call for entries', re.I)),
            soup.find('h1'),
        ]
        
        if any(positive_indicators):
            negative_indicators = [
                soup.find('form', id='new_user'),
                soup.find('input', attrs={'name': 'user[email]'}),
                soup.find(string=re.compile(r'^sign up$|^create account$|^register now$', re.I)),
            ]
            
            if any(negative_indicators):
                return False
            
            return True
        
        return False
    
    # ========================================================================
    # EXTRACTION METHODS
    # ========================================================================
    
    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Festival adını çıkar"""
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text(strip=True)
            name = re.sub(r'\s*[\|–-]\s*FilmFreeway.*$', '', name)
            name = re.sub(r'\s*\|\s*Film\s*Freeway.*$', '', name, flags=re.I)
            if name and len(name) > 2:
                return name
        
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            name = og_title.get('content')
            name = re.sub(r'\s*[\|–-]\s*FilmFreeway.*$', '', name)
            if name and len(name) > 2:
                return name
        
        title_tag = soup.find('title')
        if title_tag:
            name = title_tag.get_text(strip=True)
            name = re.sub(r'\s*[\|–-]\s*FilmFreeway.*$', '', name)
            if name and len(name) > 2:
                return name
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Açıklama çıkar"""
        desc_selectors = [
            'div.Festival__description',
            'div.festival-description',
            'div.about-section',
            'div[class*="description"]',
            'div[class*="about"]',
            'p.Festival__about',
            'section.Festival__about',
        ]
        
        for selector in desc_selectors:
            desc_el = soup.select_one(selector)
            if desc_el:
                text = desc_el.get_text(strip=True)
                if text and len(text) > 50:
                    return text[:2000]
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = meta_desc.get('content')
            if len(content) > 50:
                return content[:2000]
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            content = og_desc.get('content')
            if len(content) > 50:
                return content[:2000]
        
        return None
    
    def _extract_location(self, soup: BeautifulSoup, description: str = '') -> Dict:
        """Lokasyon çıkar"""
        result = {
            'full': 'Global / Online',
            'city': '',
            'state': '',
            'country': '',
            'is_online': True
        }
        
        page_text = soup.get_text().lower()[:5000]
        if description:
            page_text += ' ' + description.lower()
        
        online_indicators = [
            'online festival', 'virtual festival', 'global / online',
            'worldwide online', 'streaming festival', 'remote festival',
            'no physical location', 'entirely online', 'virtual event',
            'online only', 'digital festival', 'web-based festival',
            'submit from anywhere', 'global submission'
        ]
        
        for indicator in online_indicators:
            if indicator in page_text:
                return result
        
        location_schema = soup.find(itemprop='location')
        if location_schema:
            address = location_schema.find(itemprop='address')
            if address:
                city_el = address.find(itemprop='addressLocality')
                region_el = address.find(itemprop='addressRegion')
                country_el = address.find(itemprop='addressCountry')
                
                if city_el:
                    result['city'] = city_el.get_text(strip=True)
                if region_el:
                    result['state'] = region_el.get_text(strip=True)
                if country_el:
                    result['country'] = country_el.get_text(strip=True)
                
                if result['city'] or result['country']:
                    result['full'] = self._format_location(result)
                    result['is_online'] = False
                    return result
        
        loc_selectors = [
            'div.Festival__location',
            'span.Festival__location',
            'div[class="Festival__location"]',
            'span[class="Festival__location"]',
        ]
        
        for selector in loc_selectors:
            loc_el = soup.select_one(selector)
            if loc_el:
                loc_text = loc_el.get_text(strip=True)
                if loc_text and self._is_valid_location_text(loc_text):
                    parsed = self._parse_location_text(loc_text)
                    if parsed['full'] and parsed['full'] != 'Global / Online':
                        return parsed
        
        geo_placename = soup.find('meta', attrs={'name': 'geo.placename'})
        geo_region = soup.find('meta', attrs={'name': 'geo.region'})
        
        if geo_placename and geo_placename.get('content'):
            result['city'] = geo_placename.get('content')
            result['is_online'] = False
        
        if geo_region and geo_region.get('content'):
            region = geo_region.get('content')
            if '-' in region:
                parts = region.split('-')
                result['country'] = parts[0]
                result['state'] = parts[1] if len(parts) > 1 else ''
            else:
                result['country'] = region
            result['is_online'] = False
        
        if result['city'] or result['country']:
            result['full'] = self._format_location(result)
            return result
        
        address_el = soup.find('address')
        if address_el:
            text = address_el.get_text(strip=True)
            if self._is_valid_location_text(text):
                parsed = self._parse_location_text(text)
                if parsed['full'] and parsed['full'] != 'Global / Online':
                    return parsed
        
        return result
    
    def _is_valid_location_text(self, text: str) -> bool:
        """Metnin geçerli bir lokasyon olup olmadığını kontrol et"""
        if not text or len(text) < 2 or len(text) > 100:
            return False
        
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        if words:
            invalid_count = sum(1 for w in words if w in INVALID_LOCATION_WORDS)
            if invalid_count == len(words):
                return False
        
        if len(re.findall(r'\d', text)) > 8:
            return False
        
        return True
    
    def _parse_location_text(self, text: str) -> Dict:
        """Lokasyon metnini parse et"""
        result = {
            'full': '',
            'city': '',
            'state': '',
            'country': '',
            'is_online': False
        }
        
        if not text:
            result['full'] = 'Global / Online'
            result['is_online'] = True
            return result
        
        text = text.strip()
        
        if any(kw in text.lower() for kw in ONLINE_KEYWORDS):
            result['full'] = 'Global / Online'
            result['is_online'] = True
            return result
        
        if ',' in text:
            parts = [p.strip() for p in text.split(',')]
            
            if len(parts) >= 3:
                result['city'] = parts[0]
                result['state'] = parts[1]
                result['country'] = parts[2]
            elif len(parts) == 2:
                result['city'] = parts[0]
                second = parts[1].strip().upper()
                
                if second in KNOWN_LOCATIONS:
                    expanded = KNOWN_LOCATIONS[second]
                    if 'USA' in expanded or 'United States' in expanded:
                        result['state'] = second
                        result['country'] = 'USA'
                    elif 'Canada' in expanded:
                        result['state'] = second
                        result['country'] = 'Canada'
                    else:
                        result['country'] = expanded
                else:
                    result['country'] = parts[1].strip()
        else:
            upper_text = text.upper()
            if upper_text in KNOWN_LOCATIONS:
                result['country'] = KNOWN_LOCATIONS[upper_text]
            else:
                result['city'] = text
        
        result['full'] = self._format_location(result)
        
        if not result['full'] or result['full'] == ', ':
            result['full'] = 'Global / Online'
            result['is_online'] = True
        
        return result
    
    def _format_location(self, loc: Dict) -> str:
        """Lokasyonu formatlı string olarak döndür"""
        parts = []
        
        if loc.get('city'):
            parts.append(loc['city'])
        if loc.get('state'):
            parts.append(loc['state'])
        if loc.get('country'):
            parts.append(loc['country'])
        
        if not parts:
            return 'Global / Online'
        
        return ', '.join(parts)
    
    def _extract_event_dates(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Event tarihlerini çıkar"""
        date_selectors = [
            'div.Festival__dates',
            'div.event-dates',
            'span.dates',
            'div[class*="event-date"]',
            'div[class*="festival-date"]',
            'time[itemprop="startDate"]',
            'time[itemprop="endDate"]',
        ]
        
        for selector in date_selectors:
            date_el = soup.select_one(selector)
            if date_el:
                if date_el.get('datetime'):
                    dt = date_el.get('datetime')[:10]
                    return {
                        'start': dt,
                        'end': dt,
                        'raw': date_el.get_text(strip=True)
                    }
                
                text = date_el.get_text(strip=True)
                parsed = self._parse_event_date_range(text)
                if parsed:
                    parsed['raw'] = text
                    return parsed
        
        return None
    
    def _parse_event_date_range(self, text: str) -> Optional[Dict]:
        """Tarih aralığını parse et"""
        match = re.search(
            r'([A-Z][a-z]+)\s+(\d{1,2})\s*[-–—]\s*([A-Z][a-z]+)\s+(\d{1,2}),?\s*(\d{4})',
            text
        )
        if match:
            try:
                year = match.group(5)
                start = datetime.strptime(f"{match.group(1)} {match.group(2)} {year}", "%B %d %Y")
                end = datetime.strptime(f"{match.group(3)} {match.group(4)} {year}", "%B %d %Y")
                return {
                    'start': start.strftime('%Y-%m-%d'),
                    'end': end.strftime('%Y-%m-%d')
                }
            except:
                pass
        
        match = re.search(
            r'([A-Z][a-z]+)\s+(\d{1,2})\s*[-–—]\s*(\d{1,2}),?\s*(\d{4})',
            text
        )
        if match:
            try:
                month = match.group(1)
                year = match.group(4)
                start = datetime.strptime(f"{month} {match.group(2)} {year}", "%B %d %Y")
                end = datetime.strptime(f"{month} {match.group(3)} {year}", "%B %d %Y")
                return {
                    'start': start.strftime('%Y-%m-%d'),
                    'end': end.strftime('%Y-%m-%d')
                }
            except:
                pass
        
        return None
    
    def _extract_deadlines(self, soup: BeautifulSoup) -> List[Dict]:
        """Tüm deadline'ları çıkar"""
        deadlines = []
        
        deadline_selectors = [
            'div.Festival__deadlines',
            'div.Deadlines',
            'div.deadlines',
            'table.deadlines',
            'ul.deadlines',
            'div[class*="deadline"]',
            'div.SubmissionDeadlines',
            'section.deadlines',
        ]
        
        for selector in deadline_selectors:
            containers = soup.select(selector)
            for container in containers:
                rows = container.find_all(['tr', 'li', 'div'], recursive=False)
                if not rows:
                    rows = container.find_all(['tr', 'li', 'div'])
                
                for row in rows:
                    deadline = self._parse_deadline_row(row)
                    if deadline:
                        deadlines.append(deadline)
        
        seen = set()
        unique_deadlines = []
        for d in deadlines:
            key = f"{d.get('type', '')}_{d.get('date', '')}"
            if key not in seen:
                seen.add(key)
                unique_deadlines.append(d)
        
        return unique_deadlines
    
    def _parse_deadline_row(self, row) -> Optional[Dict]:
        """Tek bir deadline satırını parse et"""
        text = row.get_text(strip=True)
        if not text or len(text) < 5:
            return None
        
        deadline_type = 'General'
        type_patterns = [
            (r'Super\s*Early', 'Super Early'),
            (r'Early\s*Bird', 'Early Bird'),
            (r'Early', 'Early'),
            (r'Regular', 'Regular'),
            (r'Late', 'Late'),
            (r'Extended', 'Extended'),
            (r'Final', 'Final'),
            (r'Standard', 'Standard'),
        ]
        
        for pattern, name in type_patterns:
            if re.search(pattern, text, re.I):
                deadline_type = name
                break
        
        date_str = self._parse_date(text)
        if not date_str:
            return None
        
        fee = None
        fee_match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
        if fee_match:
            fee = float(fee_match.group(1))
        elif re.search(r'\bfree\b', text, re.I):
            fee = 0.0
        
        return {
            'type': deadline_type,
            'date': date_str,
            'fee': fee,
            'raw': text[:150]
        }
    
    def _get_next_deadline(self, deadlines: List[Dict]) -> Optional[Dict]:
        """En yakın gelecekteki deadline'ı bul"""
        now = datetime.now()
        future_deadlines = []
        
        for d in deadlines:
            date_str = d.get('date', '')
            if date_str:
                try:
                    if 'T' in date_str:
                        dt = datetime.fromisoformat(date_str.split('T')[0])
                    else:
                        dt = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if dt >= now:
                        future_deadlines.append({**d, 'parsed_date': dt})
                except:
                    pass
        
        if future_deadlines:
            future_deadlines.sort(key=lambda x: x['parsed_date'])
            result = future_deadlines[0].copy()
            del result['parsed_date']
            return result
        
        return deadlines[0] if deadlines else None
    
    def _parse_date(self, text: str) -> Optional[str]:
        """Tarih metnini ISO formatına çevir"""
        if not text:
            return None
        
        patterns = [
            (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
            (r'([A-Z][a-z]+)\s+(\d{1,2}),?\s+(\d{4})', '%B %d %Y'),
            (r'([A-Z][a-z]{2})\s+(\d{1,2}),?\s+(\d{4})', '%b %d %Y'),
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
            (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%d-%m-%Y'),
            (r'(\d{1,2})\s+([A-Z][a-z]+)\s+(\d{4})', '%d %B %Y'),
            (r'(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})', '%d %b %Y'),
        ]
        
        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = match.group(0).replace(',', '')
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        
        return None
    
    def _calculate_deadline_info(self, deadline_str: str) -> Dict:
        """Deadline bilgisini hesapla"""
        result = {
            'status': 'unknown',
            'days_left': None,
            'display': 'TBA'
        }
        
        if not deadline_str:
            return result
        
        try:
            if 'T' in deadline_str:
                deadline = datetime.fromisoformat(deadline_str.split('T')[0])
            else:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
            
            now = datetime.now()
            days_left = (deadline - now).days
            
            result['days_left'] = days_left
            
            if days_left < 0:
                result['status'] = 'closed'
                result['display'] = 'Closed'
            elif days_left == 0:
                result['status'] = 'closing_soon'
                result['display'] = 'Today!'
            elif days_left == 1:
                result['status'] = 'closing_soon'
                result['display'] = '1 Day'
            elif days_left <= 7:
                result['status'] = 'closing_soon'
                result['display'] = f'{days_left} Days'
            elif days_left <= 30:
                result['status'] = 'open'
                result['display'] = f'{days_left} Days'
            else:
                result['status'] = 'open'
                result['display'] = f'{days_left} Days'
            
            return result
            
        except Exception as e:
            logger.debug(f"Deadline parse error: {e}")
            return result
    
    def _extract_entry_fee(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Entry fee'yi parse et"""
        fee_selectors = [
            'div.Festival__fees',
            'div.entry-fee',
            'span.fee',
            'div[class*="fee"]',
            'div.SubmissionFees',
        ]
        
        for selector in fee_selectors:
            fee_el = soup.select_one(selector)
            if fee_el:
                text = fee_el.get_text(strip=True)
                return self._parse_fee(text)
        
        return None
    
    def _parse_fee(self, text: str) -> Optional[Dict]:
        """Entry fee'yi parse et"""
        if 'free' in text.lower() or 'no fee' in text.lower():
            return {'min': 0, 'max': 0, 'currency': 'USD', 'is_free': True}
        
        usd_prices = re.findall(r'\$(\d+(?:\.\d{2})?)', text)
        if usd_prices:
            prices = [float(p) for p in usd_prices]
            return {
                'min': min(prices),
                'max': max(prices),
                'currency': 'USD',
                'is_free': min(prices) == 0
            }
        
        return None
    
    def _extract_categories(self, soup: BeautifulSoup) -> List[str]:
        """Kabul edilen kategorileri çıkar"""
        categories = []
        
        cat_selectors = [
            'div.Festival__categories',
            'div.categories',
            'ul.categories',
            'div.project-types',
            'div.AcceptedCategories',
            'div[class*="categor"]',
        ]
        
        for selector in cat_selectors:
            container = soup.select_one(selector)
            if container:
                items = container.find_all(['li', 'span', 'a', 'div'])
                for item in items:
                    cat = item.get_text(strip=True)
                    if cat and len(cat) > 2 and len(cat) < 100 and cat not in categories:
                        categories.append(cat)
        
        return categories[:20]
    
    def _extract_awards(self, soup: BeautifulSoup) -> List[Dict]:
        """Ödülleri çıkar"""
        awards = []
        
        award_selectors = [
            'div.Festival__awards',
            'div.awards',
            'ul.awards',
            'div.prizes',
            'div[class*="award"]',
            'div[class*="prize"]',
        ]
        
        for selector in award_selectors:
            container = soup.select_one(selector)
            if container:
                items = container.find_all(['li', 'div', 'p'])
                for item in items:
                    text = item.get_text(strip=True)
                    if text and len(text) > 3:
                        money_match = re.search(r'[\$€£][\d,]+', text)
                        awards.append({
                            'name': text[:200],
                            'cash_prize': money_match.group(0) if money_match else None
                        })
        
        return awards[:15]
    
    def _extract_cover_photo(self, soup: BeautifulSoup) -> Optional[str]:
        """Cover photo URL'ini çıkar - GELİŞTİRİLDİ"""
        
        # 1. Open Graph image (en güvenilir)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = og_image.get('content')
            if url and self._is_valid_image_url(url):
                logger.debug(f"Found og:image: {url[:50]}...")
                return url
        
        # 2. Twitter image
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter_image and twitter_image.get('content'):
            url = twitter_image.get('content')
            if url and self._is_valid_image_url(url):
                return url
        
        # 3. FilmFreeway specific selectors
        ff_selectors = [
            'div.Festival__cover img',
            'div.Festival__header img',
            'div.Festival__banner img',
            'div.FestivalHeader__cover img',
            'div.FestivalHeader__banner img',
            'img.Festival__coverImage',
            'img.FestivalHeader__image',
            'div[class*="cover"] img',
            'div[class*="banner"] img',
            'div[class*="header"] img',
            'div[class*="hero"] img',
            'header img',
        ]
        
        for selector in ff_selectors:
            img = soup.select_one(selector)
            if img:
                src = self._get_best_image_src(img)
                if src and self._is_valid_image_url(src):
                    url = self._normalize_image_url(src)
                    if url:
                        logger.debug(f"Found cover from selector '{selector}': {url[:50]}...")
                        return url
        
        # 4. Background image from style
        for div in soup.find_all('div', class_=re.compile(r'cover|banner|hero|header|background', re.I)):
            style = div.get('style', '')
            match = re.search(r'background(?:-image)?:\s*url\(["\']?(.*?)["\']?\)', style)
            if match:
                url = match.group(1)
                if self._is_valid_image_url(url):
                    url = self._normalize_image_url(url)
                    if url:
                        return url
        
        # 5. data-background attribute
        for div in soup.find_all(['div', 'section', 'header'], attrs={'data-background': True}):
            url = div.get('data-background')
            if url and self._is_valid_image_url(url):
                return self._normalize_image_url(url)
        
        # 6. data-src attribute (lazy loading)
        for div in soup.find_all(['div', 'section', 'header'], attrs={'data-src': True}):
            url = div.get('data-src')
            if url and self._is_valid_image_url(url):
                return self._normalize_image_url(url)
        
        # 7. En büyük resmi bul (son çare)
        largest_img = None
        largest_size = 0
        
        for img in soup.find_all('img'):
            src = self._get_best_image_src(img)
            if src and self._is_valid_image_url(src):
                # Boyut bilgisi varsa kullan
                width = img.get('width', '0')
                height = img.get('height', '0')
                try:
                    w = int(re.sub(r'\D', '', str(width)) or 0)
                    h = int(re.sub(r'\D', '', str(height)) or 0)
                    size = w * h
                    if size > largest_size:
                        largest_size = size
                        largest_img = src
                except:
                    pass
        
        if largest_img:
            return self._normalize_image_url(largest_img)
        
        return None
    
    def _extract_gallery_photos(self, soup: BeautifulSoup) -> List[str]:
        """Galeri fotoğraflarını çıkar"""
        photos = []
        seen = set()
        
        # og:image'ı ilk ekle
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            url = og_image.get('content')
            if url and self._is_valid_image_url(url):
                photos.append(url)
                seen.add(url)
        
        gallery_selectors = [
            'div.Festival__gallery',
            'div.Festival__media',
            'div.Festival__photos',
            'div.gallery',
            'div.photos',
            'div.media-gallery',
            'div[class*="gallery"]',
            'div[class*="carousel"]',
            'div[class*="slider"]',
            'section.Festival__photos',
        ]
        
        for selector in gallery_selectors:
            containers = soup.select(selector)
            for container in containers:
                for img in container.find_all('img'):
                    src = self._get_best_image_src(img)
                    if src:
                        url = self._normalize_image_url(src)
                        if url and self._is_valid_image_url(url) and url not in seen:
                            photos.append(url)
                            seen.add(url)
        
        # FilmFreeway CDN resimlerini ara
        for img in soup.find_all('img'):
            src = self._get_best_image_src(img)
            if src:
                # FilmFreeway CDN veya S3 URL'leri
                if any(domain in src.lower() for domain in ['filmfreeway', 'amazonaws', 'cloudfront']):
                    url = self._normalize_image_url(src)
                    if url and self._is_valid_image_url(url) and url not in seen:
                        photos.append(url)
                        seen.add(url)
        
        return photos[:10]
    
    def _get_best_image_src(self, img) -> Optional[str]:
        """Bir img elementinden en iyi src'yi al"""
        # Öncelik sırası: data-src > srcset > src
        src = (
            img.get('data-src') or
            img.get('data-lazy-src') or
            img.get('data-original') or
            img.get('data-full-src') or
            self._get_srcset_best_url(img.get('srcset')) or
            img.get('src')
        )
        return src
    
    def _get_srcset_best_url(self, srcset: str) -> Optional[str]:
        """srcset'ten en büyük boyutlu URL'i çıkar"""
        if not srcset:
            return None
        
        parts = srcset.split(',')
        best_url = None
        best_size = 0
        
        for part in parts:
            part = part.strip()
            match = re.match(r'(\S+)\s+(\d+)(?:w|x)', part)
            if match:
                url = match.group(1)
                size = int(match.group(2))
                if size > best_size:
                    best_size = size
                    best_url = url
            elif not best_url:
                best_url = part.split()[0] if part else None
        
        return best_url
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Resim URL'inin geçerli olup olmadığını kontrol et"""
        if not url:
            return False
        
        if url.startswith('data:'):
            return False
        
        # Geçersiz pattern'ler
        invalid_patterns = [
            'placeholder', 'icon', 'sprite', 'avatar', 'logo-small',
            '1x1', 'pixel', 'tracking', 'blank', 'empty',
            'spacer', 'loading', 'default', 'null',
            'transparent', 'clear', 'dot.gif', 'dot.png',
            'facebook.com', 'twitter.com', 'instagram.com',  # Sosyal medya ikonları
            'google.com/recaptcha', 'googletagmanager',
        ]
        
        url_lower = url.lower()
        for pattern in invalid_patterns:
            if pattern in url_lower:
                return False
        
        # Çok küçük resimler
        if re.search(r'/\d{1,2}x\d{1,2}[/\.]', url):
            return False
        
        # Geçerli uzantı kontrolü
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']
        has_valid_ext = any(ext in url_lower for ext in valid_extensions)
        
        # CDN URL'leri genellikle uzantısız olabilir
        is_cdn = any(cdn in url_lower for cdn in ['cloudfront', 'amazonaws', 'filmfreeway', 'cdn'])
        
        return has_valid_ext or is_cdn
    
    def _normalize_image_url(self, src: str) -> Optional[str]:
        """Image URL'ini normalize et"""
        if not src:
            return None
        
        if src.startswith('data:'):
            return None
        
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = 'https://filmfreeway.com' + src
        
        # Query parametrelerini temizle (boyut sınırlamaları vs.)
        # Ama bazı CDN'ler için query gerekli olabilir, dikkatli ol
        
        return src
    
    def _extract_website(self, soup: BeautifulSoup) -> Optional[str]:
        """Resmi website'i çıkar"""
        website_patterns = [
            soup.find('a', href=True, string=re.compile(r'website|official|visit', re.I)),
            soup.find('a', class_=re.compile(r'website|official', re.I)),
            soup.find('a', rel='external'),
        ]
        
        for el in website_patterns:
            if el and el.get('href'):
                href = el.get('href')
                if href.startswith('http') and 'filmfreeway' not in href:
                    return href
        
        return None
    
    def _extract_years_running(self, soup: BeautifulSoup) -> Optional[int]:
        """Festival'in kaç yıldır düzenlendiğini çıkar"""
        text = soup.get_text()
        
        match = re.search(r'(\d+)(?:st|nd|rd|th)\s*(annual|edition|year)', text, re.I)
        if match:
            return int(match.group(1))
        
        match = re.search(r'edition\s*#?\s*(\d+)', text, re.I)
        if match:
            return int(match.group(1))
        
        match = re.search(r'since\s*(\d{4})', text, re.I)
        if match:
            start_year = int(match.group(1))
            return datetime.now().year - start_year
        
        return None
    
    def _extract_social_links(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Sosyal medya linklerini çıkar"""
        social = {}
        
        social_patterns = {
            'facebook': r'facebook\.com/([^/\s"\']+)',
            'twitter': r'(?:twitter|x)\.com/([^/\s"\']+)',
            'instagram': r'instagram\.com/([^/\s"\']+)',
            'youtube': r'youtube\.com/(?:channel/|user/|@)?([^/\s"\']+)',
            'vimeo': r'vimeo\.com/([^/\s"\']+)',
            'linkedin': r'linkedin\.com/(?:company/)?([^/\s"\']+)',
        }
        
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            for platform, pattern in social_patterns.items():
                if platform not in social:
                    match = re.search(pattern, href, re.I)
                    if match:
                        social[platform] = href
        
        return social
    
    # ========================================================================
    # AI DETECTION & SCORING
    # ========================================================================
    
    def _is_ai_festival(self, festival: Dict) -> bool:
        """Festival'in bir AI Film Festivali olup olmadığını belirle"""
        name = festival.get('name', '').lower()
        description = festival.get('description', '').lower()
        
        for indicator in AI_FESTIVAL_INDICATORS:
            if indicator in name:
                return True
        
        if re.match(r'^a\.?i\.?\s', name):
            return True
        
        if re.search(r'\bai\b', name):
            return True
        
        strong_indicators = ['ai-generated', 'artificial intelligence', 'generative ai', 'ai filmmaking']
        for indicator in strong_indicators:
            if indicator in description:
                return True
        
        return False
    
    def _is_ai_friendly(self, festival: Dict) -> bool:
        """Festival'in AI-Friendly olup olmadığını belirle"""
        if self._is_ai_festival(festival):
            return True
        
        name = festival.get('name', '').lower()
        description = festival.get('description', '').lower()
        categories = festival.get('category', [])
        
        if categories:
            categories_lower = [cat.lower() for cat in categories]
            for cat in categories_lower:
                for friendly_cat in AI_FRIENDLY_CATEGORIES:
                    if friendly_cat in cat:
                        return True
        
        for phrase in AI_FRIENDLY_PHRASES:
            if phrase in description:
                return True
        
        for friendly_cat in AI_FRIENDLY_CATEGORIES:
            if friendly_cat in name:
                return True
        
        return False
    
    def _get_festival_type(self, festival: Dict) -> str:
        """Festival tipini belirle"""
        if self._is_ai_festival(festival):
            return 'ai'
        elif self._is_ai_friendly(festival):
            return 'ai_friendly'
        else:
            return 'traditional'
    
    def _is_major_festival(self, name: str) -> bool:
        """Major festival mi kontrol et"""
        if not name:
            return False
        name_lower = name.lower()
        return any(major in name_lower for major in MAJOR_FESTIVALS)
    
    def _calculate_scores(self, festival: Dict) -> Tuple[int, int]:
        """AI Score ve Prestige Score hesapla"""
        name = festival.get('name', '').lower()
        description = festival.get('description', '').lower()
        
        if self._is_major_festival(festival.get('name', '')):
            return 98, 95
        
        if self._is_ai_festival(festival):
            ai_score = 85
            
            if 'international' in name:
                ai_score += 5
            if 'award' in name or 'awards' in name:
                ai_score += 3
            if festival.get('years_running', 0) > 3:
                ai_score += 2
        
        elif self._is_ai_friendly(festival):
            ai_score = 75
            
            if 'international' in name:
                ai_score += 5
            if festival.get('category') and len(festival['category']) > 5:
                ai_score += 3
        
        else:
            ai_score = 60
            
            if 'international' in name:
                ai_score += 5
            if 'award' in name or 'prize' in name:
                ai_score += 3
        
        if 'academy' in name or 'qualifying' in name:
            ai_score += 10
        if festival.get('years_running', 0) > 10:
            ai_score += 3
        if festival.get('years_running', 0) > 20:
            ai_score += 2
        if festival.get('awards') and len(festival.get('awards', [])) > 3:
            ai_score += 2
        
        ai_score = min(ai_score, 99)
        
        if ai_score >= 90:
            prestige = 90
        elif ai_score >= 80:
            prestige = 75
        elif ai_score >= 70:
            prestige = 60
        elif ai_score >= 60:
            prestige = 50
        else:
            prestige = 35
        
        return ai_score, prestige
    
    def _enrich_festival_data(self, festival: Dict) -> Dict:
        """Festival verisini zenginleştir"""
        if not festival:
            return None
        
        # İsim düzeltme
        name = festival.get('name', '')
        url = festival.get('external_url', '')
        
        # Eğer isim hala slug formatındaysa düzelt
        if url:
            slug = urlparse(url).path.strip('/').split('/')[0]
            # İsim slug'dan mı geliyor kontrol et
            name_normalized = name.lower().replace(' ', '').replace('-', '').replace('_', '')
            slug_normalized = slug.lower().replace('-', '').replace('_', '')
            
            if name_normalized == slug_normalized or not name:
                name = self._slug_to_readable_name(slug)
        
        # Yılları temizle
        name = re.sub(r'\b20[2-3]\d\b', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'^[\s\-–—,]+|[\s\-–—,]+$', '', name)
        festival['name'] = name or festival.get('name', '')
        
        festival['is_major'] = self._is_major_festival(festival.get('name', ''))
        
        is_ai_fest = self._is_ai_festival(festival)
        is_ai_friendly = self._is_ai_friendly(festival)
        
        festival['is_ai_festival'] = is_ai_fest
        festival['is_ai_film_friendly'] = is_ai_friendly
        festival['festival_type'] = self._get_festival_type(festival)
        
        ai_score, prestige = self._calculate_scores(festival)
        festival['ai_score'] = ai_score
        festival['ai_relevance_score'] = ai_score
        festival['prestige_score'] = prestige
        
        if festival.get('submission_deadline') and not festival.get('deadline_display'):
            dl_info = self._calculate_deadline_info(festival['submission_deadline'])
            festival['deadline_status'] = dl_info['status']
            festival['deadline_days_left'] = dl_info['days_left']
            festival['deadline_display'] = dl_info['display']
        
        festival['scraped_at'] = datetime.now().isoformat()
        festival['source'] = festival.get('source', 'filmfreeway')
        
        return festival
    
    # ========================================================================
    # CACHING
    # ========================================================================
    
    def _cache_key(self, url: str) -> str:
        """URL için cache key oluştur"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_cached(self, url: str) -> bool:
        """Festival cache'de mi ve güncel mi?"""
        key = self._cache_key(url)
        
        if key not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(key)
        if not timestamp:
            return False
        
        age = datetime.now() - timestamp
        return age.total_seconds() < (self.cache_hours * 3600)
    
    def _get_cached(self, url: str) -> Optional[Dict]:
        """Cache'den festival getir"""
        key = self._cache_key(url)
        return self._cache.get(key)
    
    def _cache_festival(self, url: str, festival: Dict):
        """Festival'i cache'e kaydet"""
        key = self._cache_key(url)
        self._cache[key] = festival
        self._cache_timestamps[key] = datetime.now()
    
    def clear_cache(self):
        """Cache'i temizle"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info("🗑️ Cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Cache istatistiklerini döndür"""
        total = len(self._cache)
        
        now = datetime.now()
        valid = 0
        expired = 0
        
        for key, timestamp in self._cache_timestamps.items():
            age = now - timestamp
            if age.total_seconds() < (self.cache_hours * 3600):
                valid += 1
            else:
                expired += 1
        
        return {
            'total': total,
            'valid': valid,
            'expired': expired,
            'cache_hours': self.cache_hours
        }
    
    # ========================================================================
    # HTTP FETCH - GELİŞTİRİLDİ
    # ========================================================================
    
    async def _fetch_url(self, url: str, max_retries: int = 5) -> Optional[str]:
        """URL'yi fetch et - Geliştirilmiş anti-bot bypass"""
        
        for attempt in range(max_retries):
            # Her denemede farklı impersonation
            imp = random.choice(self.impersonations)
            
            try:
                if CURL_AVAILABLE:
                    async with AsyncSession(impersonate=imp) as session:
                        # Rastgele bekleme (daha doğal görünmek için)
                        await asyncio.sleep(random.uniform(0.5, 2.0))
                        
                        # Rastgele User-Agent header'ları
                        headers = self._get_random_headers()
                        
                        response = await session.get(
                            url,
                            timeout=self.timeout,
                            headers=headers
                        )
                        
                        if response.status_code == 200:
                            logger.debug(f"✅ Fetched with {imp}: {url[:50]}...")
                            return response.text
                        elif response.status_code == 403:
                            logger.debug(f"⚠️ 403 with {imp} (attempt {attempt+1}/{max_retries})")
                            # Daha uzun bekleme
                            await asyncio.sleep(2.0 + attempt * 1.5)
                            continue
                        elif response.status_code == 429:
                            logger.warning(f"⚠️ Rate limited, waiting longer...")
                            await asyncio.sleep(10.0 + attempt * 5)
                            continue
                        elif response.status_code == 503:
                            logger.debug(f"⚠️ 503 Service Unavailable, retrying...")
                            await asyncio.sleep(3.0 + attempt * 2)
                            continue
                        else:
                            logger.debug(f"HTTP {response.status_code} for {url}")
                            continue
                
                elif HTTPX_AVAILABLE:
                    async with httpx.AsyncClient(
                        timeout=self.timeout,
                        follow_redirects=True
                    ) as client:
                        response = await client.get(url)
                        if response.status_code == 200:
                            return response.text
                        else:
                            logger.debug(f"HTTP {response.status_code} for {url}")
                            continue
                
                else:
                    logger.error("No HTTP client available (curl_cffi or httpx required)")
                    return None
                    
            except asyncio.TimeoutError:
                logger.debug(f"Timeout for {url} (attempt {attempt+1})")
                await asyncio.sleep(1.0)
                continue
            except Exception as e:
                logger.debug(f"Fetch error with {imp}: {str(e)[:50]}")
                await asyncio.sleep(1.0)
                continue
        
        logger.warning(f"❌ Failed to fetch after {max_retries} attempts: {url}")
        return None
    
    def _get_random_headers(self) -> Dict[str, str]:
        """Rastgele HTTP headers oluştur"""
        accept_languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.9,tr;q=0.8',
            'en;q=0.9',
        ]
        
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice(accept_languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
    
    # ========================================================================
    # MAIN ENTRY POINTS
    # ========================================================================
    
    async def discover_all(
        self,
        search_queries: List[str] = None,
        use_rss: bool = True,
        use_listing: bool = True
    ) -> List[Dict]:
        """Tüm kaynaklardan festival keşfet"""
        if search_queries is None:
            search_queries = ['ai', 'animation', 'experimental', 'digital', 'sci-fi']
        
        all_festivals = []
        seen_urls = set()
        
        # Phase 1: RSS Discovery
        if use_rss:
            logger.info("📡 Phase 1: RSS Discovery")
            try:
                rss_festivals = await self.discover_from_rss()
                for f in rss_festivals:
                    url = f.get('external_url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_festivals.append(f)
                logger.info(f"  RSS: {len(rss_festivals)} festivals found, {len(all_festivals)} unique")
            except Exception as e:
                logger.warning(f"  RSS Discovery failed: {e}")
        
        # Phase 2: FilmFreeway Listings
        if use_listing:
            logger.info("🔍 Phase 2: FilmFreeway Listings")
            for query in search_queries:
                try:
                    listing_festivals = await self.discover_from_filmfreeway_listing(
                        search_query=query,
                        max_festivals=50
                    )
                    
                    new_count = 0
                    for f in listing_festivals:
                        url = f.get('external_url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_festivals.append(f)
                            new_count += 1
                    
                    logger.info(f"  Query '{query}': {new_count} new festivals")
                    
                except Exception as e:
                    logger.warning(f"  Query '{query}' failed: {e}")
                
                await asyncio.sleep(2.0)  # Daha uzun bekleme
        
        logger.info(f"✅ Total discovered: {len(all_festivals)} unique festivals")
        return all_festivals
    
    async def scrape_full(
        self,
        search_queries: List[str] = None,
        enrich: bool = True,
        max_enrich: int = 200,
        use_rss: bool = True,
        use_listing: bool = True,
        force_refresh: bool = False
    ) -> List[Dict]:
        """Tam scraping pipeline"""
        # Discover
        festivals = await self.discover_all(
            search_queries=search_queries,
            use_rss=use_rss,
            use_listing=use_listing
        )
        
        if not festivals:
            logger.warning("No festivals discovered")
            return []
        
        # Enrich
        if enrich and self.fetch_details:
            festivals.sort(key=lambda x: x.get('priority', 5))
            
            to_enrich = festivals[:max_enrich]
            enriched = await self.enrich_festival_details(
                to_enrich,
                force_refresh=force_refresh
            )
            
            remaining = festivals[max_enrich:]
            for f in remaining:
                enriched_basic = self._enrich_festival_data(f)
                if enriched_basic:
                    enriched.append(enriched_basic)
            
            return enriched
        else:
            return [self._enrich_festival_data(f) for f in festivals if f]
    
    async def scrape_single_festival(self, url: str, force_refresh: bool = False) -> Optional[Dict]:
        """Tek bir festival'i scrape et"""
        if not force_refresh and self._is_cached(url):
            cached = self._get_cached(url)
            if cached:
                logger.info(f"📦 Retrieved from cache: {url}")
                return cached
        
        slug = urlparse(url).path.strip('/').split('/')[0]
        
        festival = {
            "external_url": url,
            "name": self._slug_to_readable_name(slug),
            "source": "direct",
            "needs_detail_fetch": True
        }
        
        detailed = await self._fetch_festival_details(festival)
        
        if detailed:
            enriched = self._enrich_festival_data(detailed)
            self._cache_festival(url, enriched)
            return enriched
        
        # Detay çekilemese bile basic bilgilerle dön
        basic = self._enrich_festival_data(festival)
        return basic


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

class FestivalScraper(HybridFestivalScraper):
    """Backward compatible wrapper"""
    
    def __init__(self, cache_hours: int = 24):
        super().__init__(cache_hours=cache_hours)
        logger.info("🔄 FestivalScraper (backward compatible) initialized")
    
    async def scrape_filmfreeway_deep(self, url: str, max_festivals: int = 250) -> List[Dict]:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        search_query = query_params.get('q', ['ai'])[0]
        
        logger.info(f"🔄 Deep scraping: {search_query}")
        
        return await self.scrape_full(
            search_queries=[search_query],
            enrich=True,
            max_enrich=max_festivals,
            use_rss=False,
            use_listing=True
        )
    
    async def scrape_by_source_type(
        self,
        source_type: str,
        source_id: str = None,
        url: str = None
    ) -> List[Dict]:
        festivals = []
        
        try:
            if source_type == "filmfreeway":
                target_url = url or "https://filmfreeway.com/festivals?q=ai&call_for_entries=1"
                festivals = await self.scrape_filmfreeway_deep(target_url)
            elif source_type == "scraper":
                if url and "filmfreeway" in url:
                    festivals = await self.scrape_filmfreeway_deep(url)
                else:
                    festivals = await self.scrape_full()
            elif source_type == "rss":
                rss_festivals = await self.discover_from_rss()
                festivals = await self.enrich_festival_details(rss_festivals)
            else:
                festivals = await self.scrape_full()
        except Exception as e:
            logger.error(f"❌ Scraping failed: {e}")
            raise
        
        if source_id:
            for f in festivals:
                f['source_id'] = source_id
        
        return festivals


# ============================================================================
# MODULE FUNCTIONS
# ============================================================================

async def scrape_festivals(search_queries: List[str] = None, max_festivals: int = 200) -> List[Dict]:
    scraper = FestivalScraper()
    return await scraper.scrape_full(search_queries=search_queries, max_enrich=max_festivals)


async def scrape_single(url: str) -> Optional[Dict]:
    scraper = FestivalScraper()
    return await scraper.scrape_single_festival(url)


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    async def test():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        
        print("\n" + "="*70)
        print("  Festival Scraper V8.0 - Test")
        print("="*70 + "\n")
        
        scraper = HybridFestivalScraper()
        
        # Test slug dönüşümü
        print("🧪 Test: Slug to Name Conversion")
        print("-" * 50)
        
        test_slugs = [
            "BerlinSciFiFilmfest",
            "AIinternationalFilmFestival",
            "HollywoodAIShortFilmAwards",
            "HKUST-AI-Film",
            "niff2026",
            "metadisruption-AIInternationalArtandDesignFestival",
            "IndywoodInternationalAICinefest",
        ]
        
        for slug in test_slugs:
            name = scraper._slug_to_readable_name(slug)
            print(f"  {slug}")
            print(f"  → {name}")
            print()
        
        print("="*70 + "\n")
    
    asyncio.run(test())