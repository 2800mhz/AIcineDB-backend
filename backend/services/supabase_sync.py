"""
Supabase Sync Service for AIcineDB
Syncs analyzed films to Supabase database for Lovable frontend (cineai-showcase project)
"""
import os
import re
import logging
from typing import Dict, Optional, List
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


class SupabaseSyncService:
    """Handles syncing analyzed films to Supabase for the Lovable frontend"""
    
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
    
    def _generate_slug(self, title: str) -> str:
        """
        Create a URL-friendly slug from the title.
        
        Args:
            title: Film title
            
        Returns:
            URL-friendly slug
        """
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
    
    def _get_thumbnail(self, url: str, keyframes: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Extract thumbnail URL from video URL or keyframes.
        
        Args:
            url: Original video URL
            keyframes: List of keyframe data with paths
            
        Returns:
            Thumbnail URL or None
        """
        if not url:
            return None
        
        # Try to extract YouTube video ID and construct thumbnail URL
        youtube_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # Return high quality YouTube thumbnail
                return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # If not YouTube, try to use first keyframe if available
        # Note: Keyframe paths are local, so we can't use them directly as URLs
        # Return None and let the frontend handle missing thumbnails
        return None
    
    def _map_analysis_to_title(self, film_data: Dict) -> Dict:
        """
        Convert AIcineDB analysis results to Lovable titles table schema.
        
        Args:
            film_data: Complete analysis result from the pipeline
            
        Returns:
            Dictionary matching the Supabase titles table schema
        """
        # Extract narrative data if available
        narrative = film_data.get('narrative') or {}
        audio_features = film_data.get('audio_features') or {}
        shots = film_data.get('shots') or []
        characters = film_data.get('characters') or []
        scenes = film_data.get('scenes') or []
        
        # Get title and generate slug
        title = film_data.get('title', 'Untitled')
        slug = self._generate_slug(title)
        
        # Convert duration from seconds to minutes
        duration_seconds = film_data.get('duration', 0)
        duration_minutes = int(duration_seconds / 60) if duration_seconds else None
        
        # Extract genres from narrative (limit to 5)
        genres = []
        if narrative.get('genre'):
            genre_value = narrative['genre']
            if isinstance(genre_value, list):
                genres = genre_value[:5]
            elif isinstance(genre_value, str):
                genres = [genre_value]
        
        # Extract moods from audio mood + narrative tone (limit to 5)
        moods = []
        if audio_features.get('mood'):
            moods.append(audio_features['mood'])
        if narrative.get('tone'):
            tone_value = narrative['tone']
            if isinstance(tone_value, list):
                moods.extend(tone_value)
            elif isinstance(tone_value, str) and tone_value not in moods:
                moods.append(tone_value)
        moods = moods[:5]
        
        # Extract tags from narrative themes (limit to 10)
        tags = []
        if narrative.get('themes'):
            themes = narrative['themes']
            if isinstance(themes, list):
                tags = themes[:10]
        
        # Get logline and description
        logline = narrative.get('summary') or narrative.get('logline') or None
        description = narrative.get('synopsis') or logline
        
        # Get thumbnail/poster URL
        poster_url = self._get_thumbnail(
            film_data.get('url'),
            [s for s in shots if s.get('keyframe_path')]
        )
        
        # Build the title record for Supabase
        title_record = {
            "title": title,
            "slug": slug,
            "type": "movie",
            "year": datetime.now().year,
            "duration": duration_minutes,
            "logline": logline,
            "description": description,
            "poster_url": poster_url,
            "trailer_youtube_url": film_data.get('url') if 'youtube' in (film_data.get('url') or '').lower() else None,
            "status": "completed",
            "genres": genres if genres else None,
            "moods": moods if moods else None,
            "tags": tags if tags else None,
            "ai_model": "AIcineDB Analyzer",
            "aicinedb_film_id": str(film_data.get('job_id')),
            "style_fingerprint": film_data.get('style_fingerprint'),
            "shot_count": len(shots),
            "character_count": len(characters),
            "scene_count": len(scenes),
        }
        
        # Remove None values to let Supabase use defaults
        return {k: v for k, v in title_record.items() if v is not None}
    
    async def sync_film(self, film_data: Dict) -> Optional[Dict]:
        """
        Sync a film analysis to Supabase.
        Performs upsert based on aicinedb_film_id.
        
        Args:
            film_data: Complete analysis result from the pipeline
            
        Returns:
            The synced record from Supabase, or None if sync failed/disabled
        """
        if not self.enabled:
            logger.debug("Supabase sync is disabled, skipping")
            return None
        
        try:
            job_id = film_data.get('job_id')
            logger.info(f"🔄 Syncing film to Supabase (job_id: {job_id})...")
            
            # Map the analysis data to Supabase schema
            title_record = self._map_analysis_to_title(film_data)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Check if record already exists
                check_url = f"{self.rest_url}/titles"
                check_params = {
                    "aicinedb_film_id": f"eq.{job_id}",
                    "select": "id"
                }
                
                check_response = await client.get(
                    check_url,
                    headers=self.headers,
                    params=check_params
                )
                check_response.raise_for_status()
                existing = check_response.json()
                
                if existing and len(existing) > 0:
                    # Update existing record
                    existing_id = existing[0]['id']
                    update_url = f"{self.rest_url}/titles?id=eq.{existing_id}"
                    
                    response = await client.patch(
                        update_url,
                        headers=self.headers,
                        json=title_record
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    logger.info(f"✓ Updated existing film in Supabase (id: {existing_id})")
                else:
                    # Create new record
                    create_url = f"{self.rest_url}/titles"
                    
                    response = await client.post(
                        create_url,
                        headers=self.headers,
                        json=title_record
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    new_id = result[0]['id'] if result else 'unknown'
                    logger.info(f"✓ Created new film in Supabase (id: {new_id})")
                
                return result[0] if result else None
                
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"⚠ Supabase sync failed with HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return None
        except httpx.RequestError as e:
            logger.warning(f"⚠ Supabase sync failed with request error: {e}")
            return None
        except Exception as e:
            logger.warning(f"⚠ Supabase sync failed with unexpected error: {e}")
            return None
