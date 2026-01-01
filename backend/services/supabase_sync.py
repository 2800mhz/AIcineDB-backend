"""
Supabase Sync Service for AIcineDB
Syncs analyzed films to Supabase database for Lovable frontend (cineai-showcase project)
"""
import os
import re
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID  # ✅ YENİ: UUID import eklendi

from dotenv import load_dotenv
load_dotenv()

import httpx

# ✅ YENİ: supabase kütüphanesi import
try:
    from supabase import create_client, Client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:
    SUPABASE_SDK_AVAILABLE = False
    Client = None

logger = logging.getLogger(__name__)


# ✅ YENİ: UUID Serialization Helper Function
def serialize_for_json(obj: Any) -> Any:
    """
    UUID ve diğer özel tipleri JSON-serializable hale getirir.
    Nested dict/list'ler için de çalışır.
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj


class SupabaseSyncService:
    """Handles syncing analyzed films to Supabase for the Lovable frontend"""
    
    # ✅ YENİ: Singleton pattern için class attribute'lar
    _instance: Optional['SupabaseSyncService'] = None
    _supabase_client: Optional['Client'] = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize the Supabase sync service. 
        Reads SUPABASE_URL and SUPABASE_SERVICE_KEY from environment variables.
        If not configured, sync operations will be disabled. 
        """
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.enabled = bool(self.supabase_url and self.supabase_key)
        
        if self.enabled:
            # Build the REST API base URL
            self.rest_url = f"{self.supabase_url}/rest/v1"
            self.headers = {
                "apikey": self.supabase_key,
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
            logger.info("✓ Supabase sync service initialized")
        else:
            logger.warning("⚠ Supabase sync disabled: SUPABASE_URL or SUPABASE_SERVICE_KEY not configured")
    
    # ✅ YENİ: supabase property eklendi
    @property
    def supabase(self) -> Optional['Client']:
        """Get Supabase client instance (lazy initialization)"""
        if self._supabase_client is None and self.enabled:
            if not SUPABASE_SDK_AVAILABLE:
                logger.error("❌ supabase-py SDK not installed. Run: pip install supabase")
                return None
            try:
                self._supabase_client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ Supabase SDK client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Supabase SDK client: {e}")
                return None
        return self._supabase_client
    
    def upload_poster_image(self, image_path: str, title_id: str) -> Optional[str]:
        """
        Upload poster image to Supabase Storage
        
        Args:
            image_path: Local path to image file
            title_id: Title UUID
            
        Returns:
            Public URL of uploaded image, or None if upload fails
        """
        if not self.enabled:
            logger.debug("Supabase sync disabled, skipping poster upload")
            return None
        
        if not self.supabase:
            logger.error("❌ Supabase SDK client not available")
            return None
        
        try:
            # Read image file
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # Upload to storage (bucket: title-frames)
            file_name = f"posters/{title_id}_poster.jpg"
            
            result = self.supabase.storage.from_('title-frames').upload(
                file_name,
                image_data,
                {'content-type': 'image/jpeg', 'upsert': 'true'}
            )
            
            # Get public URL
            url_data = self.supabase.storage.from_('title-frames').get_public_url(file_name)
            
            logger.info(f"✅ Poster uploaded: {url_data}")
            return url_data
            
        except Exception as e:
            logger.error(f"❌ Failed to upload poster: {e}")
            return None
    
    def _generate_slug(self, title: str) -> str:
        """Create a URL-friendly slug from the title."""
        if not title:
            return "untitled"
        
        # Convert to lowercase
        slug = title.lower()
        
        # Replace spaces and underscores with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)
        
        # Remove any characters that aren't alphanumeric or hyphens
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Ensure we have something
        if not slug:
            slug = "untitled"
        
        return slug
    
    def _format_timestamp(self, timestamp) -> float:
        """
        Convert timestamp to float seconds. 
        Handles both "MM:SS" strings and numeric values.
        """
        if isinstance(timestamp, (int, float)):
            return float(timestamp)
        
        if isinstance(timestamp, str):
            # Parse "MM:SS" or "HH:MM:SS" format
            parts = timestamp.split(':')
            if len(parts) == 2:  # MM:SS
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        
        return 0.0  # Fallback
    
    def _get_thumbnail(self, url: str) -> Optional[str]:
        """Get thumbnail URL for video"""
        if not url:
            return None
        
        # YouTube patterns
        youtube_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Vimeo patterns
        vimeo_patterns = [
            r'vimeo\.com/(\d+)',
            r'vimeo\.com/video/(\d+)',
            r'player\.vimeo\.com/video/(\d+)',
        ]
        
        for pattern in vimeo_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://vumbnail.com/{video_id}.jpg"
        
        return None
    
    def _extract_genres(self, narrative: Dict, style: Dict) -> list:
        """Extract genres from narrative analysis and visual style."""
        genres = []
        
        # From narrative genre field
        if narrative.get('genre'):
            genre_value = narrative['genre']
            if isinstance(genre_value, list):
                genres.extend(genre_value)
            elif isinstance(genre_value, str):
                genres.append(genre_value)
        
        # From style fingerprint (e.g., "3d-realistic-documentary")
        style_fingerprint = style.get('fingerprint', '')
        if style_fingerprint:
            if 'documentary' in style_fingerprint.lower():
                if 'Documentary' not in genres:
                    genres.append('Documentary')
            if 'dramatic' in style_fingerprint.lower():
                if 'Drama' not in genres:
                    genres.append('Drama')
        
        # Default if empty
        if not genres:
            genres = ['Uncategorized']
        
        return genres[:5]  # Limit to 5
    
    def _extract_moods(self, narrative: Dict, audio_features: Dict) -> list:
        """Extract moods from narrative and audio analysis."""
        moods = []
        
        # From audio mood
        if audio_features.get('mood'):
            moods.append(audio_features['mood'])
        
        # From narrative tone
        if narrative.get('tone'):
            tone_value = narrative['tone']
            if isinstance(tone_value, list):
                moods.extend(tone_value)
            elif isinstance(tone_value, str) and tone_value not in moods:
                moods.append(tone_value)
        
        # From emotional arc
        if narrative.get('emotional_arc'):
            arc = narrative['emotional_arc']
            if isinstance(arc, str) and arc not in moods:
                moods.append(arc)
        
        # Default if empty
        if not moods:
            moods = ['Neutral']
        
        return moods[:5]  # Limit to 5
    
    def _extract_tags(self, narrative: Dict, film_data: Dict) -> list:
        """Extract tags from themes and other metadata."""
        tags = []
        
        # From narrative themes
        if narrative.get('themes'):
            themes = narrative['themes']
            if isinstance(themes, list):
                tags.extend(themes)
        
        # From key quotes (extract keywords)
        if narrative.get('key_quotes'):
            tags.append('Quotable')
        
        # From character count
        if len(film_data.get('characters', [])) > 10:
            tags.append('Ensemble Cast')
        
        # From shot count (visual complexity)
        if len(film_data.get('shots', [])) > 50:
            tags.append('Visually Complex')
        
        # Default if empty
        if not tags:
            tags = ['AI Analyzed']
        
        return tags[:10]  # Limit to 10
    
    def _generate_logline(self, narrative: Dict, title: str) -> str:
        """Generate a logline from narrative or create a default."""
        # Try to get from narrative
        if narrative.get('summary'):
            return narrative['summary']
        
        if narrative.get('logline'):
            return narrative['logline']
        
        # Try to build from available data
        if narrative.get('character_analysis', {}).get('protagonist'):
            protagonist = narrative['character_analysis']['protagonist']
            return f"A story following {protagonist}."
        
        # Default
        return f"AI-analyzed content: {title}"
    
    def _generate_description(self, narrative: Dict, film_data: Dict) -> str:
        """Generate a description from narrative analysis."""
        parts = []
        
        # Add summary if available
        if narrative.get('summary'):
            parts.append(narrative['summary'])
        
        # Add cinematography notes
        if narrative.get('cinematography_notes'):
            parts.append(f"Visual Style: {narrative['cinematography_notes']}")
        
        # Add structure info
        if narrative.get('structure', {}).get('act1'):
            parts.append(f"The story begins with {narrative['structure']['act1']}")
        
        # Add technical info
        shots = len(film_data.get('shots', []))
        characters = len(film_data.get('characters', []))
        scenes = len(film_data.get('scenes', []))
        
        if shots or characters or scenes:
            parts.append(f"Technical: {shots} shots, {characters} characters, {scenes} detected.")
        
        if parts:
            return " ".join(parts)
        
        return f"AI-analyzed video content with detailed shot and character analysis."
    
    def _calculate_initial_rating(self, film_data: Dict) -> float:
        """Calculate an initial rating based on analysis quality."""
        score = 5.0  # Base score
        
        narrative = film_data.get('narrative') or {}
        
        # Bonus for having narrative analysis
        if narrative.get('summary'):
            score += 1.0
        
        # Bonus for themes
        if narrative.get('themes') and len(narrative['themes']) >= 3:
            score += 0.5
        
        # Bonus for detailed structure
        if narrative.get('structure'):
            score += 0.5
        
        # Bonus for character analysis
        if len(film_data.get('characters', [])) > 5:
            score += 0.5
        
        # Bonus for visual complexity
        if len(film_data.get('shots', [])) > 20:
            score += 0.5
        
        # Cap at 10
        return min(score, 10.0)
    
    def _map_analysis_to_title(self, film_data: Dict) -> Dict:
        """
        Convert AIcineDB analysis results to Lovable titles table schema.
        
        Args:
            film_data: Complete analysis result from the pipeline
            
        Returns:
            Dictionary matching the Supabase titles table schema
        """
        # Extract components
        narrative = film_data.get('narrative') or {}
        audio_features = film_data.get('audio_features') or {}
        style = film_data.get('style') or {}
        shots = film_data.get('shots') or []
        characters = film_data.get('characters') or []
        scenes = film_data.get('scenes') or []
        
        # Get title and generate slug
        title = film_data.get('title', 'Untitled')
        slug = self._generate_slug(title)
        
        # Convert duration from seconds to minutes
        duration_seconds = film_data.get('duration', 0)
        duration_minutes = int(duration_seconds / 60) if duration_seconds else 1
        
        # Extract rich metadata
        genres = self._extract_genres(narrative, style)
        moods = self._extract_moods(narrative, audio_features)
        tags = self._extract_tags(narrative, film_data)
        logline = self._generate_logline(narrative, title)
        description = self._generate_description(narrative, film_data)
        
        # Get uploader as production company
        production_company = film_data.get('uploader') or 'Independent'
        
        # Calculate initial rating
        initial_rating = self._calculate_initial_rating(film_data)
        
        # Get year from metadata or use current year
        year = film_data.get('year') or datetime.now().year
        
        # Get dominant color from color palette
        color_palette = film_data.get('color_palette') or {}
        dominant_color = None
        if color_palette.get('palette'):
            dominant_color = color_palette['palette'][0] if color_palette['palette'] else None
        
        # Get poster URL - prioritize uploaded poster, fallback to thumbnail extraction
        poster_url = film_data.get('poster_url') or self._get_thumbnail(film_data.get('url'))
        
        # Get video URL for playback - use original URL for all platforms
        video_url = film_data.get('video_url') or film_data.get('url')
        
        # Build the title record for Supabase
        title_record = {
            "title": title,
            "slug": slug,
            "type": "movie",
            "year": year,
            "duration": duration_minutes,
            "logline": logline,
            "description": description,
            "poster_url": poster_url,
            "trailer_youtube_url": video_url,  # Used for video playback (all platforms)
            "status": "completed",
            "genres": genres,
            "moods": moods,
            "tags": tags,
            "ai_model": "AIcineDB Analyzer v1.0",
            "production_company": production_company,
            "rating_average": initial_rating,
            "rating_count": 1,  # Start with 1 (AI rating)
            "view_count": 0,
            "trending_score": 50,  # Neutral starting score
            "dominant_color": dominant_color,
            "aicinedb_film_id": str(film_data.get('job_id')),
            "style_fingerprint": film_data.get('style_fingerprint'),
            "shot_count": len(shots),
            "character_count": len(characters),
            "scene_count": len(scenes),
        }
        
        # Add uploaded_by if user_id is provided
        # Only set this for NEW titles; don't overwrite for existing titles
        user_id = film_data.get('user_id')
        if user_id:
            title_record["uploaded_by"] = user_id
        
        # Remove None values to let Supabase use defaults
        return {k: v for k, v in title_record.items() if v is not None}

    async def _sync_cast_crew(self, title_id: str, film_data: Dict) -> None:
        """
        Sync cast & crew to Supabase title_cast table
        
        Args:
            title_id: Supabase title UUID
            film_data: Analysis result with cast/crew
        """
        if not self.enabled:
            return
        
        try:
            cast = film_data.get('cast', [])
            crew = film_data.get('crew', [])
            
            if not cast and not crew:
                logger.debug("No cast/crew to sync")
                return
            
            # Combine cast & crew
            all_people = []
            
            # Cast members
            for i, member in enumerate(cast):
                all_people.append({
                    'title_id': title_id,
                    'name': member.get('name', 'Unknown'),
                    'character_name': member.get('role'),  # Character name
                    'role': member.get('type', 'actor'),
                    'department': 'acting',
                    'ordering': i + 1,
                    'screen_time': member.get('screen_time'),
                    'appearance_count': member.get('appearance_count'),
                })
            
            # Crew members
            for i, member in enumerate(crew):
                all_people.append({
                    'title_id': title_id,
                    'name': member.get('name', 'Unknown'),
                    'character_name': None,
                    'role': member.get('role', 'crew').lower().replace(' ', '_'),
                    'department': member.get('department', 'production'),
                    'ordering': len(cast) + i + 1,
                })
            
            if not all_people:
                return
            
            # First, delete existing cast/crew for this title (upsert)
            async with httpx.AsyncClient(timeout=30.0) as client:
                delete_url = f"{self.rest_url}/title_cast"
                await client.delete(
                    delete_url,
                    headers=self.headers,
                    params={"title_id": f"eq.{title_id}"}
                )
                
                # Then insert new cast/crew
                insert_url = f"{self.rest_url}/title_cast"
                response = await client.post(
                    insert_url,
                    headers=self.headers,
                    json=all_people
                )
                response.raise_for_status()
                
                logger.info(f"✓ Synced {len(all_people)} cast/crew members to Supabase")
                
        except Exception as e:
            logger.warning(f"⚠ Cast/crew sync failed: {e}")

    async def sync_film(self, film_data: Dict, title_id: str = None) -> Optional[Dict]:
        """
        Sync a film analysis to Supabase with proper conflict handling. 
        
        Strategy:
        1. If title_id is provided:  UPDATE that specific record
        2. Otherwise, check if film exists by backend_job_id or slug  # 👈 BURADA DEĞİŞİKLİK
        3. If exists: UPDATE the record
        4. If new: INSERT new record
        5. Always return title_id for frame upload
        """
        if not self.enabled:
            logger.debug("Supabase sync is disabled, skipping")
            return None
        
        try:
            job_id = film_data.get('job_id')
            title = film_data.get('title', 'Unknown')
            slug = self._generate_slug(title)
            
            logger.info(f"🔄 Syncing film to Supabase: {title} (job_id: {job_id}, slug: {slug}, title_id: {title_id})")
            
            # Map the analysis data to Supabase schema
            title_record = self._map_analysis_to_title(film_data)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                existing_title = None
                
                # Step 1: If title_id is provided, update that specific record
                if title_id:
                    logger.info(f"✓ Updating existing title:  {title_id}")
                    update_url = f"{self.rest_url}/titles"
                    update_headers = {
                        **self.headers,
                        "Prefer": "return=representation",
                        "Content-Type": "application/json; charset=utf-8"
                    }
                    
                    # 🔥 ÖNEMLİ: slug ve aicinedb_film_id'yi update'den çıkar
                    update_data = {k: v for k, v in title_record.items() 
                                if k not in ['slug', 'aicinedb_film_id']}  # 👈 YENİ
                    
                    logger.info(f"✓ Removing slug and backend_job_id from update (preserving existing values)")  # 👈 YENİ
                    
                    # ✅ FIX: UUID'leri string'e çevir
                    update_data = serialize_for_json(update_data)
                    json_data = json.dumps(update_data, ensure_ascii=False)
                    
                    response = await client.patch(
                        update_url,
                        headers=update_headers,
                        params={"id": f"eq.{title_id}"},
                        content=json_data. encode('utf-8')
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if result and len(result) > 0:
                        existing_title = result[0]
                        logger.info(f"✅ Updated title in Supabase: {title_id}")
                    else: 
                        # Fetch the updated record
                        select_url = f"{self.rest_url}/titles"
                        response = await client.get(
                            select_url,
                            headers=self.headers,
                            params={"id":  f"eq.{title_id}", "select": "*"}
                        )
                        result = response.json()
                        existing_title = result[0] if result else None
                        
                        if existing_title:
                            logger.info(f"✅ Fetched updated title:  {title_id}")
                        else:
                            logger.error(f"❌ Could not fetch title after update: {title_id}")
                            return None
                else: 
                    # 🔥 YENİ: backend_job_id ile de ara
                    if job_id:
                        select_url = f"{self.rest_url}/titles"
                        response = await client.get(
                            select_url,
                            headers=self.headers,
                            params={"backend_job_id": f"eq.{job_id}", "select": "*"}  # 👈 YENİ
                        )
                        if response.status_code == 200:
                            result = response. json()
                            if result and len(result) > 0:
                                existing_title = result[0]
                                logger. info(f"✓ Found existing title by backend_job_id: {existing_title['id']}")
                    
                    # Fallback: Try by slug
                    if not existing_title:
                        select_url = f"{self.rest_url}/titles"
                        response = await client.get(
                            select_url,
                            headers=self.headers,
                            params={"slug": f"eq.{slug}", "select": "*"}
                        )
                        if response.status_code == 200:
                            result = response.json()
                            if result and len(result) > 0:
                                existing_title = result[0]
                                logger.info(f"✓ Found existing title by slug: {existing_title['id']}")
                    
                    # UPDATE or INSERT
                    if existing_title:
                        title_id = existing_title['id']
                        logger.info(f"📝 Updating existing title: {title_id}")
                        
                        # 🔥 Slug ve aicinedb_film_id'yi update'den çıkar
                        update_data = {k: v for k, v in title_record.items() 
                                    if k not in ['slug', 'aicinedb_film_id']}
                        
                        update_url = f"{self.rest_url}/titles"
                        update_headers = {
                            **self.headers,
                            "Prefer": "return=representation",
                            "Content-Type": "application/json; charset=utf-8"
                        }
                        
                        # ✅ FIX: UUID'leri string'e çevir
                        update_data = serialize_for_json(update_data)
                        json_data = json.dumps(update_data, ensure_ascii=False)
                        
                        response = await client.patch(
                            update_url,
                            headers=update_headers,
                            params={"id":  f"eq.{title_id}"},
                            content=json_data.encode('utf-8')
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if result and len(result) > 0:
                            logger.info(f"✅ Updated title in Supabase:  {title_id}")
                            existing_title = result[0]
                        else:
                            logger.warning(f"⚠️ Update returned no data, using existing title_id: {title_id}")
                            existing_title = {'id': title_id, **update_data}
                    else: 
                        # INSERT new record
                        logger.info(f"✨ Creating new title")
                        
                        insert_url = f"{self.rest_url}/titles"
                        insert_headers = {
                            **self.headers,
                            "Prefer": "return=representation",
                            "Content-Type":  "application/json; charset=utf-8"
                        }
                        
                        # ✅ FIX: UUID'leri string'e çevir
                        title_record = serialize_for_json(title_record)
                        json_data = json.dumps(title_record, ensure_ascii=False)
                        
                        response = await client.post(
                            insert_url,
                            headers=insert_headers,
                            content=json_data.encode('utf-8')
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if result and len(result) > 0:
                            existing_title = result[0]
                            title_id = existing_title['id']
                            logger.info(f"✅ Created new title in Supabase: {title_id}")
                        else: 
                            logger.error(f"❌ Insert failed, no data returned")
                            return None
                
                # Step 3:  Sync cast & crew
                await self._sync_cast_crew(existing_title['id'], film_data)
                
                return existing_title
                
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Supabase sync failed with HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.error(f"❌ Supabase sync failed with request error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Supabase sync failed with unexpected error: {e}", exc_info=True)
            return None
    
    async def upload_frames(self, title_id: str, frames: List[Dict]) -> List[str]:
        """
        Upload frames to Supabase storage and insert into title_frames table.
        
        Args:
            title_id: Supabase title UUID
            frames: List of frame dicts with 'path', 'timestamp', 'frame_number', etc.
            
        Returns:
            List of public URLs for uploaded frames
        """
        if not self.enabled:
            logger.debug("Supabase sync is disabled, skipping frame upload")
            return []
        
        if not frames:
            logger.debug("No frames to upload")
            return []
        
        import base64
        from pathlib import Path
        
        logger.info(f"📤 Uploading {len(frames)} frames for title {title_id}...")
        
        uploaded_urls = []
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # First, delete existing frames for this title
                try:
                    delete_url = f"{self.rest_url}/title_frames"
                    await client.delete(
                        delete_url,
                        headers=self.headers,
                        params={"title_id": f"eq.{title_id}"}
                    )
                    logger.info("✓ Cleared existing frame records")
                except Exception as e:
                    logger.warning(f"Failed to clear existing frames: {e}")
                
                # Upload each frame
                for idx, frame in enumerate(frames):
                    try:
                        frame_path = frame.get('path', '')
                        if not frame_path or not Path(frame_path).exists():
                            logger.warning(f"Frame path not found: {frame_path}")
                            continue
                        
                        # Read frame file
                        with open(frame_path, 'rb') as f:
                            file_data = f.read()
                        
                        # Storage path
                        frame_number = frame.get('frame_number', idx + 1)
                        storage_path = f"{title_id}/frame_{frame_number:04d}.jpg"
                        
                        # Upload to Supabase Storage
                        storage_url = f"{self.supabase_url}/storage/v1/object/title-frames/{storage_path}"
                        
                        upload_headers = {
                            "apikey": self.supabase_key,
                            "Authorization": f"Bearer {self.supabase_key}",
                            "Content-Type": "image/jpeg",
                            "x-upsert": "true"
                        }
                        
                        response = await client.post(
                            storage_url,
                            headers=upload_headers,
                            content=file_data
                        )
                        
                        if response.status_code not in [200, 201]:
                            logger.warning(f"Frame upload failed: {response.status_code}")
                            continue
                        
                        # Get public URL
                        public_url = f"{self.supabase_url}/storage/v1/object/public/title-frames/{storage_path}"
                        
                        # Insert into title_frames table
                        frame_record = {
                            "title_id": title_id,
                            "frame_url": public_url,
                            "frame_number": frame_number,
                            "timestamp": self._format_timestamp(frame.get('timestamp', 0)),
                            "ordering": frame.get('ordering', idx)
                        }
                        
                        insert_url = f"{self.rest_url}/title_frames"
                        await client.post(
                            insert_url,
                            headers=self.headers,
                            json=frame_record
                        )
                        
                        uploaded_urls.append(public_url)
                        
                        # Log progress every 5 frames
                        if (idx + 1) % 5 == 0:
                            logger.info(f"  ↗ Uploaded {idx + 1}/{len(frames)} frames...")
                            
                    except Exception as e:
                        logger.warning(f"Failed to upload frame {idx + 1}: {e}")
                        continue
                
                logger.info(f"✓ Successfully uploaded {len(uploaded_urls)}/{len(frames)} frames")
                
        except Exception as e:
            logger.error(f"Frame upload failed: {e}")
        
        return uploaded_urls

    async def upload_keyframes(self, title_id: str, keyframes_dir: str) -> int:
        """
        Upload keyframes to Supabase Storage and create database records.
        
        This method uploads keyframes from a local directory to Supabase Storage
        and creates corresponding records in the title_frames table.
        
        Args:
            title_id: UUID of the title in Supabase
            keyframes_dir: Local directory containing keyframe images
            
        Returns:
            Number of successfully uploaded frames
        """
        if not self.enabled:
            logger.debug("Supabase sync is disabled, skipping keyframe upload")
            return 0
        
        if not os.path.exists(keyframes_dir):
            logger.warning(f"Keyframes directory not found: {keyframes_dir}")
            return 0
        
        # Get all .jpg and .png files
        keyframe_files = sorted([
            f for f in os.listdir(keyframes_dir)
            if f.lower().endswith('.jpg') or f.lower().endswith('.png')
        ])
        
        if not keyframe_files:
            logger.warning(f"No keyframes found in {keyframes_dir}")
            return 0
        
        logger.info(f"📤 Uploading {len(keyframe_files)} keyframes for title {title_id}")
        
        uploaded_count = 0
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Clear existing frames for this title
                try:
                    delete_url = f"{self.rest_url}/title_frames"
                    await client.delete(
                        delete_url,
                        headers=self.headers,
                        params={"title_id": f"eq.{title_id}"}
                    )
                    logger.info("✓ Cleared existing frame records")
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    logger.warning(f"Could not clear existing frames: {e}")
                
                for idx, filename in enumerate(keyframe_files, 1):
                    try:
                        file_path = os.path.join(keyframes_dir, filename)
                        
                        # Extract frame number from filename
                        # Try specific patterns first (shot_0001.jpg, frame_0001.jpg)
                        match = re.search(r'(?:shot|frame)[_-]?(\d+)', filename, re.IGNORECASE)
                        if not match:
                            # Fallback to any number sequence
                            match = re.search(r'(\d+)', filename)
                        frame_number = int(match.group(1)) if match else idx
                        
                        # Read file
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        # Determine content type
                        content_type = 'image/jpeg' if filename.lower().endswith('.jpg') else 'image/png'
                        extension = 'jpg' if filename.lower().endswith('.jpg') else 'png'
                        
                        # Storage path
                        storage_path = f"{title_id}/frame_{frame_number:04d}.{extension}"
                        
                        # Upload to Supabase Storage
                        storage_url = f"{self.supabase_url}/storage/v1/object/title-frames/{storage_path}"
                        
                        upload_headers = {
                            "apikey": self.supabase_key,
                            "Authorization": f"Bearer {self.supabase_key}",
                            "Content-Type": content_type,
                            "x-upsert": "true"
                        }
                        
                        response = await client.post(
                            storage_url,
                            headers=upload_headers,
                            content=file_data
                        )
                        
                        if response.status_code not in [200, 201]:
                            logger.warning(f"Frame upload failed for {filename}: {response.status_code}")
                            continue
                        
                        # Get public URL
                        public_url = f"{self.supabase_url}/storage/v1/object/public/title-frames/{storage_path}"
                        
                        # Create database record
                        # Approximate timestamp based on frame ordering (10 seconds between frames)
                        frame_record = {
                            "title_id": title_id,
                            "frame_url": public_url,
                            "frame_number": frame_number,
                            "timestamp": self._format_timestamp(idx * 10.0),
                            "ordering": idx
                        }
                        
                        insert_url = f"{self.rest_url}/title_frames"
                        await client.post(
                            insert_url,
                            headers=self.headers,
                            json=frame_record
                        )
                        
                        uploaded_count += 1
                        
                        if uploaded_count % 5 == 0:
                            logger.info(f"  ↗ Uploaded {uploaded_count}/{len(keyframe_files)} frames...")
                            
                    except Exception as e:
                        logger.error(f"Failed to upload {filename}: {e}")
                        continue
                
        except Exception as e:
            logger.error(f"Keyframe upload failed: {e}", exc_info=True)
        
        logger.info(f"✅ Successfully uploaded {uploaded_count}/{len(keyframe_files)} keyframes")
        return uploaded_count
    
    async def sync_discovered_festival(self, festival_data: dict) -> Optional[str]:
        """
        Festival'i discovered_festivals tablosuna UPSERT ile kaydet.
        """
        if not self.enabled:
            return None
        
        import httpx
        
        external_url = festival_data.get('external_url')
        if not external_url:
            logger.warning("⚠️ Festival has no external_url, skipping")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Mevcut kaydı kontrol et
                check_response = await client.get(
                    f"{self.rest_url}/discovered_festivals",
                    headers=self.headers,
                    params={
                        "external_url": f"eq.{external_url}",
                        "select": "id"
                    }
                )
                
                existing = check_response.json() if check_response.status_code == 200 else []
                
                # 2. Veriyi hazırla (DB şemasına uygun)
                db_data = {
                    "name": festival_data.get('name', 'Unknown Festival'),
                    "external_url": external_url,
                    "description": festival_data.get('description'),
                    "location": festival_data.get('location'),
                    "country": festival_data.get('country'),
                    "submission_deadline": festival_data.get('submission_deadline'),
                    
                    # ✅ DÜZELTME: Doğru alan adları
                    "is_ai_film_friendly": festival_data.get('is_ai_film_friendly', False),
                    "prestige_score": festival_data.get('prestige_score', 30),
                    "ai_relevance_score": festival_data.get('ai_score', 50),
                    
                    "status": "pending",
                    "updated_at": datetime.now().isoformat()
                }
                
                # source_id varsa ekle
                if festival_data.get('source_id'):
                    db_data['source_id'] = festival_data.get('source_id')
                
                if existing and len(existing) > 0:
                    # UPDATE
                    festival_id = existing[0]['id']
                    
                    update_response = await client.patch(
                        f"{self.rest_url}/discovered_festivals",
                        headers=self.headers,
                        params={"id": f"eq.{festival_id}"},
                        json=db_data
                    )
                    
                    if update_response.status_code in [200, 204]:
                        logger.debug(f"🔄 Updated festival: {festival_data.get('name')}")
                        return festival_id
                    else:
                        logger.warning(f"⚠️ Update failed: {update_response.text}")
                        return None
                else:
                    # INSERT
                    db_data['created_at'] = datetime.now().isoformat()
                    
                    insert_response = await client.post(
                        f"{self.rest_url}/discovered_festivals",
                        headers={**self.headers, "Prefer": "return=representation"},
                        json=db_data
                    )
                    
                    if insert_response.status_code in [200, 201]:
                        result = insert_response.json()
                        festival_id = result[0]['id'] if result else None
                        logger.info(f"✅ Saved new festival: {festival_data.get('name')}")
                        return festival_id
                    else:
                        logger.warning(f"⚠️ Insert failed: {insert_response.text}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ sync_discovered_festival error: {e}")
            return None
         
# backend/services/supabase_sync.py -> sync_news_article fonksiyonu

    async def sync_news_article(self, article: Dict) -> Optional[str]:
        """
        Save news article with SMART TAGGING
        """
        if not self.enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Check existing
                select_url = f"{self.rest_url}/news_articles"
                response = await client.get(
                    select_url,
                    headers=self.headers,
                    params={"external_url": f"eq.{article.get('external_url')}", "select": "id"}
                )
                if response.status_code == 200 and response.json():
                    return response.json()[0].get('id')
                
                # 2. Source ID bulma (Aynı mantık)
                source_id = None
                source_name = article.get("source_name") or article.get("source")
                if source_name:
                    try:
                        src_resp = await client.get(
                            f"{self.rest_url}/news_sources",
                            headers=self.headers,
                            params={"name": f"ilike.%{source_name}%", "select": "id"}
                        )
                        if src_resp.status_code == 200:
                            data = src_resp.json()
                            if data: source_id = data[0]['id']
                    except: pass

                # 3. AKILLI ETİKETLEME (YENİ KISIM) 🧠
                # Başlık ve özeti birleştirip analiz edelim
                full_text = (str(article.get('title')) + " " + str(article.get('summary'))).lower()
                
                categories = []
                tags = []
                
                # Kategori Kuralları
                if any(x in full_text for x in ['festival', 'sundance', 'cannes', 'berlinale', 'venice']):
                    categories.append('Festivals')
                    tags.append('Film Festival')
                
                if any(x in full_text for x in ['award', 'oscar', 'globe', 'bafta', 'nomination']):
                    categories.append('Awards')
                    tags.append('Awards Season')
                    
                if any(x in full_text for x in ['ai', 'artificial intelligence', 'tech', 'digital', 'software', 'vfx']):
                    categories.append('Technology')
                    tags.append('AI in Film')
                    
                if any(x in full_text for x in ['release', 'trailer', 'premiere', 'box office', 'opening']):
                    categories.append('Releases')
                
                if any(x in full_text for x in ['interview', 'director', 'actor', 'cast', 'spoke to']):
                    categories.append('Interviews')

                # Eğer hiçbiri uymadıysa 'Industry' yap
                if not categories:
                    categories.append('Industry')

                # 4. Insert payload
                summary_text = article.get("summary", "")
                if len(summary_text) > 3000: summary_text = summary_text[:2997] + "..."

                article_data = {
                    "title": article.get("title"),
                    "summary": summary_text,
                    "external_url": article.get("external_url"),
                    "image_url": article.get("image_url"),
                    "author": article.get("author"),
                    "source_id": source_id,
                    "category": categories,  # ✅ Otomatik kategoriler
                    "tags": tags,            # ✅ Otomatik etiketler
                    "ai_relevance_score": article.get("ai_relevance_score"),
                    "is_ai_curated": article.get("is_ai_cinema_relevant", False),
                    "published_at": article.get("published_at"),
                }
                
                # Clean None values
                article_data = {k: v for k, v in article_data.items() if v is not None}
                
                response = await client.post(
                    f"{self.rest_url}/news_articles",
                    headers=self.headers,
                    json=article_data
                )
                
                response.raise_for_status()
                result = response.json()
                
                if result:
                    return result[0].get('id')
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to sync news: {e}")
            return None
    
# backend/services/supabase_sync.py dosyasındaki approve_festival fonksiyonu:

    async def approve_festival(self, discovered_id: str) -> Optional[str]:
        """
        Move festival from discovered_festivals to festivals table.
        Matches the exact schema of both tables.
        """
        if not self.enabled:
            logger.debug("Supabase sync disabled, skipping festival approval")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Get discovered festival
                logger.info(f"📋 Fetching discovered festival: {discovered_id}")
                
                select_response = await client.get(
                    f"{self.rest_url}/discovered_festivals",
                    headers=self.headers,
                    params={"id": f"eq.{discovered_id}", "select": "*"}
                )
                
                if select_response.status_code != 200:
                    logger.error(f"❌ Failed to fetch discovered festival: {select_response.text}")
                    return None
                
                result = select_response.json()
                if not result:
                    logger.error(f"❌ Discovered festival not found: {discovered_id}")
                    return None
                
                discovered = result[0]
                festival_name = discovered.get('name', 'Unknown')
                logger.info(f"✅ Found discovered festival: {festival_name}")
                
                # 2. Prepare data for festivals table (EXACT SCHEMA MATCH)
                festival_data = {
                    # Required fields
                    "name": festival_name,
                    "slug": self._generate_slug(festival_name),
                    
                    # Optional text fields
                    "description": discovered.get("description"),
                    "external_url": discovered.get("external_url"),
                    "location": discovered.get("location"),
                    "country": discovered.get("country"),
                    
                    # Date fields
                    "start_date": discovered.get("start_date"),
                    "end_date": discovered.get("end_date"),
                    "submission_deadline": discovered.get("submission_deadline"),
                    
                    # Array fields
                    "category": discovered.get("category") or [],
                    "genres": discovered.get("genres") or [],
                    
                    # Boolean/Integer fields
                    "is_ai_friendly": discovered.get("is_ai_film_friendly", False),
                    "prestige_score": discovered.get("prestige_score", 50),
                    
                    # Status fields - CRITICAL!
                    "status": "active",      # ✅ Must be 'active' to show
                    "visibility": "public",  # ✅ Must be 'public' to show
                    
                    # Timestamps
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                # Remove None values to use DB defaults
                festival_data = {k: v for k, v in festival_data.items() if v is not None}
                
                logger.info(f"📝 Inserting festival to main table: {festival_name}")
                logger.debug(f"Festival data: {festival_data}")
                
                # 3. Check if festival already exists (by external_url or slug)
                existing_check = await client.get(
                    f"{self.rest_url}/festivals",
                    headers=self.headers,
                    params={
                        "or": f"(external_url.eq.{discovered.get('external_url')},slug.eq.{festival_data['slug']})",
                        "select": "id,name"
                    }
                )
                
                if existing_check.status_code == 200:
                    existing = existing_check.json()
                    if existing:
                        logger.warning(f"⚠️ Festival already exists: {existing[0].get('name')} (ID: {existing[0].get('id')})")
                        # Update discovered_festivals to mark as duplicate
                        await client.patch(
                            f"{self.rest_url}/discovered_festivals",
                            headers=self.headers,
                            params={"id": f"eq.{discovered_id}"},
                            json={
                                "status": "duplicate",
                                "duplicate_of": existing[0].get('id'),
                                "updated_at": datetime.now().isoformat()
                            }
                        )
                        return existing[0].get('id')
                
                # 4. Insert into festivals table
                insert_response = await client.post(
                    f"{self.rest_url}/festivals",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=festival_data
                )
                
                if insert_response.status_code not in [200, 201]:
                    logger.error(f"❌ Failed to insert festival: {insert_response.status_code}")
                    logger.error(f"Response: {insert_response.text}")
                    return None
                
                insert_result = insert_response.json()
                
                if not insert_result or len(insert_result) == 0:
                    logger.error("❌ Insert returned empty result")
                    return None
                
                festival_id = insert_result[0].get('id')
                logger.info(f"✅ Festival inserted with ID: {festival_id}")
                
                # 5. Update discovered_festivals status to 'approved'
                update_response = await client.patch(
                    f"{self.rest_url}/discovered_festivals",
                    headers=self.headers,
                    params={"id": f"eq.{discovered_id}"},
                    json={
                        "status": "approved",
                        "reviewed_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                )
                
                if update_response.status_code not in [200, 204]:
                    logger.warning(f"⚠️ Failed to update discovered festival status: {update_response.text}")
                
                logger.info(f"🎉 Successfully approved: {festival_name} → ID: {festival_id}")
                return festival_id
                
        except Exception as e:
            logger.error(f"❌ Failed to approve festival: {e}", exc_info=True)
            return None
    
    async def find_duplicate_festivals(self, festival_id: str, threshold: float = 0.95) -> List[Dict]:
        """
        Find similar festivals using vector similarity
        
        Args:
            festival_id: UUID of festival to compare
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar festivals
        """
        if not self.enabled:
            return []
        
        try:
            # This would use pgvector's similarity search in production
            # For now, return empty list as placeholder
            logger.info(f"🔍 Finding duplicates for festival {festival_id}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to find duplicate festivals: {e}")
            return []


# ✅ YENİ: Singleton instance ve helper fonksiyon
_supabase_service: Optional[SupabaseSyncService] = None

def get_supabase_client() -> Optional['Client']:
    """
    Get Supabase client instance.
    
    Returns:
        Supabase Client instance or None if not configured
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseSyncService()
    return _supabase_service.supabase