"""
Supabase Sync Service for AIcineDB
Syncs analyzed films to Supabase database for Lovable frontend (cineai-showcase project)
"""
import os
import re
import json
import logging
from typing import Dict, Optional
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

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
    
    def _get_thumbnail(self, url: str) -> Optional[str]:
        """Get thumbnail URL for video"""
        if not url:
            logger.debug("No URL provided for thumbnail")
            return None
        
        logger.debug(f"Getting thumbnail for URL: {url}")
        
        # YouTube patterns
        youtube_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                logger.debug(f"Found YouTube thumbnail: {thumbnail_url}")
                return thumbnail_url
        
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
                thumbnail_url = f"https://vumbnail.com/{video_id}.jpg"
                logger.debug(f"Found Vimeo thumbnail: {thumbnail_url}")
                return thumbnail_url
        
        logger.warning(f"No thumbnail pattern matched for URL: {url}")
        return None
    
    def _extract_genres(self, narrative: Dict, style: Dict) -> list:
        """Extract genres from narrative analysis and visual style."""
        genres = []
        
        # From narrative genre field
        if narrative.get('genre'):
            genre_value = narrative['genre']
            if isinstance(genre_value, list):
                genres.extend([str(g) for g in genre_value])
            elif isinstance(genre_value, str):
                try:
                    # Try to parse if it's a JSON string
                    parsed = json.loads(genre_value)
                    if isinstance(parsed, list):
                        genres.extend([str(g) for g in parsed])
                    else:
                        genres.append(str(genre_value))
                except (json.JSONDecodeError, TypeError):
                    genres.append(str(genre_value))
        
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
            mood_val = audio_features['mood']
            if isinstance(mood_val, str):
                moods.append(mood_val)
        
        # From narrative tone
        if narrative.get('tone'):
            tone_value = narrative['tone']
            if isinstance(tone_value, list):
                moods.extend([str(t) for t in tone_value])
            elif isinstance(tone_value, str):
                try:
                    # Try to parse if it's a JSON string
                    parsed = json.loads(tone_value)
                    if isinstance(parsed, list):
                        moods.extend([str(t) for t in parsed])
                    elif str(tone_value) not in moods:
                        moods.append(str(tone_value))
                except (json.JSONDecodeError, TypeError):
                    if str(tone_value) not in moods:
                        moods.append(str(tone_value))
        
        # From emotional arc
        if narrative.get('emotional_arc'):
            arc = narrative['emotional_arc']
            if isinstance(arc, str):
                try:
                    parsed = json.loads(arc)
                    if isinstance(parsed, str) and parsed not in moods:
                        moods.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    if arc not in moods:
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
                tags.extend([str(t) for t in themes])
            elif isinstance(themes, str):
                try:
                    parsed = json.loads(themes)
                    if isinstance(parsed, list):
                        tags.extend([str(t) for t in parsed])
                    else:
                        tags.append(str(themes))
                except (json.JSONDecodeError, TypeError):
                    tags.append(str(themes))
        
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
            parts.append(f"Technical: {shots} shots, {characters} characters, {scenes} scenes detected.")
        
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
        
        # Build the title record for Supabase
        title_record = {
            "title": title,
            "slug": slug,
            "type": "movie",
            "year": year,
            "duration": duration_minutes,
            "logline": logline,
            "description": description,
            "poster_url": self._get_thumbnail(film_data.get('url')),
            "trailer_youtube_url": film_data.get('url') if 'youtube' in (film_data.get('url') or '').lower() else None,
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
        
        # Remove None values to let Supabase use defaults
        return {k: v for k, v in title_record.items() if v is not None}
    
    async def sync_film(self, film_data: Dict) -> Optional[Dict]:
        """
        Sync a film analysis to Supabase. 
        Performs upsert based on aicinedb_film_id using Supabase's native upsert.
        
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
            
            # Log what we're sending
            logger.info(f"📤 Sending to Supabase: genres={title_record.get('genres')}, moods={title_record.get('moods')}, rating={title_record.get('rating_average')}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use Supabase's native upsert with on_conflict
                upsert_url = f"{self.rest_url}/titles"
                
                # Set headers for upsert operation with UTF-8 encoding
                upsert_headers = {
                    **self.headers,
                    "Prefer": "return=representation,resolution=merge-duplicates",
                    "Content-Type": "application/json; charset=utf-8"
                }
                
                # Ensure proper JSON encoding for Turkish characters
                json_data = json.dumps(title_record, ensure_ascii=False)
                
                response = await client.post(
                    upsert_url,
                    headers=upsert_headers,
                    params={"on_conflict": "aicinedb_film_id"},
                    content=json_data.encode('utf-8')
                )
                response.raise_for_status()
                result = response.json()
                
                if result:
                    record_id = result[0].get('id', 'unknown')
                    logger.info(f"✓ Synced film to Supabase (id: {record_id})")
                    return result[0]
                
                return None
                
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