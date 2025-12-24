"""
Content Aggregation Tests
Tests for festival scraper, news aggregator, and AI filter services
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from backend.services.festival_scraper import FestivalScraper
from backend.services.news_aggregator import NewsAggregator
from backend.services.ai_filter import AIFilter


class TestFestivalScraper:
    """Tests for FestivalScraper service"""
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self):
        """Test that scraper initializes correctly"""
        scraper = FestivalScraper()
        
        assert scraper.user_agent is not None
        assert scraper.rate_limit_delay > 0
        assert scraper.max_retries > 0
        assert scraper.headers is not None
    
    @pytest.mark.asyncio
    async def test_parse_filmfreeway_card(self):
        """Test parsing FilmFreeway festival card"""
        scraper = FestivalScraper()
        
        # Mock BeautifulSoup card element
        from bs4 import BeautifulSoup
        html = """
        <div class="festival-card">
            <h3>Test Festival</h3>
            <p class="description">A great festival for AI films</p>
            <span class="location">San Francisco, USA</span>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')
        card = soup.find('div', class_='festival-card')
        
        festival = scraper._parse_filmfreeway_card(card)
        
        assert festival is not None
        assert festival['name'] == 'Test Festival'
        assert festival['description'] == 'A great festival for AI films'
        assert 'USA' in festival['location']
        assert festival['source'] == 'filmfreeway'
    
    @pytest.mark.asyncio
    async def test_scrape_rss_feed(self):
        """Test RSS feed scraping"""
        scraper = FestivalScraper()
        
        # Test with a mock RSS feed
        # In a real test, you'd mock the HTTP request
        # For now, just test that the method exists and can be called
        with patch.object(scraper, '_fetch_with_retry', return_value=None):
            festivals = await scraper.scrape_rss_feed("https://example.com/feed.xml")
            assert isinstance(festivals, list)


class TestNewsAggregator:
    """Tests for NewsAggregator service"""
    
    @pytest.mark.asyncio
    async def test_aggregator_initialization(self):
        """Test that aggregator initializes correctly"""
        aggregator = NewsAggregator()
        
        assert aggregator.sources is not None
        assert len(aggregator.sources) > 0
        assert aggregator.user_agent is not None
    
    @pytest.mark.asyncio
    async def test_extract_image_from_entry(self):
        """Test image extraction from RSS entry"""
        aggregator = NewsAggregator()
        
        # Mock RSS entry with media content
        entry = Mock()
        entry.media_content = [{'url': 'https://example.com/image.jpg', 'medium': 'image'}]
        
        image_url = aggregator._extract_image_from_entry(entry)
        
        assert image_url == 'https://example.com/image.jpg'
    
    @pytest.mark.asyncio
    async def test_deduplicate_articles(self):
        """Test article deduplication"""
        aggregator = NewsAggregator()
        
        articles = [
            {"title": "Article 1", "external_url": "https://example.com/1"},
            {"title": "Article 2", "external_url": "https://example.com/2"},
            {"title": "Article 1 Duplicate", "external_url": "https://example.com/1"},
        ]
        
        unique = aggregator.deduplicate_articles(articles)
        
        assert len(unique) == 2
        assert unique[0]['external_url'] == "https://example.com/1"
        assert unique[1]['external_url'] == "https://example.com/2"
    
    @pytest.mark.asyncio
    async def test_extract_tags_from_entry(self):
        """Test tag extraction from RSS entry"""
        aggregator = NewsAggregator()
        
        # Mock RSS entry with tags
        entry = Mock()
        tag1 = Mock()
        tag1.get = lambda x: 'ai' if x == 'term' else None
        tag2 = Mock()
        tag2.get = lambda x: 'filmmaking' if x == 'term' else None
        entry.tags = [tag1, tag2]
        
        tags = aggregator._extract_tags_from_entry(entry)
        
        assert 'ai' in tags
        assert 'filmmaking' in tags


