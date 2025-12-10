"""
Gemini Title Extractor
Uses Google Gemini AI to extract film/movie titles from tweet text
"""
import os
import logging
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI not available")


class GeminiTitleExtractor:
    """Extract film titles from tweet text using Gemini AI"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash-lite"):
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
        
        logger.info(f"✓ Gemini title extractor initialized with {model_name}")
    
    def extract_title(self, tweet_text: str) -> Dict:
        """
        Extract film/movie title from tweet text
        
        Args:
            tweet_text: Tweet text content (preferably sanitized)
            
        Returns:
            Dict with extracted title and confidence score
            {
                'title': str,
                'confidence': str,  # 'high', 'medium', 'low', 'none'
                'raw_response': str
            }
        """
        if not tweet_text or len(tweet_text.strip()) < 3:
            logger.warning("Tweet text is too short or empty")
            return {
                'title': 'Unknown Title',
                'confidence': 'none',
                'raw_response': 'Empty tweet text'
            }
        
        try:
            logger.info(f"🎬 Extracting film title from tweet: {tweet_text[:100]}...")
            
            prompt = self._build_extraction_prompt(tweet_text)
            
            # Generate response
            response = self.model.generate_content(prompt)
            raw_response = response.text.strip()
            
            # Parse the response
            result = self._parse_response(raw_response, tweet_text)
            
            logger.info(f"✅ Extracted title: '{result['title']}' (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Title extraction failed: {e}")
            return {
                'title': 'Unknown Title',
                'confidence': 'none',
                'raw_response': str(e)
            }
    
    def _build_extraction_prompt(self, tweet_text: str) -> str:
        """
        Build prompt for title extraction
        Supports both Turkish and English
        
        Args:
            tweet_text: Tweet text
            
        Returns:
            Prompt string
        """
        prompt = f"""Analyze this tweet and extract the film/movie title being discussed.

Tweet: "{tweet_text}"

Instructions:
1. Look for explicit film/movie mentions (e.g., "Just watched Inception", "Inception is amazing")
2. Extract ONLY the film title, nothing else
3. Do NOT include years, director names, or extra context
4. If the tweet mentions multiple films, extract the primary one
5. Support both Turkish and English tweets
6. If no clear film title is found, respond with exactly: "Unknown"

Examples:
- "Just finished watching Inception (2010) 🎬" → "Inception"
- "Inception is a masterpiece!" → "Inception"
- "Yeni izlediğim film Amelie harika bir sinema deneyimiydi" → "Amelie"
- "I love this movie 🎬" → "Unknown"
- "Great cinematography!" → "Unknown"

Respond with ONLY the film title or "Unknown". No explanations, no extra text.

Film title:"""
        
        return prompt
    
    def _parse_response(self, raw_response: str, original_tweet: str) -> Dict:
        """
        Parse Gemini response and determine confidence
        
        Args:
            raw_response: Raw response from Gemini
            original_tweet: Original tweet text for validation
            
        Returns:
            Dict with title, confidence, and raw response
        """
        # Clean the response
        title = raw_response.strip()
        
        # Remove common prefixes/suffixes (English and Turkish)
        # English: "Film title:", "Title:", "Answer:", "Response:"
        # Turkish: "Film adı:", "Film başlığı:", "Başlık:", "Cevap:"
        title = re.sub(
            r'^(Film title:|Film adı:|Film başlığı:|Title:|Başlık:|Answer:|Response:|Cevap:)\s*',
            '',
            title,
            flags=re.IGNORECASE
        )
        title = re.sub(r'[.!?]+$', '', title)
        title = title.strip(' "\'')
        
        # Check if it's "Unknown" or similar (English and Turkish)
        unknown_patterns = ['unknown', 'none', 'n/a', 'not found', 'no title', 'bilinmiyor', 'yok', 'bulunamadı']
        if title.lower() in unknown_patterns:
            return {
                'title': 'Unknown Title',
                'confidence': 'none',
                'raw_response': raw_response
            }
        
        # Determine confidence based on validation
        confidence = self._calculate_confidence(title, original_tweet, raw_response)
        
        # If confidence is none, default to Unknown Title
        if confidence == 'none':
            title = 'Unknown Title'
        
        return {
            'title': title,
            'confidence': confidence,
            'raw_response': raw_response
        }
    
    def _calculate_confidence(self, title: str, original_tweet: str, raw_response: str) -> str:
        """
        Calculate confidence level of the extraction
        
        Args:
            title: Extracted title
            original_tweet: Original tweet text
            raw_response: Raw response from Gemini
            
        Returns:
            Confidence level: 'high', 'medium', 'low', or 'none'
        """
        # If title is empty or too short
        if not title or len(title) < 2:
            return 'none'
        
        # If title is too long (probably not a movie title)
        if len(title) > 100:
            return 'low'
        
        # Convert to lowercase for comparison
        title_lower = title.lower()
        tweet_lower = original_tweet.lower()
        
        # High confidence: Title appears verbatim in tweet
        if title_lower in tweet_lower:
            return 'high'
        
        # Medium confidence: Most words from title appear in tweet
        title_words = set(title_lower.split())
        tweet_words = set(tweet_lower.split())
        
        if len(title_words) > 0:
            overlap = len(title_words & tweet_words) / len(title_words)
            
            if overlap >= 0.8:
                return 'high'
            elif overlap >= 0.5:
                return 'medium'
            elif overlap >= 0.3:
                return 'low'
        
        # Low confidence: Title seems reasonable but no strong match
        # Check if it looks like a movie title (starts with capital, reasonable length)
        if title[0].isupper() and 2 <= len(title) <= 50:
            return 'medium'
        
        return 'low'
    
    def extract_title_batch(self, tweet_texts: list) -> list:
        """
        Extract titles from multiple tweets
        
        Args:
            tweet_texts: List of tweet texts
            
        Returns:
            List of extraction results
        """
        results = []
        
        for tweet_text in tweet_texts:
            result = self.extract_title(tweet_text)
            results.append(result)
        
        return results
