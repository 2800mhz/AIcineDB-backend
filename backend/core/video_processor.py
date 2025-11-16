"""
Video Processing Module
Downloads, extracts frames and audio from videos
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
    
    def download_video(self, url: str, video_id: str) -> Dict:
        """
        Download video from URL
        
        Args:
            url: Video URL (YouTube, etc.)
            video_id: Unique identifier for the video
            
        Returns:
            Dict with video info and file paths
        """
        if not YT_DLP_AVAILABLE:
            raise ImportError("yt-dlp is not installed")
        
        logger.info(f"📥 Downloading video from: {url}")
        
        output_template = str(self.videos_dir / f"{video_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'best[height<=720]',  # Max 720p to save space
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
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
                }
                
                logger.info(f"✅ Downloaded: {result['title']} ({result['duration']}s)")
                return result
                
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
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
        
        # Use ffmpeg via opencv
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