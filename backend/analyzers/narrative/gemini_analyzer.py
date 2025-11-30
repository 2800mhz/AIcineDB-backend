"""
Narrative Analysis with Google Gemini AI
Analyzes screenplay structure, themes, and story beats
"""
import os
import logging
from typing import Dict, Optional, List
import json

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available")


class GeminiNarrativeAnalyzer:
    """Narrative analysis using Google Gemini AI"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        Args:
            model_name: Gemini model to use
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package is required")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        
        logger.info(f"✓ Gemini analyzer initialized with {model_name}")
    
    async def analyze_narrative(
        self,
        transcript: str,
        title: str,
        duration: float,
        visual_context: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze narrative structure and themes
        
        Args:
            transcript: Full transcript text
            title: Film title
            duration: Duration in seconds
            visual_context: Optional visual information (colors, lighting, shots)
            
        Returns:
            Dictionary with narrative analysis
        """
        try:
            logger.info(f"Analyzing narrative for '{title}'...")
            
            # Build prompt
            prompt = self._build_narrative_prompt(
                transcript,
                title,
                duration,
                visual_context
            )
            
            # Generate analysis
            response = self.model.generate_content(prompt)
            
            # Parse response
            analysis = self._parse_narrative_response(response.text)
            
            logger.info(f"✓ Narrative analysis complete")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Narrative analysis failed: {e}")
            return self._empty_analysis()
    
    def _build_narrative_prompt(
        self,
        transcript: str,
        title: str,
        duration: float,
        visual_context: Optional[Dict]
    ) -> str:
        """Build comprehensive analysis prompt"""
        
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"
        
        prompt = f"""You are an expert film analyst. Analyze the following film comprehensively.

**Film:** {title}
**Duration:** {duration_str}

**Transcript:**
{transcript[:8000]}  # Limit to ~8000 chars to fit context

"""
        
        if visual_context:
            prompt += f"""
**Visual Context:**
- Total Shots: {visual_context.get('total_shots', 'Unknown')}
- Dominant Colors: {', '.join(visual_context.get('colors', [])[:5])}
- Lighting: {visual_context.get('lighting', 'Unknown')}

"""
        
        prompt += """
**Please provide a detailed analysis in JSON format with the following structure:**

```json
{
  "summary": "Brief 2-3 sentence summary of the film",
  "genre": "Primary genre",
  "themes": ["theme1", "theme2", "theme3"],
  "tone": "Overall tone/mood of the film",
  "structure": {
    "act1": "Description of setup (first 25%)",
    "act2": "Description of confrontation (middle 50%)",
    "act3": "Description of resolution (final 25%)"
  },
  "story_beats": [
    {
      "beat": "Opening Image",
      "description": "What happens",
      "timestamp_estimate": "0:00 - 2:00"
    },
    {
      "beat": "Inciting Incident",
      "description": "What happens",
      "timestamp_estimate": "5:00 - 8:00"
    }
  ],
  "character_analysis": {
    "protagonist": "Who and their arc",
    "antagonist": "Who and their role",
    "supporting": "Key supporting characters"
  },
  "cinematography_notes": "How visual style supports the narrative",
  "audio_notes": "How dialogue/sound supports the story",
  "key_quotes": ["memorable quote 1", "memorable quote 2"],
  "emotional_arc": "How the emotional journey progresses"
}
```

Provide ONLY the JSON, no other text.
"""
        
        return prompt
    
    def _parse_narrative_response(self, response_text: str) -> Dict:
        """Parse Gemini response into structured data"""
        try:
            # Clean response - extract JSON if wrapped in markdown
            text = response_text.strip()
            
            # Remove markdown code blocks if present
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            # Parse JSON
            analysis = json.loads(text)
            
            # Validate required fields
            required = ["summary", "genre", "themes", "tone"]
            for field in required:
                if field not in analysis:
                    logger.warning(f"Missing field: {field}")
                    analysis[field] = "Not analyzed"
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            
            # Return basic analysis from text
            return {
                "summary": response_text[:200],
                "genre": "Unknown",
                "themes": [],
                "tone": "Unknown",
                "raw_response": response_text
            }
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "summary": "Analysis not available",
            "genre": "Unknown",
            "themes": [],
            "tone": "Unknown",
            "structure": {},
            "story_beats": [],
            "character_analysis": {},
            "cinematography_notes": "",
            "audio_notes": "",
            "key_quotes": [],
            "emotional_arc": ""
        }
    
    def analyze_themes(self, transcript: str) -> List[str]:
        """
        Quick theme extraction
        
        Args:
            transcript: Full transcript
            
        Returns:
            List of themes
        """
        try:
            prompt = f"""Extract the main themes from this film transcript. 
Return ONLY a JSON array of themes, like: ["theme1", "theme2", "theme3"]

Transcript:
{transcript[:4000]}
"""
            
            response = self.model.generate_content(prompt)
            themes = json.loads(response.text)
            
            return themes if isinstance(themes, list) else []
            
        except Exception as e:
            logger.error(f"Theme extraction failed: {e}")
            return []
    
    def generate_summary(self, transcript: str, max_sentences: int = 3) -> str:
        """
        Generate concise summary
        
        Args:
            transcript: Full transcript
            max_sentences: Maximum sentences in summary
            
        Returns:
            Summary text
        """
        try:
            prompt = f"""Summarize this film in {max_sentences} sentences or less.

Transcript:
{transcript[:4000]}

Summary:"""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return "Summary not available"
