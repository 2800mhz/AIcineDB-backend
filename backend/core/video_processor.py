"""
Video Processor - Multi-Platform Support (YouTube, Vimeo, etc.)
Downloads and processes videos with frame/audio extraction
"""
import os
import re
import logging
import subprocess
import cv2
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
    """Handles video download and processing from multiple platforms"""
    
    # Supported platforms
    SUPPORTED_PLATFORMS = ['youtube', 'vimeo', 'dailymotion', 'twitter', 'facebook']
    
    def __init__(self, output_dir: str = "/app/data"):
        self.output_dir = Path(output_dir)
        self.videos_dir = self.output_dir / "videos"
        self. frames_dir = self.output_dir / "frames"
        self.audio_dir = self.output_dir / "audio"
        
        # Create directories
        for directory in [self.videos_dir, self.frames_dir, self. audio_dir]:
            directory. mkdir(parents=True, exist_ok=True)
    
    # ============================================================
    # PLATFORM DETECTION
    # ============================================================
    
    def detect_platform(self, url: str) -> str:
        """Detect video platform from URL"""
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
    
    def get_platform_options(self, platform: str) -> Dict:
        """Get platform-specific yt-dlp options"""
        base_opts = {
            'format': 'best[height<=720]',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks
            'ignoreerrors': False,
        }
        
        if platform == 'youtube':
            base_opts. update({
                'user_agent': 'Mozilla/5. 0 (Windows NT 10. 0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://www. youtube.com/',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537. 36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
            })
        
        elif platform == 'vimeo':
            # Vimeo için cookie dosyası yolu (varsa)
            cookie_file = Path(__file__).parent. parent / 'cookies' / 'vimeo_cookies.txt'
            
            base_opts.update({
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537. 36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'referer': 'https://vimeo.com/',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537. 36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Origin': 'https://vimeo.com',
                },
            })
            
            # Cookie dosyası varsa ekle
            if cookie_file. exists():
                base_opts['cookiefile'] = str(cookie_file)
                logger.info(f"📝 Using Vimeo cookies from: {cookie_file}")
        
        return base_opts
    
    # ============================================================
    # VIDEO DOWNLOAD (ESKİ + YENİ HİBRİT)
    # ============================================================
    
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
        logger.info(f"📥 Downloading {platform. upper()} video from: {url}")
        
        output_template = str(self.videos_dir / f"{video_id}.%(ext)s")
        
        # Get platform-specific options
        ydl_opts = self.get_platform_options(platform)
        ydl_opts['outtmpl'] = output_template
        
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
                    'description': info. get('description', ''),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'fps': info.get('fps', 30),
                    'platform': platform,
                    'view_count': info.get('view_count', 0),
                    'like_count': info. get('like_count', 0),
                    'upload_date': info.get('upload_date'),
                }
                
                logger.info(f"✅ Downloaded [{platform.upper()}]: {result['title']} ({result['duration']}s)")
                return result
                
        except yt_dlp.utils. DownloadError as e:
            error_msg = str(e)
            logger.error(f"❌ Download failed [{platform}]: {error_msg}")
            
            # Platform-specific error handling
            if platform == 'vimeo':
                if 'private' in error_msg. lower():
                    raise Exception(f"This Vimeo video is private. Please check if you have access.")
                elif 'password' in error_msg.lower():
                    raise Exception(f"This Vimeo video is password protected.")
            elif platform == 'youtube':
                if '403' in error_msg or 'Forbidden' in error_msg:
                    logger.error(f"   YouTube blocked the request (403 Forbidden)")
                    logger.error(f"   Try: pip install --upgrade yt-dlp")
                    raise Exception("YouTube blocked the download (403 Forbidden).  Please update yt-dlp.")
                elif 'unavailable' in error_msg.lower():
                    raise Exception(f"This YouTube video is unavailable.")
            
            raise Exception(f"Failed to download video: {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error downloading video: {e}")
            raise
    
    # ============================================================
    # FRAME EXTRACTION (ESKİ ÇALIŞAN KOD - DEĞİŞMEDİ)
    # ============================================================
    
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
        duration = total_frames / video_fps if video_fps > 0 else 0
        
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
    
    # ============================================================
    # AUDIO EXTRACTION (ESKİ ÇALIŞAN KOD - DEĞİŞMEDİ)
    # ============================================================
    
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
            subprocess. run(cmd, check=True, capture_output=True)
            logger.info(f"✅ Audio extracted to: {audio_path}")
            return str(audio_path)
        except subprocess. CalledProcessError as e:
            logger.error(f"❌ Audio extraction failed: {e}")
            raise
    
    # ============================================================
    # VIDEO INFO (ESKİ ÇALIŞAN KOD - DEĞİŞMEDİ)
    # ============================================================
    
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
    
    # ============================================================
    # CLEANUP (ESKİ ÇALIŞAN KOD - DEĞİŞMEDİ)
    # ============================================================
    
    def cleanup(self, video_id: str):
        """Clean up files for a video"""
        import shutil
        
        # Remove video
        for ext in ['mp4', 'webm', 'mkv']:
            video_file = self. videos_dir / f"{video_id}.{ext}"
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