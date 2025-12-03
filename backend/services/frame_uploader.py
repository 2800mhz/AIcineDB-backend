"""
Frame Uploader Service - FIXED for Windows paths
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
        title_id: str,
        film_title: str = "Unknown"
    ) -> List[Dict]:
        """
        Upload all keyframes from directory to Supabase
        
        Args:
            keyframes_dir: Path to keyframes directory (Windows or Linux)
            title_id: UUID of the title in Supabase (must be unique per film)
            film_title: Title of the film (for logging)
            
        Returns:
            List of uploaded frame metadata
        """
        # ✅ FIXED: Convert to Path object for cross-platform support
        keyframes_path = Path(keyframes_dir)
        
        # ✅ FIXED: Convert to absolute path and normalize
        if not keyframes_path.is_absolute():
            keyframes_path = keyframes_path.resolve()
        
        logger.info(f"📤 Starting keyframe upload for '{film_title}' (title_id: {title_id})")
        logger.info(f"📁 Keyframes directory: {keyframes_path}")
        
        if not keyframes_path.exists():
            logger.error(f"❌ Keyframes directory not found: {keyframes_path}")
            return []
        
        # ✅ Get all .jpg files (case-insensitive)
        keyframe_files = sorted(keyframes_path.glob("shot_*.jpg"))
        
        if not keyframe_files:
            logger.warning(f"❌ No shot_*.jpg files found in: {keyframes_path}")
            
            # ✅ DEBUG: List all files in directory
            all_files = list(keyframes_path.glob("*.*"))
            logger.warning(f"📂 Directory contains {len(all_files)} files")
            for f in all_files[:10]:  # Show first 10
                logger.warning(f"  - {f.name}")
            
            return []
        
        logger.info(f"📤 Found {len(keyframe_files)} keyframes to upload")
        
        # ✅ CRITICAL: Clean up old keyframes for this title_id first
        try:
            logger.info(f"🧹 Cleaning up old keyframes for title_id: {title_id}")
            
            # List existing files in storage
            existing_files = self.supabase.storage.from_('title-frames').list(f"{title_id}/")
            
            if existing_files:
                logger.info(f"🧹 Found {len(existing_files)} old keyframes to remove")
                # Batch removal - collect all paths and remove in a single call
                old_paths = [f"{title_id}/{old_file['name']}" for old_file in existing_files]
                self.supabase.storage.from_('title-frames').remove(old_paths)
                logger.info(f"✓ Cleaned up old keyframes from storage")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup old keyframes from storage: {e}")
        
        # ✅ Delete old database records
        try:
            self.supabase.table('title_frames').delete().eq('title_id', title_id).execute()
            logger.info(f"✓ Deleted old frame records from database")
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete old frame records: {e}")
        
        uploaded_frames = []
        
        for idx, keyframe_path in enumerate(keyframe_files, 1):
            try:
                # Read file
                with open(keyframe_path, 'rb') as f:
                    file_data = f.read()
                
                # Storage path: title-frames/{title_id}/shot_{idx:04d}.jpg
                storage_path = f"title-frames/{title_id}/shot_{idx:04d}.jpg"
                
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
                
                # Extract shot number from filename
                shot_number = idx
                
                # Estimate timestamp (if duration is known)
                # For now, assume evenly spaced
                timestamp = self._estimate_timestamp(idx, len(keyframe_files))
                
                # Save to database
                self.supabase.table('title_frames').insert({
                    'title_id': title_id,
                    'frame_url': frame_url,
                    'frame_number': shot_number,
                    'timestamp': timestamp
                }).execute()
                
                uploaded_frames.append({
                    'frame_number': shot_number,
                    'frame_url': frame_url,
                    'timestamp': timestamp,
                    'local_path': str(keyframe_path)
                })
                
                # ✅ Log every 10th frame to avoid spam
                if idx % 10 == 0:
                    logger.info(f"  ↗ Uploaded {idx}/{len(keyframe_files)} frames...")
                
            except Exception as e:
                logger.error(f"❌ Failed to upload frame {idx}: {e}")
                continue
        
        logger.info(f"✅ Successfully uploaded {len(uploaded_frames)}/{len(keyframe_files)} keyframes for '{film_title}'")
        
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
            # Fallback: assume ~3 seconds per shot (reasonable average)
            timestamp_sec = frame_number * 3
        
        minutes = int(timestamp_sec // 60)
        seconds = int(timestamp_sec % 60)
        
        return f"{minutes:02d}:{seconds:02d}"