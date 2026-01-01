"""
News Aggregator Service - BATCH AI EDITION 🚀
Tüm haberleri TEK SEFERDE analiz eder - Ultra hızlı, minimal kota kullanımı
"""
import os
import asyncio
import logging
import re
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from bs4 import BeautifulSoup
import feedparser
from dotenv import load_dotenv

# Browser impersonation
try:
    from curl_cffi.requests import AsyncSession
    CURL_AVAILABLE = True
except ImportError:
    CURL_AVAILABLE = False

# Google Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

import httpx

load_dotenv()
logger = logging.getLogger(__name__)


# =========================================================================
# 🧠 BATCH AI PROVIDER - Tüm haberleri tek seferde analiz eder
# =========================================================================
class GeminiBatchProvider:
    """
    Gemini Batch Provider - 20+ haberi TEK API çağrısında analiz eder
    """
    
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.current_key_idx = 0
        self.model = None
        self.max_batch_size = 25
        
        if self.api_keys:
            self._configure_model()
    
    def _configure_model(self):
        """Aktif API key ile modeli yapılandır"""
        if not self.api_keys:
            return
        
        try:
            genai.configure(api_key=self.api_keys[self.current_key_idx])
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            logger.info(f"🔑 Gemini configured (key {self.current_key_idx + 1}/{len(self.api_keys)})")
        except Exception as e:
            logger.error(f"❌ Gemini config error: {e}")
    
    def _rotate_key(self) -> bool:
        """Sonraki API key'e geç"""
        if len(self.api_keys) <= 1:
            return False
        
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        logger.warning(f"🔄 Rotating to API key #{self.current_key_idx + 1}")
        self._configure_model()
        return True
    
    def _build_batch_prompt(self, articles: List[Dict]) -> str:
        """Toplu analiz için prompt oluştur - F-STRING YOK!"""
        
        # Haber listesini JSON formatına çevir
        articles_json = json.dumps([
            {
                "id": a["temp_id"],
                "title": a["title"][:100],
                "summary": a["summary"][:150]
            }
            for a in articles
        ], ensure_ascii=False, indent=2)
        
        # ⚠️ NORMAL STRING KULLAN - f-string DEĞİL!
        prompt = """
You are a content curator for AIcineDB, a database for Filmmakers and VFX Artists.

Analyze each article and determine if it's relevant to:
1. Cinema/Film Technology (cameras, lenses, lighting, audio gear)
2. AI in Creative Fields (Sora, Runway, Midjourney, etc.)
3. Post-Production Software (Premiere, DaVinci, Nuke, Blender, Unreal)
4. VFX/Virtual Production/Motion Capture
5. Film Industry Tech News

EXCLUDE: Celebrity gossip, movie reviews (unless tech-focused), politics, crime.

Be LENIENT - if borderline relevant, INCLUDE IT.

OUTPUT FORMAT:
Return a JSON object where keys are article IDs and values have "relevant" (boolean) and "score" (0-100).

Example:
{"0": {"relevant": true, "score": 85}, "1": {"relevant": false, "score": 15}}

Return ONLY raw JSON. No markdown, no explanation.

ARTICLES TO ANALYZE:
"""
        # articles_json'ı prompt'un sonuna ekle
        return prompt + articles_json
    
    async def analyze_batch(self, articles: List[Dict]) -> Dict[int, Dict]:
        """Tüm haberleri TEK SEFERDE analiz et"""
        if not articles:
            return {}
        
        if not self.model:
            logger.warning("⚠️ No AI model, accepting all articles")
            return {a["temp_id"]: {"relevant": True, "score": 50} for a in articles}
        
        all_results = {}
        
        for i in range(0, len(articles), self.max_batch_size):
            batch = articles[i:i + self.max_batch_size]
            batch_results = await self._analyze_single_batch(batch)
            all_results.update(batch_results)
        
        return all_results
    
    async def _analyze_single_batch(self, articles: List[Dict]) -> Dict[int, Dict]:
        """Tek bir batch'i analiz et"""
        
        prompt = self._build_batch_prompt(articles)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🤖 Batch analyzing {len(articles)} articles... (attempt {attempt + 1})")
            
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json" # <--- BU SATIR HAYAT KURTARIR
                    }
                )
                
                # JSON temizliği
                text = response.text.strip()
                
                # Markdown code block temizle
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                    text = text.strip()
                
                # Parse et
                try:
                    results = json.loads(text)
                    
                    # String key'leri int'e çevir
                    parsed = {}
                    for key, value in results.items():
                        try:
                            article_id = int(key)
                            if isinstance(value, dict):
                                parsed[article_id] = {
                                    "relevant": value.get("relevant", False),
                                    "score": value.get("score", 50)
                                }
                            elif isinstance(value, bool):
                                parsed[article_id] = {
                                    "relevant": value,
                                    "score": 70 if value else 20
                                }
                        except (ValueError, TypeError):
                            continue
                    
                    relevant_count = sum(1 for v in parsed.values() if v.get("relevant"))
                    logger.info(f"✅ Batch complete: {relevant_count}/{len(parsed)} relevant")
                    return parsed
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON parse error: {e}")
                    logger.debug(f"Raw response: {text[:500]}")
                    # Fallback: hepsini kabul et
                    return {a["temp_id"]: {"relevant": True, "score": 50} for a in articles}
                
            except Exception as e:
                error_str = str(e).lower()
                
                if "429" in str(e) or "quota" in error_str or "resource" in error_str:
                    logger.warning("⚠️ Quota exceeded!")
                    
                    if self._rotate_key():
                        logger.info(" Waiting 10 seconds for new key cooldown...")
                        await asyncio.sleep(10)
                        continue
                    else:
                        await asyncio.sleep(60)
                        continue
                
                logger.error(f" Gemini batch error: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # Hata durumunda hepsini kabul et
        logger.warning("⚠️ All batch attempts failed, accepting all articles")
        return {a["temp_id"]: {"relevant": True, "score": 40} for a in articles}
# =========================================================================
#  ANA NEWS AGGREGATOR SINIFI
# =========================================================================
class NewsAggregator:
    """AI-powered news aggregator with BATCH processing"""
    
    # =====================================================================
    # AI Anahtar Kelimeleri - Yüksek skor (+15 each)
    # =====================================================================
    AI_KEYWORDS = [
        # Core AI terms
        "artificial intelligence", " ai ", "ai-", "-ai", "ai's", "a.i.",
        "generative ai", "genai", "gen ai", "gen-ai",
        # AI Companies & Products
        "chatgpt", "gpt-4", "gpt-5", "gpt4", "gpt5", "openai", "open ai",
        "anthropic", "claude", "gemini", "copilot", "bard",
        "midjourney", "stable diffusion", "dall-e", "dalle", "dall e",
        "sora", "runway", "pika labs", "kling", "luma", "haiper",
        # Technical terms
        "deepfake", "deep fake", "neural network", "machine learning",
        "large language model", "llm", "diffusion model", "transformer",
        "deep learning", "computer vision", "natural language processing",
        # Industry
        "vfx", "visual effects", "cgi", "virtual production", "led wall",
        "nvidia", "adobe firefly", "adobe sensei",
        "text-to-video", "text to video", "ai-generated", "ai generated",
        "synthetic media", "digital human", "digital twin",
        # Film-specific AI
        "ai in film", "ai filmmaking", "ai cinema", "ai movies",
        "ai animation", "ai vfx", "ai visual effects", "ai-powered",
        "ai actors", "virtual actors", "de-aging", "face swap",
        "ai screenwriting", "ai script", "ai editing", "ai color",
        # Türkçe
        "yapay zeka", "yapay zekâ", "derin öğrenme", "makine öğrenmesi",
        "sanal prodüksiyon", "görsel efekt",
    ]
    
    # =====================================================================
    # Film/Sinema Anahtar Kelimeleri - Orta skor (+8 each)
    # =====================================================================
    CINEMA_KEYWORDS = [
        # Core film terms
        "film", "movie", "cinema", "movies", "films", "motion picture",
        "hollywood", "bollywood", "studio", "studios",
        # People
        "director", "actor", "actress", "star", "cast", "filmmaker",
        "producer", "screenwriter", "cinematographer",
        # Production
        "screenplay", "production", "filming", "shooting", "wrap",
        "post-production", "pre-production", "on set", "on-set",
        # Business
        "box office", "blockbuster", "premiere", "release", "theatrical",
        "opening weekend", "gross", "budget", "greenlit", "greenlight",
        # Distribution
        "streaming", "netflix", "disney", "disney+", "hbo", "hbo max",
        "amazon prime", "prime video", "apple tv", "apple tv+",
        "hulu", "peacock", "paramount+", "max",
        # Studios
        "warner", "warner bros", "paramount", "universal", "sony",
        "lionsgate", "a24", "focus features", "searchlight", "miramax",
        "mgm", "20th century", "new line", "blumhouse",
        # Animation
        "animation", "animated", "pixar", "dreamworks", "illumination",
        "laika", "ghibli", "anime", "cartoon",
        # Awards & Festivals  
        "oscar", "oscars", "academy award", "emmy", "golden globe", "bafta",
        "cannes", "sundance", "venice", "berlin", "toronto", "tiff",
        "tribeca", "sxsw", "telluride", "locarno", "venice film",
        # Genres
        "documentary", "thriller", "horror", "comedy", "drama", "action",
        "sci-fi", "science fiction", "fantasy", "romance", "indie",
        "superhero", "marvel", "dc", "sequel", "franchise", "reboot",
        # TV
        "tv series", "television", "series", "season", "episode", "showrunner",
        "limited series", "miniseries", "pilot",
        # Türkçe
        "sinema", "yönetmen", "oyuncu", "yapım", "dizi", "senaryo",
        "prodüksiyon", "fragman", "gala", "ödül", "vizyona", "seyirci",
    ]
    
    # =====================================================================
    # 🚫 YASAKLI KELİMELER (Magazin/Gossip) - Direkt Eleme
    # =====================================================================
    BLOCK_KEYWORDS = [
        # Celebrity gossip
        "diddy", "arrested", "jail", "prison", "lawsuit", "allegation", "scandal",
        "divorce", "break up", "breakup", "dating", "boyfriend", "girlfriend", 
        "engaged", "engagement", "married", "wedding", "split", "cheating",
        # Fashion/Red Carpet
        "red carpet", "fashion", "outfit", "dress", "look", "stunning", 
        "wore", "style", "gala", "party", "met gala",
        # Box Office Only
        "opening weekend", "grossed", "revenue", "profit", "bombed",
        # Death/Obituary
        "dead", "dies", "died", "death", "obituary", "memorial", "funeral",
        "passed away", "rip", "rest in peace",
        # Politics
        "election", "vote", "campaign", "politician", "senate", "congress",
        # Crime
        "murder", "killed", "shooting", "crime", "trial", "verdict",
        # Türkçe magazin
        "boşandı", "ayrıldı", "sevgili", "ödül töreni", "kırmızı halı",
        "tutuklandı", "hapis", "dava",
    ]
    
    # =====================================================================
    # Default Sources
    # =====================================================================
    DEFAULT_SOURCES = [
        {
            "name": "The Verge",
            "url": "https://www.theverge.com/rss/index.xml",
            "source_type": "rss",
            "category": ["tech", "ai"]
        },
        {
            "name": "TechCrunch",
            "url": "https://techcrunch.com/feed/",
            "source_type": "rss",
            "category": ["startup", "tech"]
        },
        {
            "name": "Ars Technica",
            "url": "https://arstechnica.com/feed/",
            "source_type": "rss",
            "category": ["tech", "science"]
        },
        {
            "name": "MIT Tech Review",
            "url": "https://www.technologyreview.com/feed/",
            "source_type": "rss",
            "category": ["science", "tech"]
        },
        # Yapay Zeka Odaklı
        {
            "name": "VentureBeat AI",
            "url": "https://venturebeat.com/category/ai/feed/",
            "source_type": "rss",
            "category": ["ai"]
        },
        # Uzay ve Bilim
        {
            "name": "Space.com",
            "url": "https://www.space.com/feeds/all",
            "source_type": "rss",
            "category": ["space"]
        },
        {
            "name": "ScienceDaily",
            "url": "https://www.sciencedaily.com/rss/matter_energy.xml",
            "source_type": "rss",
            "category": ["science", "energy"]
        },
        # Temiz Enerji
        {
            "name": "CleanTechnica",
            "url": "https://cleantechnica.com/feed/",
            "source_type": "rss",
            "category": ["energy"]
        }
    ]

    # =====================================================================
    # Scraper için SKIP listesi
    # =====================================================================
    SKIP_TITLES = [
        "home", "about", "contact", "login", "sign up", "subscribe",
        "menu", "search", "more", "see all", "view all", "read more",
        "next", "previous", "back", "close", "share", "comment",
        "news", "reviews", "features", "podcasts", "videos", "shop",
        "facebook", "twitter", "instagram", "youtube", "linkedin", "tiktok",
        "ana sayfa", "hakkımızda", "iletişim", "giriş", "kayıt",
    ]
    
    ARTICLE_PATTERNS = [
        r'/\d{4}/\d{2}/',
        r'/article/',
        r'/news/',
        r'/story/',
        r'/post/',
        r'/blog/',
        r'-\d+/?$',
    ]

    def __init__(self, sources: Optional[List[Dict]] = None, filter_mode: str = "strict"):
        self.sources = sources if sources else self.DEFAULT_SOURCES
        self.filter_mode = filter_mode
        
        self.user_agent = os.getenv(
            "SCRAPING_USER_AGENT", 
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15"
        )
        self.timeout = float(os.getenv("SCRAPING_TIMEOUT", "30"))
        self.rate_limit_delay = float(os.getenv("SCRAPING_RATE_LIMIT_DELAY", "2"))
        self.max_retries = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
        
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        # 🧠 BATCH GEMINI KURULUMU
        gemini_keys_str = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_NEW_AGENT", "")
        
        # Virgülle ayrılmış key'leri parse et
        self.gemini_keys = [k.strip() for k in gemini_keys_str.split(',') if k.strip()]
        
        self.use_ai_filter = GEMINI_AVAILABLE and len(self.gemini_keys) > 0
        self.batch_provider = None
        
        if self.use_ai_filter:
            try:
                self.batch_provider = GeminiBatchProvider(self.gemini_keys)
                logger.info(f"🧠 BATCH AI MODE ACTIVE: {len(self.gemini_keys)} API key(s) loaded 🚀")
            except Exception as e:
                logger.error(f"❌ Batch provider init failed: {e}")
                self.use_ai_filter = False
        else:
            logger.warning("⚠️ AI Filter DISABLED - Using keyword filter only")
        
        logger.info(f"📰 NewsAggregator initialized: {len(self.sources)} sources, mode={filter_mode}")

    # =====================================================================
    # FETCH CONTENT
    # =====================================================================
    async def _fetch_content(self, url: str, retry_count: int = 0) -> Optional[str]:
        """Fetch URL content with retry logic"""
        if CURL_AVAILABLE:
            try:
                async with AsyncSession(impersonate="safari15_5") as session:
                    response = await session.get(url, timeout=self.timeout)
                    if response.status_code == 200:
                        logger.debug(f"✅ Fetched {url}")
                        return response.text
            except:
                pass
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
        except Exception as e:
            if retry_count < self.max_retries:
                await asyncio.sleep(self.rate_limit_delay * (retry_count + 1))
                return await self._fetch_content(url, retry_count + 1)
            logger.error(f"❌ Failed to fetch {url}: {e}")
        
        return None

    # =====================================================================
    # KEYWORD CHECKERS
    # =====================================================================
    def _has_ai_keywords(self, text: str) -> bool:
        if not text:
            return False
        text_lower = " " + text.lower().replace("-", " ").replace("_", " ") + " "
        return any(kw in text_lower for kw in self.AI_KEYWORDS)
    
    def _has_cinema_keywords(self, text: str) -> bool:
        if not text:
            return False
        text_lower = " " + text.lower() + " "
        return any(kw in text_lower for kw in self.CINEMA_KEYWORDS)
    
    def _has_blocked_keywords(self, text: str) -> bool:
        """Yasaklı kelime kontrolü"""
        if not text:
            return False
        text_lower = text.lower()
        return any(bad in text_lower for bad in self.BLOCK_KEYWORDS)

    def _pre_filter(self, title: str, summary: str = "") -> bool:
        """Ön eleme - AI'a sormadan önce hızlı filtre"""
        combined = f"{title} {summary}"
        
        # 1. Yasaklı kelime varsa REDDET
        if self._has_blocked_keywords(combined):
            return False
        
        # 2. En az bir teknoloji/sinema kelimesi olmalı
        has_relevant = self._has_ai_keywords(combined) or self._has_cinema_keywords(combined)
        return has_relevant

    def _calculate_relevance_score(self, title: str, summary: str) -> int:
            combined = (title + " " + summary).lower()
            score = 0
            
            # 1. Herhangi bir yasaklı kelime varsa direkt 0 puan
            if any(bad in combined for bad in self.BLOCK_KEYWORDS):
                return 0

            # 2. Kategori Puanlaması
            ai_matches = sum(1 for kw in self.AI_KEYWORDS if kw in combined)
            space_matches = sum(1 for kw in self.SPACE_KEYWORDS if kw in combined)
            energy_matches = sum(1 for kw in self.ENERGY_KEYWORDS if kw in combined)
            
            # Puan ekle (Space ve Energy haberleri de artık değerli)
            score += min(ai_matches * 20, 60)
            score += min(space_matches * 20, 60)
            score += min(energy_matches * 20, 60)
            
            # Eğer hiç teknoloji kelimesi yoksa puan verme
            if score == 0:
                return 10
                
            return min(score, 100)

    # =====================================================================
    # IMAGE EXTRACTION
    # =====================================================================
    def _extract_image_from_entry(self, entry) -> Optional[str]:
        """RSS entry'den resim çıkar"""
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('url'):
                    return media['url']
        
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enc in entry.enclosures:
                if 'image' in enc.get('type', ''):
                    return enc.get('href') or enc.get('url')
        
        content = ""
        if entry.get('content'):
            content = entry['content'][0].get('value', '')
        summary = entry.get('summary', '') or entry.get('description', '')
        html = content or summary
        
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            img = soup.find('img')
            if img:
                return img.get('src') or img.get('data-src')
        
        return None

    async def _extract_image_from_url(self, url: str) -> Optional[str]:
        """URL'den og:image vs. çıkar"""
        try:
            html = await self._fetch_content(url)
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Open Graph
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                return og["content"]
            
            # Twitter
            tw = soup.find("meta", name="twitter:image")
            if tw and tw.get("content"):
                return tw["content"]
            
            # JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and "image" in data:
                        img = data["image"]
                        if isinstance(img, str):
                            return img
                        if isinstance(img, dict):
                            return img.get("url")
                        if isinstance(img, list) and img:
                            return img[0] if isinstance(img[0], str) else img[0].get("url")
                except:
                    pass
            
            # Fallback img
            for img in soup.find_all("img", src=True):
                src = img["src"]
                if not any(bad in src.lower() for bad in ["logo", "icon", "avatar", "pixel"]):
                    if src.startswith("http"):
                        return src
                        
        except Exception as e:
            logger.debug(f"Image extraction failed: {e}")
        
        return None

    # =====================================================================
    # TAG & DATE EXTRACTION
    # =====================================================================
    def _extract_tags_from_entry(self, entry) -> List[str]:
        tags = []
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                term = tag.get('term', '').strip()
                if term:
                    tags.append(term)
        return list(set(tags))[:10]

    def _parse_publish_date(self, entry) -> Optional[str]:
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                return dt.isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                dt = datetime(*entry.updated_parsed[:6])
                return dt.isoformat()
        except:
            pass
        return None

    # =====================================================================
    # 🚀 BATCH RSS PROCESSING - Ana Optimizasyon
    # =====================================================================
    async def _process_rss_source(self, source: Dict, content: str) -> List[Dict]:
        """
        RSS kaynağını BATCH AI ile işle
        
        Akış:
        1. Tüm entry'leri oku
        2. Kelime bazlı ön filtre (hızlı)
        3. Kalan haberleri TEK SEFERDE AI'a gönder
        4. Sadece onaylananlar için resim bul
        """
        articles = []
        feed = feedparser.parse(content)
        
        if not feed.entries:
            logger.warning(f"⚠️ No entries: {source.get('name')}")
            return articles
        
        source_name = source.get('name', 'Unknown')
        logger.info(f"📋 Processing {len(feed.entries)} entries from {source_name}")
        
        # ─────────────────────────────────────────────────────────────────
        # ADIM 1: Ön Filtre (Kelime Kontrolü - AI'a göndermeden önce eleme)
        # ─────────────────────────────────────────────────────────────────
        candidates = []
        
        for entry in feed.entries[:30]:  # Max 30 entry/kaynak
            try:
                title = entry.get('title', '').strip()
                if not title or len(title) < 10:
                    continue
                
                summary_raw = entry.get('summary', '') or entry.get('description', '')
                soup = BeautifulSoup(summary_raw, 'html.parser')
                summary = soup.get_text(strip=True)[:300]
                
                # Kelime bazlı ön filtre
                if not self._pre_filter(title, summary):
                    continue
                
                # Aday listeye ekle
                candidates.append({
                    'temp_id': len(candidates),
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'entry': entry
                })
                
            except Exception as e:
                logger.debug(f"Entry parse error: {e}")
                continue
        
        if not candidates:
            logger.info(f"✨ No keyword matches in {source_name}")
            return articles
        
        logger.info(f"🔍 Pre-filtered: {len(candidates)} candidates from {source_name}")
        
        # ─────────────────────────────────────────────────────────────────
        # ADIM 2: 🧠 BATCH AI ANALİZİ (TEK API ÇAĞRISI!)
        # ─────────────────────────────────────────────────────────────────
        if self.use_ai_filter and self.batch_provider:
            ai_results = await self.batch_provider.analyze_batch(candidates)
        else:
            # AI kapalıysa keyword skoru kullan
            ai_results = {
                c["temp_id"]: {
                    "relevant": True, 
                    "score": self._calculate_relevance_score(c["title"], c["summary"])
                } 
                for c in candidates
            }
        
        # ─────────────────────────────────────────────────────────────────
        # ADIM 3: Sonuçları İşle (Sadece onaylananlar için resim bul)
        # ─────────────────────────────────────────────────────────────────
        source_category = source.get("category", ["news"])
        if isinstance(source_category, str):
            source_category = [source_category]
        
        accepted = 0
        rejected = 0
        
        for candidate in candidates:
            temp_id = candidate['temp_id']
            ai_result = ai_results.get(temp_id, {'relevant': False, 'score': 0})
            
            is_relevant = ai_result.get('relevant', False)
            score = ai_result.get('score', 0)
            
            if not is_relevant:
                rejected += 1
                logger.debug("  REJECTED [%s] %s...", score, candidate['title'][:50])
                continue
            
            accepted += 1
            logger.info("  ACCEPTED [%s] %s...", score, candidate['title'][:50])
            
            # 🎯 Sadece onaylananlar için resim bul (büyük optimizasyon!)
            image_url = self._extract_image_from_entry(candidate['entry'])
            if not image_url and candidate['link']:
                image_url = await self._extract_image_from_url(candidate['link'])
            
            # Meta bilgiler
            tags = self._extract_tags_from_entry(candidate['entry'])
            published_at = self._parse_publish_date(candidate['entry'])
            
            has_ai = self._has_ai_keywords(f"{candidate['title']} {candidate['summary']}")
            has_cinema = self._has_cinema_keywords(f"{candidate['title']} {candidate['summary']}")
            
            if has_ai and "AI" not in tags:
                tags.insert(0, "AI")
            if has_cinema and "Film" not in tags:
                tags.insert(0, "Film")
            tags.insert(0, "AI-Verified")
            
            articles.append({
                "source_id": source.get("id"),
                "source_name": source_name,
                "title": candidate['title'],
                "summary": candidate['summary'],
                "external_url": candidate['link'],
                "published_at": published_at or datetime.now().isoformat(),
                "image_url": image_url,
                "author": candidate['entry'].get('author') or source_name,
                "ai_relevance_score": score,
                "is_ai_cinema_relevant": has_ai and has_cinema,
                "has_ai_keywords": has_ai,
                "has_cinema_keywords": has_cinema,
                "category": source_category,
                "tags": tags,
                "extraction_method": "batch_ai_rss"
            })
        
        logger.info(f"📡 {source_name}: ✅ {accepted} accepted, 🗑️ {rejected} rejected")
        return articles

    # =====================================================================
    # SCRAPER SOURCE PROCESSING
    # =====================================================================
    async def _process_scraper_source(self, source: Dict, content: str) -> List[Dict]:
        """HTML scraper - batch AI ile"""
        articles = []
        soup = BeautifulSoup(content, 'html.parser')
        
        source_name = source.get("name", "Unknown")
        source_category = source.get("category", ["news"])
        if isinstance(source_category, str):
            source_category = [source_category]
        
        base_url = "/".join(source.get("url", "").split('/')[:3])
        seen_urls = set()
        
        # Aday toplama
        candidates = []
        
        containers = soup.find_all(['article', 'div'], class_=re.compile(
            r'(post|article|story|news|card|item|entry)', re.I
        ))
        
        for container in containers[:30]:
            try:
                link = container.find('a', href=True)
                if not link:
                    continue
                
                href = link['href']
                if href.startswith('/'):
                    full_url = base_url + href
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                
                # Başlık bul
                title = None
                for tag in ['h1', 'h2', 'h3', 'h4']:
                    h = container.find(tag)
                    if h:
                        title = h.get_text(strip=True)
                        break
                
                if not title:
                    title = link.get_text(strip=True) or link.get('title', '')
                
                if not title or len(title) < 25:
                    continue
                
                title_lower = title.lower().strip()
                if title_lower in self.SKIP_TITLES:
                    continue
                if len(title.split()) < 4:
                    continue
                
                # Ön filtre
                if not self._pre_filter(title):
                    continue
                
                # Summary
                summary = ""
                excerpt = container.find(['p', 'div'], class_=re.compile(r'(excerpt|summary|desc)', re.I))
                if excerpt:
                    summary = excerpt.get_text(strip=True)[:300]
                
                candidates.append({
                    'temp_id': len(candidates),
                    'title': title,
                    'summary': summary,
                    'link': full_url,
                    'container': container
                })
                
            except Exception as e:
                logger.debug(f"Container error: {e}")
                continue
        
        if not candidates:
            return articles
        
        logger.info(f"🔍 Scraper pre-filtered: {len(candidates)} candidates from {source_name}")
        
        # BATCH AI ANALİZİ
        if self.use_ai_filter and self.batch_provider:
            ai_results = await self.batch_provider.analyze_batch(candidates)
        else:
            ai_results = {
                c["temp_id"]: {"relevant": True, "score": 50} 
                for c in candidates
            }
        
        # Sonuçları işle
        for candidate in candidates:
            temp_id = candidate['temp_id']
            ai_result = ai_results.get(temp_id, {'relevant': False, 'score': 0})
            
            if not ai_result.get('relevant', False):
                continue
            
            score = ai_result.get('score', 0)
            
            # Resim
            image_url = None
            img = candidate['container'].find('img')
            if img:
                image_url = img.get('src') or img.get('data-src')
                if image_url and image_url.startswith('/'):
                    image_url = base_url + image_url
            
            if not image_url:
                image_url = await self._extract_image_from_url(candidate['link'])
            
            has_ai = self._has_ai_keywords(candidate['title'])
            has_cinema = self._has_cinema_keywords(candidate['title'])
            tags = ["AI-Verified"]
            if has_ai:
                tags.append("AI")
            if has_cinema:
                tags.append("Film")
            
            articles.append({
                "source_id": source.get("id"),
                "source_name": source_name,
                "title": candidate['title'],
                "summary": candidate['summary'] or f"{candidate['title'][:100]}...",
                "external_url": candidate['link'],
                "published_at": datetime.now().isoformat(),
                "image_url": image_url,
                "author": source_name,
                "ai_relevance_score": score,
                "is_ai_cinema_relevant": has_ai and has_cinema,
                "has_ai_keywords": has_ai,
                "has_cinema_keywords": has_cinema,
                "category": source_category,
                "tags": tags,
                "extraction_method": "batch_ai_scraper"
            })
            
            if len(articles) >= 15:
                break
        
        logger.info(f"🕷️ Scraper [{source_name}]: {len(articles)} articles")
        return articles

    # =====================================================================
    # MAIN METHODS
    # =====================================================================
    async def scrape_source(self, source: Dict) -> List[Dict]:
        """Tek bir kaynağı scrape et"""
        url = source.get("url")
        name = source.get("name", "Unknown")
        stype = (source.get("source_type") or "rss").lower()
        
        if not url:
            return []
        
        await asyncio.sleep(self.rate_limit_delay)
        
        content = await self._fetch_content(url)
        if not content:
            logger.error(f"❌ Failed to fetch: {name}")
            return []
        
        try:
            if stype in ['rss', 'feed']:
                logger.info(f"📡 Processing RSS: {name}")
                return await self._process_rss_source(source, content)
            else:
                logger.info(f"🕷️ Processing HTML: {name}")
                return await self._process_scraper_source(source, content)
        except Exception as e:
            logger.error(f"❌ Error processing {name}: {e}")
            return []

    async def aggregate_all_sources(self) -> List[Dict]:
        """Tüm kaynaklardan haberleri topla"""
        logger.info(f"📰 Aggregating from {len(self.sources)} sources...")
        
        tasks = [self.scrape_source(s) for s in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        for i, result in enumerate(results):
            name = self.sources[i].get('name', f'Source {i}')
            if isinstance(result, list):
                all_articles.extend(result)
                logger.info(f"  ✓ {name}: {len(result)} articles")
            else:
                logger.error(f"  ✗ {name}: {result}")
        
        logger.info(f"✅ Total collected: {len(all_articles)} articles")
        return all_articles

    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """URL'e göre duplicate temizle"""
        seen = set()
        unique = []
        for a in articles:
            url = a.get('external_url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(a)
        
        removed = len(articles) - len(unique)
        if removed > 0:
            logger.info(f"🗑️ Removed {removed} duplicates")
        return unique

    async def fetch_and_deduplicate(self) -> List[Dict]:
        """Ana entry point - haberleri topla, filtrele, dedupe et"""
        articles = await self.aggregate_all_sources()
        unique = self.deduplicate_articles(articles)
        
        # Score'a göre sırala (en yüksek önce)
        unique.sort(key=lambda x: x.get('ai_relevance_score', 0), reverse=True)
        
        logger.info(f"🎯 FINAL RESULT: {len(unique)} AI-verified articles")
        return unique


# =========================================================================
# CONVENIENCE FUNCTION
# =========================================================================
async def aggregate_news(
    sources: Optional[List[Dict]] = None, 
    filter_mode: str = "strict"
) -> List[Dict]:
    """
    Ana entry point for news aggregation
    
    Args:
        sources: Kaynak listesi (opsiyonel, default sources kullanılır)
        filter_mode: 'strict' veya 'relaxed'
        
    Returns:
        Deduplicated, AI-filtered haber listesi
    """
    aggregator = NewsAggregator(sources, filter_mode)
    return await aggregator.fetch_and_deduplicate()


# =========================================================================
# TEST RUNNER
# =========================================================================
if __name__ == "__main__":
    # Logging ayarla
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        print("=" * 70)
        print("🧪 Testing BATCH AI News Aggregator")
        print("=" * 70)
        
        articles = await aggregate_news()
        
        print(f"\n{'=' * 70}")
        print(f"✅ Found {len(articles)} AI-verified articles")
        print("=" * 70)
        
        for i, a in enumerate(articles[:10], 1):
            print(f"\n{i}. [{a['ai_relevance_score']:2d}] {a['title'][:60]}...")
            print(f"   📰 Source: {a['source_name']}")
            print(f"   🖼️  Image: {'✅' if a.get('image_url') else '❌'}")
            print(f"   🏷️  Tags: {', '.join(a.get('tags', [])[:3])}")
    
    asyncio.run(test())