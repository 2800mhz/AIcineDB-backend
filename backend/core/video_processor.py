"""
Video Processing Module - FIXED for 403 Errors
Downloads, extracts frames and audio from videos
Supports YouTube, Vimeo, X/Twitter, and other platforms
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional
import cv2

logger = logging.getLogger(__name__)

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logger.warning("yt-dlp not available")

# Import Twitter service
try:
    from backend.services.tweet_video_service import TweetVideoService
    TWITTER_SERVICE_AVAILABLE = True
except ImportError:
    TWITTER_SERVICE_AVAILABLE = False
    logger.warning("Tweet video service not available")


class VideoProcessor:
    """Handles video download and processing"""
    
    def __init__(self, output_dir: str = "/app/data"):
        self.output_dir = Path(output_dir)
        self.videos_dir = self.output_dir / "videos"
        self.frames_dir = self.output_dir / "frames"
        self.audio_dir = self.output_dir / "audio"
        
        # Create directories
        for directory in [self.videos_dir, self.frames_dir, self.audio_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize Twitter service if available
        self.twitter_service = TweetVideoService() if TWITTER_SERVICE_AVAILABLE else None
    
    def _detect_platform(self, url: str) -> str:
        """
        Detect the platform from URL for download strategy selection
        
        Args:
            url: Video URL
            
        Returns:
            Platform name: 'twitter', 'youtube', 'vimeo', or 'other'
            
        Security Note:
            This is used only for selecting the appropriate download strategy,
            not for URL validation or sanitization. The actual URL validation
            and security is handled by yt-dlp during download. The substring
            checks here are for platform identification only.
            
        Implementation Note:
            Twitter uses regex validation (via TweetVideoService.is_twitter_url)
            for precise pattern matching of status URLs. YouTube/Vimeo use
            simple substring checks as they have more varied URL formats and
            yt-dlp handles all variations. This mixed approach is intentional
            for optimal balance of precision and simplicity.
        """
        url_lower = url.lower()
        
        # Check for Twitter/X (uses regex pattern for proper validation)
        if self.twitter_service and self.twitter_service.is_twitter_url(url):
            return 'twitter'
        
        # Check for YouTube (substring check is safe here - only for platform identification)
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        
        # Check for Vimeo (substring check is safe here - only for platform identification)
        if 'vimeo.com' in url_lower:
            return 'vimeo'
        
        return 'other'
    
    def download_video(self, url: str, video_id: str) -> Dict:
        """
        Download video from URL with enhanced error handling
        
        Args:
            url: Video URL (YouTube, Twitter, Vimeo, etc.)
            video_id: Unique identifier for the video
            
        Returns:
            Dict with video info and file paths, including:
            - platform: str ('twitter', 'youtube', 'vimeo', 'other')
            - tweet_text: str (only for Twitter)
            - tweet_metadata: dict (only for Twitter)
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        # Detect platform
        platform = self._detect_platform(url)
        logger.info(f"📥 Downloading video from {platform}: {url}")
        
        # For Twitter, extract tweet metadata first
        tweet_metadata = None
        tweet_text = None
        
        if platform == 'twitter' and self.twitter_service:
            try:
                tweet_metadata = self.twitter_service.extract_tweet_metadata(url)
                tweet_text = tweet_metadata.get('sanitized_text', '')
                logger.info(f"📱 Extracted tweet text: {tweet_text[:100]}...")
            except Exception as e:
                logger.warning(f"⚠️ Could not extract tweet metadata: {e}")
                tweet_text = ""
                tweet_metadata = {}
        
        output_template = str(self.videos_dir / f"{video_id}.%(ext)s")
        
        # FIXED: Enhanced ydl_opts to handle 403 errors
        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            
            # Add user agent to avoid bot detection
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Add referer
            'referer': 'https://www.youtube.com/',
            
            # Retry settings
            'retries': 10,
            'fragment_retries': 10,
            
            # Network settings
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks
            
            # Ignore errors on unavailable fragments
            'ignoreerrors': False,
            
            # Add headers to bypass restrictions
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                video_path = ydl.prepare_filename(info)
                
                result = {
                    'video_path': video_path,
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'thumbnail': info.get('thumbnail'),
                    'description': info.get('description', ''),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'fps': info.get('fps', 30),
                    'platform': platform,
                }
                
                # Add Twitter-specific metadata
                if platform == 'twitter':
                    result['tweet_text'] = tweet_text or ''
                    result['tweet_metadata'] = tweet_metadata or {}
                
                logger.info(f"✅ Downloaded: {result['title']} ({result['duration']}s)")
                return result
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            
            if "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
                logger.error(f"❌ Video host blocked the request (403 Forbidden)")
                logger.error(f"   This usually means:")
                logger.error(f"   1. yt-dlp needs an update: pip install --upgrade yt-dlp")
                logger.error(f"   2. Video has geo-restrictions or requires login")
                logger.error(f"   3. Bot detection triggered")
                
                raise Exception(
                    "Video download blocked (403 Forbidden). "
                    "Please update yt-dlp: pip install --upgrade yt-dlp"
                )
            
            elif "unavailable" in error_msg.lower():
                logger.error(f"❌ Video is unavailable or private")
                raise Exception(f"Video unavailable: {error_msg}")
            
            else:
                logger.error(f"❌ Download failed: {error_msg}")
                raise Exception(f"Download failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"❌ Unexpected error during download: {e}")
            raise
    
    def extract_frames(
        self, 
        video_path: str, 
        video_id: str,
        fps: float = 1.0,
        max_frames: int = 300
    ) -> Dict:
        """
        Extract frames from video
        
        Args:
            video_path: Path to video file
            video_id: Unique identifier
            fps: Frames per second to extract (1 = 1 frame/sec)
            max_frames: Maximum number of frames to extract
            
        Returns:
            Dict with frame paths and info
        """
        logger.info(f"🎞️ Extracting frames at {fps} FPS...")
        
        frames_output_dir = self.frames_dir / video_id
        frames_output_dir.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps
        
        # Calculate frame interval
        frame_interval = int(video_fps / fps)
        
        extracted_frames = []
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Extract every Nth frame
            if frame_count % frame_interval == 0:
                frame_path = frames_output_dir / f"frame_{saved_count:05d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                
                extracted_frames.append({
                    'path': str(frame_path),
                    'frame_number': frame_count,
                    'timestamp': frame_count / video_fps
                })
                
                saved_count += 1
                
                if saved_count >= max_frames:
                    logger.warning(f"⚠️ Reached max frames limit ({max_frames})")
                    break
            
            frame_count += 1
        
        cap.release()
        
        logger.info(f"✅ Extracted {saved_count} frames from {total_frames} total frames")
        
        return {
            'frames': extracted_frames,
            'total_extracted': saved_count,
            'total_frames': total_frames,
            'duration': duration,
            'video_fps': video_fps,
            'extraction_fps': fps,
            'output_dir': str(frames_output_dir)
        }
    
    def extract_audio(self, video_path: str, video_id: str) -> str:
        """
        Extract audio from video
        
        Args:
            video_path: Path to video file
            video_id: Unique identifier
            
        Returns:
            Path to extracted audio file
        """
        logger.info("🎵 Extracting audio...")
        
        audio_path = self.audio_dir / f"{video_id}.wav"
        
        # Use ffmpeg via subprocess
        import subprocess
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', '16000',  # 16kHz sample rate (good for Whisper)
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"✅ Audio extracted to: {audio_path}")
            return str(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Audio extraction failed: {e}")
            raise
    
    def get_video_info(self, video_path: str) -> Dict:
        """Get basic video information"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'fps': fps,
            'frame_count': frame_count,
            'width': width,
            'height': height,
            'duration': duration
        }
    
    def cleanup(self, video_id: str):
        """Clean up files for a video"""
        import shutil
        
        # Remove video
        for ext in ['mp4', 'webm', 'mkv']:
            video_file = self.videos_dir / f"{video_id}.{ext}"
            if video_file.exists():
                video_file.unlink()
        
        # Remove frames
        frames_dir = self.frames_dir / video_id
        if frames_dir.exists():
            shutil.rmtree(frames_dir)
        
        # Remove audio
        audio_file = self.audio_dir / f"{video_id}.wav"
        if audio_file.exists():
            audio_file.unlink()
        
        logger.info(f"🗑️ Cleaned up files for video {video_id}")