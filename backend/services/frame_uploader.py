"""
Frame Uploader Service
Uploads extracted keyframes to Supabase Storage
"""
import os
from pathlib import Path
from typing import List, Dict
from supabase import create_client
import logging

logger = logging.getLogger(__name__)


class FrameUploader:
    """Upload keyframes to Supabase Storage"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not configured")
        
        self.supabase = create_client(supabase_url, supabase_key)
        logger.info("✓ Frame uploader initialized")
    
    async def upload_keyframes(
        self,
        keyframes_dir: str,
        title_id: str
    ) -> List[Dict]:
        """
        Upload all keyframes from directory to Supabase
        
        Args:
            keyframes_dir: Path to keyframes directory
            title_id: UUID of the title in Supabase
            
        Returns:
            List of uploaded frame metadata
        """
        keyframes_path = Path(keyframes_dir)
        
        if not keyframes_path.exists():
            logger.warning(f"Keyframes directory not found: {keyframes_dir}")
            return []
        
        # Get all . jpg files
        keyframe_files = sorted(keyframes_path.glob("shot_*. jpg"))
        
        if not keyframe_files:
            logger.warning("No keyframes found")
            return []
        
        logger.info(f"📤 Uploading {len(keyframe_files)} keyframes to Supabase...")
        
        uploaded_frames = []
        
        for idx, keyframe_path in enumerate(keyframe_files, 1):
            try:
                # Read file
                with open(keyframe_path, 'rb') as f:
                    file_data = f.read()
                
                # Storage path: title-frames/{title_id}/shot_{idx:04d}.jpg
                storage_path = f"{title_id}/shot_{idx:04d}.jpg"
                
                # Upload to Supabase Storage
                self.supabase.storage.from_('title-frames').upload(
                    storage_path,
                    file_data,
                    {
                        'content-type': 'image/jpeg',
                        'cache-control': '3600',
                        'upsert': 'true'  # Overwrite if exists
                    }
                )
                
                # Get public URL
                frame_url = self.supabase.storage.from_('title-frames').get_public_url(storage_path)
                
                # Extract timestamp from filename (if available)
                # shot_0001.jpg → frame 1
                timestamp = self._estimate_timestamp(idx, len(keyframe_files))
                
                # Save to database
                self. supabase.table('title_frames').insert({
                    'title_id': title_id,
                    'frame_url': frame_url,
                    'frame_number': idx,
                    'timestamp': timestamp
                }).execute()
                
                uploaded_frames.append({
                    'frame_number': idx,
                    'frame_url': frame_url,
                    'timestamp': timestamp,
                    'local_path': str(keyframe_path)
                })
                
                logger.info(f"   ✅ Uploaded frame {idx}/{len(keyframe_files)}")
                
            except Exception as e:
                logger.error(f"   ❌ Failed to upload frame {idx}: {e}")
                continue
        
        logger.info(f"🎉 Uploaded {len(uploaded_frames)}/{len(keyframe_files)} frames")
        
        return uploaded_frames
    
    def _estimate_timestamp(self, frame_number: int, total_frames: int, total_duration: float = None) -> str:
        """
        Estimate timestamp for frame
        
        Args:
            frame_number: Frame number (1-based)
            total_frames: Total number of frames
            total_duration: Total video duration in seconds (optional)
            
        Returns:
            Timestamp string "MM:SS"
        """
        if total_duration:
            timestamp_sec = (frame_number / total_frames) * total_duration
        else:
            # Fallback: assume evenly spaced
            timestamp_sec = frame_number * 10  # Rough estimate
        
        minutes = int(timestamp_sec // 60)
        seconds = int(timestamp_sec % 60)
        
        return f"{minutes:02d}:{seconds:02d}"