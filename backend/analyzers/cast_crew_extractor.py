"""
Cast & Crew Extractor
Extracts cast and crew information from:
1. Video end credits (OCR + Gemini)
2.  Video description (Gemini parsing)
3. Character face matching
"""
import re
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import google.generativeai as genai
from PIL import Image

logger = logging.getLogger(__name__)


class CastCrewExtractor:
    """Extract cast and crew from video credits and descriptions"""
    
    def __init__(self, gemini_api_key: str):
        """Initialize with Gemini API"""
        genai. configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self. vision_model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    async def extract_all(
        self,
        video_path: str,
        description: str,
        duration: float,
        frames_dir: str,
        characters: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract cast & crew from all available sources
        
        Args:
            video_path: Path to video file
            description: Video description from YouTube/Vimeo
            duration: Video duration in seconds
            frames_dir: Directory containing extracted frames
            characters: Detected characters from face recognition
            
        Returns:
            Complete cast & crew data
        """
        results = {
            'cast': [],
            'crew': [],
            'sources': [],
            'confidence': 0.0
        }
        
        # 1. Extract from video description
        logger.info("📝 Extracting cast & crew from description...")
        desc_result = await self._extract_from_description(description)
        if desc_result:
            results['cast'].extend(desc_result. get('cast', []))
            results['crew'].extend(desc_result.get('crew', []))
            results['sources']. append('description')
        
        # 2.  Extract from end credits (last 10% of video or last 30 seconds)
        logger.info("🎬 Analyzing end credits...")
        credits_result = await self._extract_from_credits(
            frames_dir, 
            duration
        )
        if credits_result:
            # Merge with existing, avoiding duplicates
            results['cast'] = self._merge_people(results['cast'], credits_result.get('cast', []))
            results['crew'] = self._merge_people(results['crew'], credits_result.get('crew', []))
            results['sources'].append('credits')
        
        # 3.  Match characters to cast if we have face data
        if characters:
            logger.info("🎭 Matching characters to cast...")
            results['cast'] = self._match_characters_to_cast(
                results['cast'], 
                characters
            )
            results['sources'].append('character_matching')
        
        # 4. Calculate confidence score
        results['confidence'] = self._calculate_confidence(results)
        
        # 5. Clean and deduplicate
        results['cast'] = self._deduplicate_people(results['cast'])
        results['crew'] = self._deduplicate_people(results['crew'])
        
        logger.info(f"✅ Found {len(results['cast'])} cast, {len(results['crew'])} crew members")
        
        return results
    
    async def _extract_from_description(self, description: str) -> Optional[Dict]:
        """
        Extract cast & crew from video description using Gemini
        
        Args:
            description: Video description text
            
        Returns:
            Dict with cast and crew lists
        """
        if not description or len(description) < 10:
            return None
        
        prompt = """Analyze this video description and extract cast & crew information. 

VIDEO DESCRIPTION:
\"\"\"
{description}
\"\"\"

Extract all people mentioned with their roles.  Look for:
- Actors/Cast (people appearing in the video)
- Director(s)
- Writer(s)/Screenwriter(s)
- Producer(s)
- Cinematographer/DOP
- Editor
- Composer/Music
- Voice actors
- Any other crew roles

Return JSON format:
{{
    "cast": [
        {{
            "name": "Person Name",
            "role": "character name or 'Actor'",
            "type": "actor"
        }}
    ],
    "crew": [
        {{
            "name": "Person Name",
            "role": "Director",
            "department": "directing"
        }}
    ]
}}

If no cast/crew information found, return empty arrays.
Only include names that are clearly people (not company names).
""".format(description=description[:3000])  # Limit description length
        
        try:
            response = await self.model. generate_content_async(prompt)
            result_text = response.text
            
            # Extract JSON from response
            json_match = re. search(r'\{[\s\S]*\}', result_text)
            if json_match:
                import json
                return json.loads(json_match.group())
            
        except Exception as e:
            logger.error(f"Failed to extract from description: {e}")
        
        return None
    
    async def _extract_from_credits(
        self, 
        frames_dir: str, 
        duration: float
    ) -> Optional[Dict]:
        """
        Extract cast & crew from end credits frames
        
        Args:
            frames_dir: Directory with extracted frames
            duration: Video duration
            
        Returns:
            Dict with cast and crew from credits
        """
        frames_path = Path(frames_dir)
        if not frames_path. exists():
            return None
        
        # Get frames from last 15% of video (likely credits)
        all_frames = sorted(frames_path. glob("*.jpg")) + sorted(frames_path.glob("*. png"))
        if not all_frames:
            return None
        
        # Calculate which frames are from the end
        total_frames = len(all_frames)
        credits_start = int(total_frames * 0.85)  # Last 15%
        credit_frames = all_frames[credits_start:]
        
        if not credit_frames:
            return None
        
        # Sample up to 10 frames from credits section
        step = max(1, len(credit_frames) // 10)
        sampled_frames = credit_frames[::step][:10]
        
        # Analyze credit frames with Gemini Vision
        all_cast = []
        all_crew = []
        
        for frame_path in sampled_frames:
            try:
                result = await self._analyze_credit_frame(frame_path)
                if result:
                    all_cast.extend(result.get('cast', []))
                    all_crew.extend(result. get('crew', []))
            except Exception as e:
                logger.warning(f"Failed to analyze frame {frame_path}: {e}")
                continue
        
        return {
            'cast': all_cast,
            'crew': all_crew
        }
    
    async def _analyze_credit_frame(self, frame_path: Path) -> Optional[Dict]:
        """
        Analyze a single credit frame with Gemini Vision
        
        Args:
            frame_path: Path to frame image
            
        Returns:
            Dict with cast/crew from this frame
        """
        try:
            image = Image.open(frame_path)
            
            prompt = """Analyze this video frame.  If it shows credits/titles, extract the names and roles.

Look for:
- Cast/Actor names with character names
- Director, Writer, Producer credits
- Any crew credits (Editor, Cinematographer, Music, etc.)

Return JSON:
{
    "is_credits": true/false,
    "cast": [{"name": ".. .", "role": "...", "type": "actor"}],
    "crew": [{"name": "...", "role": "...", "department": "... "}]
}

If this is not a credits frame, return {"is_credits": false, "cast": [], "crew": []}
Only extract clearly visible text. Don't guess."""

            response = await self.vision_model.generate_content_async([prompt, image])
            result_text = response.text
            
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                import json
                data = json.loads(json_match.group())
                if data.get('is_credits'):
                    return data
                    
        except Exception as e:
            logger.warning(f"Credit frame analysis failed: {e}")
        
        return None
    
    def _match_characters_to_cast(
        self, 
        cast: List[Dict], 
        characters: List[Dict]
    ) -> List[Dict]:
        """
        Match detected characters to cast members
        
        Args:
            cast: Extracted cast list
            characters: Detected characters from face recognition
            
        Returns:
            Updated cast list with character info
        """
        # Sort characters by screen time
        sorted_chars = sorted(
            characters, 
            key=lambda x: x.get('screen_time', 0), 
            reverse=True
        )
        
        # If we have cast names but no character info, try to match by order
        for i, char in enumerate(sorted_chars):
            char_data = {
                'character_id': char.get('id'),
                'screen_time': char. get('screen_time', 0),
                'appearance_count': char.get('appearance_count', 0),
                'thumbnail': char.get('thumbnail_path')
            }
            
            # Try to match to existing cast member
            if i < len(cast):
                cast[i]. update(char_data)
            else:
                # Add as unknown cast member
                cast. append({
                    'name': f"Unknown Actor {i+1}",
                    'role': char. get('name', f'Character {i+1}'),
                    'type': 'actor',
                    **char_data
                })
        
        return cast
    
    def _merge_people(
        self, 
        existing: List[Dict], 
        new: List[Dict]
    ) -> List[Dict]:
        """Merge two lists of people, avoiding duplicates"""
        existing_names = {p. get('name', '').lower() for p in existing}
        
        for person in new:
            name = person.get('name', '').lower()
            if name and name not in existing_names:
                existing.append(person)
                existing_names.add(name)
        
        return existing
    
    def _deduplicate_people(self, people: List[Dict]) -> List[Dict]:
        """Remove duplicate entries"""
        seen = set()
        unique = []
        
        for person in people:
            name = person.get('name', '').lower(). strip()
            if name and name not in seen:
                seen.add(name)
                unique.append(person)
        
        return unique
    
    def _calculate_confidence(self, results: Dict) -> float:
        """Calculate confidence score based on sources and data quality"""
        score = 0.0
        
        # More sources = higher confidence
        source_count = len(results. get('sources', []))
        score += min(source_count * 0.2, 0.6)
        
        # More people found = higher confidence
        people_count = len(results. get('cast', [])) + len(results.get('crew', []))
        if people_count > 0:
            score += min(people_count * 0.05, 0.3)
        
        # Has key crew = higher confidence
        crew_roles = {p.get('role', '').lower() for p in results.get('crew', [])}
        key_roles = {'director', 'writer', 'producer', 'cinematographer'}
        if crew_roles & key_roles:
            score += 0.1
        
        return min(score, 1.0)


# Integration with main pipeline
async def extract_cast_crew_for_film(
    video_path: str,
    description: str,
    duration: float,
    frames_dir: str,
    characters: List[Dict],
    gemini_api_key: str
) -> Dict:
    """
    Main function to extract cast & crew for a film
    
    Args:
        video_path: Path to video
        description: Video description
        duration: Duration in seconds
        frames_dir: Frames directory
        characters: Detected characters
        gemini_api_key: Gemini API key
        
    Returns:
        Complete cast & crew data
    """
    extractor = CastCrewExtractor(gemini_api_key)
    return await extractor.extract_all(
        video_path=video_path,
        description=description,
        duration=duration,
        frames_dir=frames_dir,
        characters=characters
    )