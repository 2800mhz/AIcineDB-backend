"""
Video Processing Module - FIXED for YouTube JS challenges
Downloads, extracts frames and audio from videos
Supports YouTube, Vimeo, X/Twitter, and other platforms
"""
import os
import logging
import subprocess
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
        self.posters_dir = self.output_dir / "posters"
        
        # Create directories
        for directory in [self.videos_dir, self.frames_dir, self.audio_dir, self.posters_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize Twitter service if available
        self.twitter_service = TweetVideoService() if TWITTER_SERVICE_AVAILABLE else None
        
        # ✅ Create yt-dlp config for remote components
        self._setup_ytdlp_config()
    
    def _setup_ytdlp_config(self):
        """Setup yt-dlp config file for remote components"""
        try:
            config_dir = Path("/root/.config/yt-dlp")
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config"
            
            # Write config with remote components enabled
            config_content = "--remote-components ejs:github\n"
            
            if not config_file.exists():
                config_file.write_text(config_content)
                logger.info("✅ Created yt-dlp config with remote components")
            else:
                # Check if remote components already in config
                existing = config_file.read_text()
                if "--remote-components" not in existing:
                    config_file.write_text(existing + config_content)
                    logger.info("✅ Updated yt-dlp config with remote components")
        except Exception as e:
            logger.warning(f"⚠️ Could not setup yt-dlp config: {e}")
    
    def _detect_platform(self, url: str) -> str:
        """
        Detect the platform from URL for download strategy selection
        """
        url_lower = url.lower()
        
        # Check for Twitter/X
        if self.twitter_service and self.twitter_service.is_twitter_url(url):
            return 'twitter'
        
        # Check for YouTube
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        
        # Check for Vimeo
        if 'vimeo.com' in url_lower:
            return 'vimeo'
        
        return 'other'
    
    def _extract_twitter_thumbnail(self, video_path: str, video_id: str) -> Optional[str]:
        """
        Extract first frame as thumbnail for Twitter videos
        """
        try:
            thumbnail_path = self.posters_dir / f"{video_id}_poster.jpg"
            
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-ss', '00:00:01',
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                str(thumbnail_path)
            ]
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if thumbnail_path.exists():
                logger.info(f"✅ Thumbnail extracted: {thumbnail_path}")
                return str(thumbnail_path)
            else:
                logger.warning(f"⚠️ Thumbnail file not created: {thumbnail_path}")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Thumbnail extraction failed: {e.stderr}")
            return None
        except Exception as e:
            logger.warning(f"⚠️ Unexpected error during thumbnail extraction: {e}")
            return None
    
    def _verify_video_has_video_stream(self, video_path: str) -> bool:
        """
        Verify that the downloaded file actually contains a video stream
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return 'video' in result.stdout.lower()
        except Exception as e:
            logger.warning(f"⚠️ Could not verify video stream: {e}")
            return False
    
    def download_video(self, url: str, video_id: str) -> Dict:
        """
        Download video from URL with enhanced error handling
        
        Args:
            url: Video URL (YouTube, Twitter, Vimeo, etc.)
            video_id: Unique identifier for the video
            
        Returns:
            Dict with video info and file paths
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
        
        # ✅ FIXED: Basitleştirilmiş format
        ydl_opts = {
            'format': '18',
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            
            # User agent
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            
            # Headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            
            # Retry settings
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,
            
            # Post-processors
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # ✅ Use info['ext'] directly (more reliable)
                downloaded_ext = info.get('ext', 'mp4')
                video_path = self.videos_dir / f"{video_id}.{downloaded_ext}"
                
                # Verify file exists
                if not video_path.exists():
                    # Debug: list all files
                    all_files = list(self.videos_dir.glob(f"{video_id}.*"))
                    logger.error(f"❌ Expected file not found: {video_path}")
                    logger.error(f"   Files in directory: {[f.name for f in all_files]}")
                    
                    # Fallback: use first matching file
                    if all_files:
                        video_path = all_files[0]
                        logger.warning(f"⚠️ Using fallback: {video_path}")
                    else:
                        raise ValueError(f"Video file not found: {video_id}")
                
                video_path = str(video_path)
                logger.info(f"✅ Downloaded: {info.get('title')} -> {video_path}")
                
                # Verify video stream exists
                if not self._verify_video_has_video_stream(video_path):
                    raise ValueError(f"Downloaded file has no video stream: {video_path}")
                
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
                    thumbnail_path = self._extract_twitter_thumbnail(video_path, video_id)
                    if thumbnail_path:
                        result['thumbnail_path'] = thumbnail_path
                
                return result
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            
            if "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
                logger.error(f"❌ Video host blocked the request (403 Forbidden)")
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
        logger.info(f"🎞️ Extracting frames at {fps} FPS from: {video_path}")
        
        # Verify video file exists
        if not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")
        
        # Verify video has video stream
        if not self._verify_video_has_video_stream(video_path):
            raise ValueError(f"File has no video stream: {video_path}")
        
        frames_output_dir = self.frames_dir / video_id
        frames_output_dir.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if video_fps <= 0:
            logger.warning(f"⚠️ Invalid FPS ({video_fps}), defaulting to 30")
            video_fps = 30
        
        duration = total_frames / video_fps if video_fps > 0 else 0
        
        # Calculate frame interval
        frame_interval = max(1, int(video_fps / fps))
        
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
        logger.info(f"🎵 Extracting audio from: {video_path}")
        
        # Verify video file exists
        if not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")
        
        audio_path = self.audio_dir / f"{video_id}.wav"
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            '-y',
            str(audio_path)
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"✅ Audio extracted to: {audio_path}")
            return str(audio_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Audio extraction failed: {e.stderr}")
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
        
        # Remove video files
        for ext in ['mp4', 'webm', 'mkv', 'm4a', 'mp3', 'wav']:
            video_file = self.videos_dir / f"{video_id}.{ext}"
            if video_file.exists():
                video_file.unlink()
                logger.info(f"🗑️ Deleted: {video_file}")
        
        # Remove frames directory
        frames_dir = self.frames_dir / video_id
        if frames_dir.exists():
            shutil.rmtree(frames_dir)
            logger.info(f"🗑️ Deleted frames: {frames_dir}")
        
        # Remove audio file
        audio_file = self.audio_dir / f"{video_id}.wav"
        if audio_file.exists():
            audio_file.unlink()
            logger.info(f"🗑️ Deleted audio: {audio_file}")
        
        # Remove poster/thumbnail
        poster_file = self.posters_dir / f"{video_id}_poster.jpg"
        if poster_file.exists():
            poster_file.unlink()
            logger.info(f"🗑️ Deleted poster: {poster_file}")
        
        logger.info(f"✅ Cleaned up all files for video {video_id}")