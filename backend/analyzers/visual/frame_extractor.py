"""
Frame Extractor - Extracts key frames from videos for analysis and storage
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import cv2

logger = logging.getLogger(__name__)


class FrameExtractor:
    """
    Extracts key frames from videos at regular intervals.
    Saves frames to a specified directory with metadata.
    """
    
    def __init__(self, default_interval: float = 10.0, default_max_frames: int = 20):
        """
        Initialize frame extractor.
        
        Args:
            default_interval: Default interval between frames in seconds
            default_max_frames: Default maximum number of frames to extract
        """
        self.default_interval = default_interval
        self.default_max_frames = default_max_frames
        logger.info("✓ Frame extractor initialized")
    
    async def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        interval_seconds: float = None,
        max_frames: int = None,
        generate_thumbnails: bool = True,
        thumbnail_size: tuple = (320, 180)
    ) -> List[Dict]:
        """
        Extract key frames from video at regular intervals.
        
        Args:
            video_path: Path to the video file
            output_dir: Directory to save extracted frames
            interval_seconds: Interval between frames (default: 10 seconds)
            max_frames: Maximum number of frames to extract (default: 20)
            generate_thumbnails: Whether to generate thumbnail versions
            thumbnail_size: Size of thumbnails (width, height)
            
        Returns:
            List of frame metadata dictionaries containing:
            - frame_number: Sequential frame number
            - timestamp: Time in video (seconds)
            - path: Full path to saved frame
            - thumbnail_path: Path to thumbnail (if generated)
            - width: Frame width
            - height: Frame height
        """
        interval = interval_seconds or self.default_interval
        max_count = max_frames or self.default_max_frames
        
        if not video_path or not os.path.exists(video_path):
            logger.warning(f"Video path not found: {video_path}")
            return []
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Create thumbnails subdirectory if needed
        if generate_thumbnails:
            thumbs_dir = output_path / "thumbnails"
            thumbs_dir.mkdir(parents=True, exist_ok=True)
        
        frames = []
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                logger.error(f"Failed to open video: {video_path}")
                return []
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"📸 Video: {duration:.1f}s, {fps:.1f} FPS, {total_frames} frames")
            
            # Calculate frame positions
            # Use interval but respect max_frames limit
            if duration <= 0:
                logger.warning("Video duration is 0, cannot extract frames")
                cap.release()
                return []
            
            # Calculate optimal interval to get desired number of frames
            optimal_interval = max(interval, duration / max_count)
            
            # Generate timestamps
            timestamps = []
            current_time = 0
            while current_time < duration and len(timestamps) < max_count:
                timestamps.append(current_time)
                current_time += optimal_interval
            
            logger.info(f"📸 Extracting {len(timestamps)} frames at {optimal_interval:.1f}s intervals")
            
            # Extract frames
            for idx, timestamp in enumerate(timestamps):
                frame_number = idx + 1
                frame_position = int(timestamp * fps)
                
                # Seek to position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
                ret, frame = cap.read()
                
                if not ret:
                    logger.warning(f"Failed to read frame at {timestamp:.1f}s")
                    continue
                
                # Get dimensions
                height, width = frame.shape[:2]
                
                # Save full frame
                frame_filename = f"frame_{frame_number:04d}.jpg"
                frame_path = output_path / frame_filename
                cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                
                frame_data = {
                    'frame_number': frame_number,
                    'timestamp': timestamp,
                    'path': str(frame_path),
                    'width': width,
                    'height': height,
                }
                
                # Generate thumbnail
                if generate_thumbnails:
                    thumb_filename = f"thumb_{frame_number:04d}.jpg"
                    thumb_path = thumbs_dir / thumb_filename
                    
                    # Resize for thumbnail
                    thumb = cv2.resize(frame, thumbnail_size, interpolation=cv2.INTER_AREA)
                    cv2.imwrite(str(thumb_path), thumb, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    
                    frame_data['thumbnail_path'] = str(thumb_path)
                
                frames.append(frame_data)
            
            cap.release()
            
            logger.info(f"✓ Extracted {len(frames)} frames to {output_dir}")
            
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return []
        
        return frames
    
    def extract_single_frame(
        self,
        video_path: str,
        timestamp: float,
        output_path: str
    ) -> Optional[Dict]:
        """
        Extract a single frame at a specific timestamp.
        
        Args:
            video_path: Path to video file
            timestamp: Time in seconds
            output_path: Path to save the frame
            
        Returns:
            Frame metadata dict or None if failed
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return None
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_position = int(timestamp * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_position)
            ret, frame = cap.read()
            
            if not ret:
                cap.release()
                return None
            
            height, width = frame.shape[:2]
            
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(output_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            cap.release()
            
            return {
                'timestamp': timestamp,
                'path': output_path,
                'width': width,
                'height': height
            }
            
        except Exception as e:
            logger.error(f"Single frame extraction failed: {e}")
            return None
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get basic video information.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dict with video info (duration, fps, dimensions, frame_count)
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                return {}
            
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'duration': duration,
                'fps': fps,
                'width': width,
                'height': height,
                'frame_count': frame_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
