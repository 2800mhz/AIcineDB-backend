"""
Narrative Analysis using Google Gemini AI
Provides deep narrative breakdown, themes, and story structure analysis
"""
import os
import json
import logging
from typing import Dict, List, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


async def test_gemini_connection() -> bool:
    """Test Gemini API connection"""
    if not GEMINI_API_KEY:
        return False
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello")
        return True
    except Exception as e:
        logger.error(f"Gemini connection test failed: {e}")
        return False


class GeminiNarrativeAnalyzer:
    """
    Narrative analyzer using Gemini AI
    Provides professional film analysis including themes, structure, and tone
    """
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.model = genai.GenerativeModel('gemini-pro')
        logger.info("✓ Gemini narrative analyzer initialized")
    
    async def analyze_narrative(
        self,
        transcript: str,
        title: str,
        duration: float,
        visual_context: Optional[Dict] = None
    ) -> Dict:
        """
        Complete narrative analysis of a film
        
        Args:
            transcript: Full transcript text
            title: Film title
            duration: Duration in seconds
            visual_context: Optional dict with shot info, colors, etc.
            
        Returns:
            Complete narrative analysis dict
        """
        
        if not transcript or len(transcript) < 50:
            logger.warning("Transcript too short for meaningful analysis")
            return self._default_analysis()
        
        try:
            # Build context
            context = self._build_context(transcript, title, duration, visual_context)
            
            # Generate analysis
            logger.info("🤖 Analyzing narrative with Gemini...")
            
            analysis = {}
            
            # 1. Logline & Synopsis
            analysis['logline'], analysis['synopsis'] = await self._generate_logline_synopsis(context)
            
            # 2. Themes
            analysis['themes'] = await self._extract_themes(context)
            
            # 3. Genre & Tone
            analysis['genre'], analysis['tone'] = await self._classify_genre_tone(context)
            
            # 4. Story Structure
            analysis['story_beats'] = await self._extract_story_beats(context)
            analysis['act_structure'] = await self._analyze_act_structure(context)
            
            # 5. Conflict & Stakes
            analysis['conflict_type'] = await self._identify_conflict(context)
            
            # 6. Emotional Arc
            analysis['emotional_arc'] = await self._trace_emotional_arc(context)
            
            logger.info("✓ Narrative analysis complete")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Narrative analysis failed: {e}")
            return self._default_analysis()
    
    def _build_context(
        self,
        transcript: str,
        title: str,
        duration: float,
        visual_context: Optional[Dict]
    ) -> str:
        """Build context string for Gemini"""
        
        context = f"""
Film Title: {title}
Duration: {duration/60:.1f} minutes

Transcript:
{transcript[:8000]}  # Limit to avoid token limits

"""
        
        if visual_context:
            context += f"""
Visual Context:
- Total shots: {visual_context.get('total_shots', 'unknown')}
- Primary colors: {', '.join(visual_context.get('colors', [])[:5])}
- Primary lighting: {visual_context.get('lighting', 'unknown')}
"""
        
        return context
    
    async def _generate_logline_synopsis(self, context: str) -> tuple:
        """Generate logline and synopsis"""
        
        prompt = f"""
Based on this film:

{context}

Generate:
1. A one-sentence logline (20-30 words) that captures the core story
2. A brief synopsis (100-150 words) with beginning, middle, and end

Return ONLY valid JSON in this exact format:
{{
    "logline": "...",
    "synopsis": "..."
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(self._extract_json(response.text))
            return result['logline'], result['synopsis']
        except Exception as e:
            logger.error(f"Logline/synopsis generation failed: {e}")
            return "A story unfolds.", "Synopsis unavailable."
    
    async def _extract_themes(self, context: str) -> List[Dict]:
        """Extract major themes"""
        
        prompt = f"""
Based on this film:

{context}

Identify the TOP 5 major themes present in this film.

For each theme, provide:
- name: theme name (2-3 words)
- description: brief explanation (1 sentence)
- prevalence: how dominant is this theme (0.0 to 1.0)

Common themes include: identity, power, love, isolation, freedom, corruption, 
hope, fear, sacrifice, revenge, redemption, technology, nature, society, etc.

Return ONLY valid JSON array:
[
    {{"name": "...", "description": "...", "prevalence": 0.8}},
    ...
]
"""
        
        try:
            response = self.model.generate_content(prompt)
            themes = json.loads(self._extract_json(response.text))
            return themes[:5]
        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            return [
                {"name": "mystery", "description": "Unknown themes", "prevalence": 0.5}
            ]
    
    async def _classify_genre_tone(self, context: str) -> tuple:
        """Classify genre and tone"""
        
        prompt = f"""
Based on this film:

{context}

Classify:
1. Genre: Select 1-3 genres (drama, comedy, thriller, horror, sci-fi, fantasy, romance, action, documentary, experimental, etc.)
2. Tone: Select 2-4 tones (dark, lighthearted, melancholic, tense, whimsical, serious, satirical, nostalgic, etc.)