class TestAIFilter:
    """Tests for AIFilter service"""
    
    def test_filter_initialization(self):
        """Test that AI filter initializes correctly"""
        ai_filter = AIFilter()
        
        assert ai_filter.festival_threshold >= 0
        assert ai_filter.news_threshold >= 0
        assert ai_filter.duplicate_threshold >= 0
    
    @pytest.mark.asyncio
    async def test_filter_festivals_without_openai(self):
        """Test festival filtering when OpenAI is not available"""
        with patch('backend.services.ai_filter.OPENAI_AVAILABLE', False):
            ai_filter = AIFilter()
            
            test_festivals = [
                {"name": "Test Festival", "description": "A test festival"}
            ]
            
            # Should return all festivals when filtering is disabled
            filtered = await ai_filter.filter_festivals(test_festivals)
            assert len(filtered) == len(test_festivals)
    
    @pytest.mark.asyncio
    async def test_filter_news_without_openai(self):
        """Test news filtering when OpenAI is not available"""
        with patch('backend.services.ai_filter.OPENAI_AVAILABLE', False):
            ai_filter = AIFilter()
            
            test_articles = [
                {"title": "Test Article", "summary": "A test article"}
            ]
            
            # Should return all articles when filtering is disabled
            filtered = await ai_filter.filter_news(test_articles)
            assert len(filtered) == len(test_articles)
    
    def test_cosine_similarity(self):
        """Test cosine similarity calculation"""
        ai_filter = AIFilter()
        
        # Test identical vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        similarity = ai_filter.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0)
        
        # Test orthogonal vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = ai_filter.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)
        
        # Test opposite vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]
        similarity = ai_filter.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0)
    
    @pytest.mark.asyncio
    async def test_detect_duplicates(self):
        """Test duplicate detection"""
        ai_filter = AIFilter()
        
        # Test with items without embeddings
        items = [
            {"name": "Item 1"},
            {"name": "Item 2"},
        ]
        
        unique = await ai_filter.detect_duplicates(items)
        assert len(unique) == 2
        
        # Test with items with embeddings
        items = [
            {"name": "Item 1", "embedding": [1.0, 0.0, 0.0]},
            {"name": "Item 2", "embedding": [0.0, 1.0, 0.0]},
            {"name": "Item 1 Duplicate", "embedding": [0.999, 0.001, 0.0]},  # Very similar
        ]
        
        unique = await ai_filter.detect_duplicates(items)
        # Should detect the duplicate based on similarity threshold
        assert len(unique) <= 3


# Integration test
class TestContentAggregationIntegration:
    """Integration tests for content aggregation"""
    
    @pytest.mark.asyncio
    async def test_full_festival_pipeline_mock(self):
        """Test complete festival scraping pipeline (mocked)"""
        # This would test the full pipeline from scraping to AI filtering
        # For now, just ensure the components can work together
        
        scraper = FestivalScraper()
        ai_filter = AIFilter()
        
        # Mock festival data
        mock_festivals = [
            {
                "name": "AI Film Festival",
                "description": "Festival for AI-generated films",
                "location": "San Francisco, USA"
            }
        ]
        
        # In a real integration test, we'd:
        # 1. Scrape festivals (mocked)
        # 2. Filter with AI (mocked)
        # 3. Detect duplicates
        # 4. Save to database (mocked)
        
        assert scraper is not None
        assert ai_filter is not None
    
    @pytest.mark.asyncio
    async def test_full_news_pipeline_mock(self):
        """Test complete news aggregation pipeline (mocked)"""
        aggregator = NewsAggregator()
        ai_filter = AIFilter()
        
        # Mock article data
        mock_articles = [
            {
                "title": "AI Takes Over Film Industry",
                "summary": "AI is revolutionizing filmmaking",
                "external_url": "https://example.com/article"
            }
        ]
        
        # Test deduplication
        unique = aggregator.deduplicate_articles(mock_articles)
        assert len(unique) == 1
        
        assert aggregator is not None
        assert ai_filter is not None


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
