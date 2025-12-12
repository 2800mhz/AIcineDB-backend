"""
Tweet Video Service
Extracts tweet metadata and handles X/Twitter video downloads
"""
import os
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not available")


class TweetVideoService:
    """Handles X/Twitter video downloads and metadata extraction"""
    
    @staticmethod
    def is_twitter_url(url: str) -> bool:
        """
        Check if URL is from X/Twitter
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is from X or Twitter
        """
        # Match both x.com and twitter.com
        twitter_pattern = r'https?://(www\.)?(x\.com|twitter\.com)/.+/status/\d+'
        return bool(re.match(twitter_pattern, url))
    
    @staticmethod
    def sanitize_tweet_text(text: str) -> str:
        """
        Sanitize tweet text for Gemini processing
        Remove URLs, @mentions that aren't relevant
        
        Args:
            text: Raw tweet text
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove @mentions (but keep the text after)
        text = re.sub(r'@\w+', '', text)
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_tweet_metadata(self, url: str) -> Dict:
        """
        Extract tweet metadata including text content
        Uses yt-dlp's info extraction without downloading
        
        Args:
            url: X/Twitter URL
            
        Returns:
            Dict with tweet metadata
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        if not self.is_twitter_url(url):
            raise ValueError(f"Not a valid X/Twitter URL: {url}")
        
        logger.info(f"📱 Extracting tweet metadata from: {url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Add headers for Twitter
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract tweet text from description or title
                tweet_text = info.get('description', '')
                if not tweet_text:
                    # Fallback to title if description is empty
                    tweet_text = info.get('title', '')
                
                # Get author info
                author = info.get('uploader', 'Unknown')
                author_id = info.get('uploader_id', '')
                
                # Get timestamps
                upload_date = info.get('upload_date', '')
                timestamp = info.get('timestamp', 0)
                
                # Sanitize tweet text for analysis
                sanitized_text = self.sanitize_tweet_text(tweet_text)
                
                result = {
                    'tweet_text': tweet_text,
                    'sanitized_text': sanitized_text,
                    'author': author,
                    'author_id': author_id,
                    'upload_date': upload_date,
                    'timestamp': timestamp,
                    'url': url,
                    'has_video': info.get('ext') in ['mp4', 'webm', 'mov'],
                }
                
                logger.info(f"✅ Tweet metadata extracted from @{author}")
                logger.info(f"   Tweet text preview: {sanitized_text[:100]}...")
                
                return result
                
        except Exception as e:
            logger.error(f"❌ Failed to extract tweet metadata: {e}")
            # Return minimal metadata to allow processing to continue
            return {
                'tweet_text': '',
                'sanitized_text': '',
                'author': 'Unknown',
                'author_id': '',
                'upload_date': '',
                'timestamp': 0,
                'url': url,
                'has_video': False,
                'error': str(e)
            }
    
    def extract_with_download_info(self, url: str) -> Dict:
        """
        Extract tweet metadata along with video download information
        This is used when we want both metadata and video details
        
        Args:
            url: X/Twitter URL
            
        Returns:
            Dict with tweet metadata and video info
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        logger.info(f"📱 Extracting full tweet info from: {url}")
        
        # Note: Using quiet=True for consistency with extract_tweet_metadata
        # Verbose mode can be enabled for debugging if needed
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract tweet metadata
                tweet_text = info.get('description', '')
                if not tweet_text:
                    tweet_text = info.get('title', '')
                
                sanitized_text = self.sanitize_tweet_text(tweet_text)
                
                # Extract video information
                result = {
                    # Tweet metadata
                    'tweet_text': tweet_text,
                    'sanitized_text': sanitized_text,
                    'author': info.get('uploader', 'Unknown'),
                    'author_id': info.get('uploader_id', ''),
                    'upload_date': info.get('upload_date', ''),
                    'timestamp': info.get('timestamp', 0),
                    
                    # Video metadata
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'fps': info.get('fps', 30),
                    'ext': info.get('ext', 'mp4'),
                    
                    # Platform info
                    'platform': 'twitter',
                    'url': url,
                }
                
                logger.info(f"✅ Full tweet info extracted: {result['title']}")
                
                return result
                
        except Exception as e:
            logger.error(f"❌ Failed to extract full tweet info: {e}")
            raise