Return ONLY valid JSON:
{{
    "genre": ["genre1", "genre2"],
    "tone": ["tone1", "tone2", "tone3"]
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            result = json.loads(self._extract_json(response.text))
            return result['genre'], result['tone']
        except Exception as e:
            logger.error(f"Genre/tone classification failed: {e}")
            return ["drama"], ["serious"]
    
    async def _extract_story_beats(self, context: str) -> List[Dict]:
        """Extract story beats"""
        
        prompt = f"""
Based on this film:

{context}

Identify 5-8 major story beats (key narrative moments).

For each beat, provide:
- timestamp: approximate time in seconds (estimate based on position)
- beat_type: (inciting_incident, turning_point, midpoint, climax, resolution, etc.)
- description: what happens (1 sentence)

Return ONLY valid JSON array:
[
    {{"timestamp": 120, "beat_type": "inciting_incident", "description": "..."}},
    ...
]
"""
        
        try:
            response = self.model.generate_content(prompt)
            beats = json.loads(self._extract_json(response.text))
            return beats
        except Exception as e:
            logger.error(f"Story beat extraction failed: {e}")
            return []
    
    async def _analyze_act_structure(self, context: str) -> Dict:
        """Analyze three-act structure"""
        
        prompt = f"""
Based on this film:

{context}

Analyze the three-act structure:

Act 1 (Setup): What's established?
Act 2 (Confrontation): What's the main conflict?
Act 3 (Resolution): How does it conclude?

Also identify:
- Is the structure clear or unconventional?
- Are there any structural weaknesses?

Return ONLY valid JSON:
{{
    "act_1": {{"summary": "...", "duration_pct": 0.25}},
    "act_2": {{"summary": "...", "duration_pct": 0.50}},
    "act_3": {{"summary": "...", "duration_pct": 0.25}},
    "structure_clarity": "clear/unconventional/weak",
    "notes": "..."
}}
"""
        
        try:
            response = self.model.generate_content(prompt)
            structure = json.loads(self._extract_json(response.text))
            return structure
        except Exception as e:
            logger.error(f"Act structure analysis failed: {e}")
            return {
                "act_1": {"summary": "Unknown", "duration_pct": 0.33},
                "act_2": {"summary": "Unknown", "duration_pct": 0.34},
                "act_3": {"summary": "Unknown", "duration_pct": 0.33},
                "structure_clarity": "unknown"
            }
    
    async def _identify_conflict(self, context: str) -> str:
        """Identify type of conflict"""
        
        prompt = f"""
Based on this film:

{context}

What is the PRIMARY type of conflict?

Options:
- person_vs_person
- person_vs_self
- person_vs_society
- person_vs_nature
- person_vs_technology
- person_vs_supernatural
- person_vs_fate

Return ONLY the conflict type (e.g., "person_vs_self")
"""
        
        try:
            response = self.model.generate_content(prompt)
            conflict = response.text.strip().lower().replace(" ", "_")
            return conflict if "person_vs" in conflict else "person_vs_person"
        except Exception as e:
            logger.error(f"Conflict identification failed: {e}")
            return "person_vs_person"
    
    async def _trace_emotional_arc(self, context: str) -> List[float]:
        """Trace emotional arc across the film"""
        
        prompt = f"""
Based on this film:

{context}

Trace the emotional journey across 10 points (beginning to end).

For each point, rate the emotional tone from -1.0 (very negative) to +1.0 (very positive).

Return ONLY a JSON array of 10 numbers:
[0.1, 0.3, -0.2, -0.5, -0.8, -0.4, 0.0, 0.4, 0.7, 0.9]
"""
        
        try:
            response = self.model.generate_content(prompt)
            arc = json.loads(self._extract_json(response.text))
            
            # Ensure it's 10 numbers
            if isinstance(arc, list) and len(arc) == 10:
                return [float(x) for x in arc]
            else:
                return [0.0] * 10
        except Exception as e:
            logger.error(f"Emotional arc tracing failed: {e}")
            return [0.0] * 10
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from markdown code blocks if present"""
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    def _default_analysis(self) -> Dict:
        """Return default analysis when Gemini fails"""
        return {
            'logline': 'A story unfolds in this film.',
            'synopsis': 'Analysis unavailable due to insufficient data or API limitations.',
            'themes': [
                {'name': 'mystery', 'description': 'Unknown themes', 'prevalence': 0.5}
            ],
            'genre': ['drama'],
            'tone': ['serious'],
            'story_beats': [],
            'act_structure': {
                'act_1': {'summary': 'Unknown', 'duration_pct': 0.33},
                'act_2': {'summary': 'Unknown', 'duration_pct': 0.34},
                'act_3': {'summary': 'Unknown', 'duration_pct': 0.33},
                'structure_clarity': 'unknown'
            },
            'conflict_type': 'person_vs_person',
            'emotional_arc': [0.0] * 10
        }
