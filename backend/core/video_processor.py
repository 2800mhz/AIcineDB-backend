"""
Video Processor - YouTube & Vimeo Support
Downloads and processes videos from multiple platforms
"""
import os
import re
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not available")


class VideoProcessor:
    """Handles video download and processing from YouTube, Vimeo, and other platforms"""
    
    # Supported platforms
    SUPPORTED_PLATFORMS = ['youtube', 'vimeo', 'dailymotion', 'twitter', 'facebook']
    
    def __init__(self, output_dir: str = "/app/data"):
        self.output_dir = Path(output_dir)
        self.videos_dir = self.output_dir / "videos"
        self.frames_dir = self.output_dir / "frames"
        self.audio_dir = self.output_dir / "audio"
        
        # Create directories
        for directory in [self.videos_dir, self.frames_dir, self.audio_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def detect_platform(self, url: str) -> str:
        """
        Detect video platform from URL
        
        Args:
            url: Video URL
            
        Returns:
            Platform name (youtube, vimeo, etc.)
        """
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'dailymotion.com' in url_lower:
            return 'dailymotion'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
            return 'facebook'
        else:
            return 'unknown'
    
    def get_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from URL
        
        Args:
            url: Video URL
            
        Returns:
            Video ID or None
        """
        platform = self.detect_platform(url)
        
        if platform == 'youtube':
            # YouTube patterns
            patterns = [
                r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
                    
        elif platform == 'vimeo':
            # Vimeo patterns
            patterns = [
                r'vimeo\.com/(\d+)',
                r'vimeo\.com/video/(\d+)',
                r'player\.vimeo\.com/video/(\d+)',
                r'vimeo\.com/channels/[^/]+/(\d+)',
                r'vimeo\.com/groups/[^/]+/videos/(\d+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
        
        return None
    
    def get_platform_options(self, platform: str) -> Dict:
        base_opts = {
            'format': 'best',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,
            'ignoreerrors': False,
            # 'cookiefile': yol, # Burası sadece Vimeo için eklenecek!
        }

        if platform == 'youtube':
            base_opts.update({
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
            })

        elif platform == 'vimeo':
            base_opts.update({
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://vimeo.com/',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Origin': 'https://vimeo.com',
                },
                'cookiefile': r'C:\Users\gcmsx\Desktop\AIcineDB\AIcineDB-backend\backend\cookies\vimeo_cookies.txt',
                # 'cookiesfrombrowser': ('chrome',),  # BUNU TAMAMEN KALDIR!!!
            })
        return base_opts
    def download_video(self, url: str, video_id: str) -> Dict:
        """
        Download video from URL (YouTube, Vimeo, etc.)
        
        Args:
            url: Video URL (YouTube, Vimeo, etc.)
            video_id: Unique identifier for the video
            
        Returns:
            Dict with video info and file paths
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        # Detect platform
        platform = self.detect_platform(url)
        logger.info(f"📥 Downloading {platform.upper()} video from: {url}")
        
        output_template = str(self.videos_dir / f"{video_id}.%(ext)s")
        
        # Get platform-specific options
        ydl_opts = self.get_platform_options(platform)
        ydl_opts['outtmpl'] = output_template
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                video_path = ydl.prepare_filename(info)
                
                # Get thumbnail URL based on platform
                thumbnail = self._get_thumbnail_url(url, info, platform)
                
                result = {
                    'video_path': video_path,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': thumbnail,
                    'description': info.get('description', ''),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'fps': info.get('fps', 30),
                    'platform': platform,
                    'platform_id': self.get_video_id(url),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'upload_date': info.get('upload_date'),
                }
                
                logger.info(f"✅ Downloaded [{platform.upper()}]: {result['title']} ({result['duration']}s)")
                return result
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"❌ Download failed [{platform}]: {error_msg}")
            
            # Platform-specific error handling
            if platform == 'vimeo':
                if 'private' in error_msg.lower():
                    raise Exception(f"This Vimeo video is private. Please check if you have access.")
                elif 'password' in error_msg.lower():
                    raise Exception(f"This Vimeo video is password protected.")
            elif platform == 'youtube':
                if '403' in error_msg:
                    raise Exception(f"YouTube blocked the request. Try again later.")
                elif 'unavailable' in error_msg.lower():
                    raise Exception(f"This YouTube video is unavailable.")
            
            raise Exception(f"Failed to download video: {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading video: {e}")
            raise
    
    def _get_thumbnail_url(self, url: str, info: Dict, platform: str) -> Optional[str]:
        """
        Get thumbnail URL for video
        
        Args:
            url: Original video URL
            info: Video info from yt-dlp
            platform: Platform name
            
        Returns:
            Thumbnail URL or None
        """
        # First try to get from yt-dlp info
        if info.get('thumbnail'):
            return info['thumbnail']
        
        # Platform-specific thumbnail extraction
        if platform == 'youtube':
            video_id = self.get_video_id(url)
            if video_id:
                return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
        elif platform == 'vimeo':
            video_id = self.get_video_id(url)
            if video_id:
                # Vimeo thumbnail requires API call, use yt-dlp info
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    # Get highest quality thumbnail
                    best_thumb = max(thumbnails, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    return best_thumb.get('url')
        
        return None
    
    def get_video_info(self, url: str) -> Dict:
        """
        Get video info without downloading
        
        Args:
            url: Video URL
            
        Returns:
            Dict with video metadata
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        platform = self.detect_platform(url)
        ydl_opts = self.get_platform_options(platform)
        ydl_opts['skip_download'] = True
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': self._get_thumbnail_url(url, info, platform),
                    'description': info.get('description', ''),
                    'platform': platform,
                    'platform_id': self.get_video_id(url),
                    'is_available': True,
                }
                
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {
                'is_available': False,
                'error': str(e),
                'platform': platform,
            }