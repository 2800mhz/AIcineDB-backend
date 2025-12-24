"""
News Aggregator Service
Aggregates film industry news from RSS feeds with duplicate detection
"""
import os
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import httpx
import feedparser
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class NewsAggregator:
    """Aggregates news from multiple RSS feeds"""
    
    # Default news sources
    DEFAULT_SOURCES = [
        {
            "name": "Variety",
            "url": "https://variety.com/feed/",
            "category": ["industry", "news"]
        },
        {
            "name": "The Hollywood Reporter",
            "url": "https://www.hollywoodreporter.com/feed/",
            "category": ["industry", "news"]
        },
        {
            "name": "IndieWire",
            "url": "https://www.indiewire.com/feed/",
            "category": ["independent", "news"]
        },
        {
            "name": "Screen Daily",
            "url": "https://www.screendaily.com/rss/",
            "category": ["international", "news"]
        },
        {
            "name": "Deadline",
            "url": "https://deadline.com/feed/",
            "category": ["industry", "breaking"]
        },
    ]
    
    def __init__(self, sources: Optional[List[Dict]] = None):
        self.sources = sources or self.DEFAULT_SOURCES
        self.user_agent = os.getenv("SCRAPING_USER_AGENT", "AICineDB Bot/1.0")
        self.rate_limit_delay = float(os.getenv("SCRAPING_RATE_LIMIT_DELAY", "2"))
        self.max_retries = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
        
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
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
    
    def _extract_image_from_entry(self, entry) -> Optional[str]:
        """Extract image URL from RSS entry"""
        # Try media:content (common in RSS feeds)
        if hasattr(entry, 'media_content') and entry.media_content:
            for media in entry.media_content:
                if media.get('medium') == 'image' or 'image' in media.get('type', ''):
                    return media.get('url')
        
        # Try media:thumbnail
        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
            return entry.media_thumbnail[0].get('url')
        
        # Try enclosures
        if hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if 'image' in enclosure.get('type', ''):
                    return enclosure.get('href')
        
        # Try parsing from content/summary
        content = entry.get('content', [{}])[0].get('value', '') if entry.get('content') else ''
        summary = entry.get('summary', '') or entry.get('description', '')
        html_content = content or summary
        
        if html_content:
            soup = BeautifulSoup(html_content, 'html.parser')
            img = soup.find('img')
            if img and img.get('src'):
                return img['src']
        
        return None
    
    def _extract_tags_from_entry(self, entry) -> List[str]:
        """Extract tags from RSS entry"""
        tags = []
        
        # Try tags field
        if hasattr(entry, 'tags') and entry.tags:
            tags.extend([tag.get('term', '').lower() for tag in entry.tags if tag.get('term')])
        
        # Try categories
        if hasattr(entry, 'categories') and entry.categories:
            tags.extend([cat.lower() for cat in entry.categories if isinstance(cat, str)])
        
        return list(set(tags))[:10]  # Remove duplicates and limit to 10
    
    def _parse_publish_date(self, entry) -> Optional[str]:
        """Parse published date from entry"""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                return dt.isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                dt = datetime(*entry.updated_parsed[:6])
                return dt.isoformat()
        except Exception as e:
            logger.warning(f"Failed to parse date: {e}")
        
        return None
    
    async def fetch_feed(self, source: Dict) -> List[Dict]:
        """
        Fetch articles from a single RSS feed
        
        Args:
            source: Dictionary with 'name', 'url', and optional 'category'
            
        Returns:
            List of article dictionaries
        """
        logger.info(f"📰 Fetching news from {source['name']}...")
        articles = []
        
        try:
            # Fetch feed content
            content = await self._fetch_with_retry(source['url'])
            if not content:
                return articles
            
            # Parse with feedparser
            feed = feedparser.parse(content)
            
            if not feed.entries:
                logger.warning(f"No entries found in feed: {source['name']}")
                return articles
            
            source_category = source.get('category', [])
            
            for entry in feed.entries:
                try:
                    # Extract basic info
                    title = entry.get('title', 'Untitled')
                    url = entry.get('link', '')
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # Clean summary (remove HTML tags)
                    if summary:
                        soup = BeautifulSoup(summary, 'html.parser')
                        summary = soup.get_text(strip=True)[:500]  # Limit to 500 chars
                    
                    # Extract metadata
                    author = entry.get('author', '')
                    image_url = self._extract_image_from_entry(entry)
                    tags = self._extract_tags_from_entry(entry)
                    published_at = self._parse_publish_date(entry)
                    
                    article = {
                        "title": title,
                        "summary": summary,
                        "external_url": url,
                        "image_url": image_url,
                        "author": author,
                        "source_name": source['name'],
                        "published_at": published_at or datetime.now().isoformat(),
                        "category": source_category,
                        "tags": tags,
                    }
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse entry from {source['name']}: {e}")
                    continue
            
            logger.info(f"✓ Found {len(articles)} articles from {source['name']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch feed {source['name']}: {e}")
        
        return articles
    
    async def aggregate_all_sources(self) -> List[Dict]:
        """
        Fetch articles from all sources concurrently
        
        Returns:
            Combined list of articles from all sources
        """
        logger.info(f"📰 Aggregating news from {len(self.sources)} sources...")
        
        # Fetch all feeds concurrently
        tasks = [self.fetch_feed(source) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Feed fetch failed: {result}")
        
        logger.info(f"✅ Total articles found: {len(all_articles)}")
        return all_articles
    
    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles by URL
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Deduplicated list of articles
        """
        seen_urls = set()
        unique_articles = []
        
        for article in articles:
            url = article.get('external_url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        duplicates_removed = len(articles) - len(unique_articles)
        if duplicates_removed > 0:
            logger.info(f"🗑️ Removed {duplicates_removed} duplicate articles")
        
        return unique_articles
    
    async def fetch_and_deduplicate(self) -> List[Dict]:
        """
        Fetch articles from all sources and deduplicate
        
        Returns:
            Deduplicated list of articles
        """
        articles = await self.aggregate_all_sources()
        return self.deduplicate_articles(articles)


# Convenience function
async def aggregate_news(sources: Optional[List[Dict]] = None) -> List[Dict]:
    """Convenience function to aggregate news from all sources"""
    aggregator = NewsAggregator(sources)
    return await aggregator.fetch_and_deduplicate()


if __name__ == "__main__":
    # Test the aggregator
    async def test():
        articles = await aggregate_news()
        print(f"\n✅ Found {len(articles)} unique articles")
        if articles:
            print(f"\nFirst article:")
            print(f"  Title: {articles[0]['title']}")
            print(f"  Source: {articles[0]['source_name']}")
            print(f"  URL: {articles[0]['external_url']}")
    
    asyncio.run(test())
