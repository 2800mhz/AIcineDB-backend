"""
Gemini Title Extractor - FIXED VERSION
Uses Google Gemini AI to extract film/movie titles from tweet text
Handles timeouts and improves prompt engineering
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
    
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        """
        Args:
            model_name: Gemini model to use
                - gemini-2.0-flash-exp (recommended, fastest)
                - gemini-1.5-flash (stable, fast)
                - gemini-1.5-pro (slower but more accurate)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai package is required. Install: pip install google-generativeai")
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=api_key)
        
        # ✅ Configure generation settings to prevent timeout
        generation_config = {
            "temperature": 0.1,  # Low temperature for consistent extraction
            "top_p": 0.8,
            "top_k": 20,
            "max_output_tokens": 100,  # Title should be short
        }
        
        # ✅ Set timeout in request options
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        self.model_name = model_name
        
        logger.info(f"✓ Gemini title extractor initialized with {model_name}")
    
    def extract_title(self, tweet_text: str, timeout: int = 30) -> Dict:
        """
        Extract film/movie title from tweet text
        
        Args:
            tweet_text: Tweet text content (preferably sanitized)
            timeout: Request timeout in seconds (default: 30)
            
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
            
            # ✅ Generate with timeout and retry logic
            try:
                response = self.model.generate_content(
                    prompt,
                    request_options={"timeout": timeout}
                )
                raw_response = response.text.strip()
                
            except Exception as gen_error:
                # Check if it's a timeout error
                if "timed out" in str(gen_error).lower() or "504" in str(gen_error):
                    logger.warning(f"⏰ Gemini request timed out after {timeout}s, using fallback")
                    # Try to extract from tweet text directly as fallback
                    fallback_title = self._fallback_extraction(tweet_text)
                    return {
                        'title': fallback_title,
                        'confidence': 'low',
                        'raw_response': f'Timeout fallback: {gen_error}'
                    }
                else:
                    raise gen_error
            
            # Parse the response
            result = self._parse_response(raw_response, tweet_text)
            
            logger.info(f"✅ Extracted title: '{result['title']}' (confidence: {result['confidence']})")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Title extraction failed: {e}")
            
            # ✅ Fallback to regex-based extraction
            fallback_title = self._fallback_extraction(tweet_text)
            
            return {
                'title': fallback_title,
                'confidence': 'low' if fallback_title != 'Unknown Title' else 'none',
                'raw_response': f'Error fallback: {str(e)}'
            }
    
    def _build_extraction_prompt(self, tweet_text: str) -> str:
        """
        Build IMPROVED prompt for title extraction
        Shorter prompt = faster response = less timeout risk
        
        Args:
            tweet_text: Tweet text
            
        Returns:
            Prompt string
        """
        # ✅ SHORTER, MORE DIRECT PROMPT
        prompt = f"""Extract the film/movie/video title from this tweet.

Tweet: "{tweet_text}"

Rules:
- Look for quoted titles or obvious film names
- Return ONLY the title text, nothing else
- If unsure or no title found, return: "Unknown"
- No explanations, no formatting

Title:"""
        
        return prompt
    
    def _fallback_extraction(self, tweet_text: str) -> str:
        """
        Fallback title extraction using regex patterns
        Used when Gemini fails or times out
        
        Args:
            tweet_text: Original tweet text
            
        Returns:
            Extracted title or 'Unknown Title'
        """
        logger.info("🔍 Using fallback regex extraction...")
        
        # Pattern 1: Quoted text (most reliable)
        quoted_patterns = [
            r'"([^"]+)"',  # Double quotes
            r"'([^']+)'",  # Single quotes
            r'«([^»]+)»',  # French quotes
            r'"([^"]+)"',  # Smart quotes
        ]
        
        for pattern in quoted_patterns:
            match = re.search(pattern, tweet_text)
            if match:
                title = match.group(1).strip()
                if 5 <= len(title) <= 80:  # Reasonable title length
                    logger.info(f"✓ Fallback found quoted title: {title}")
                    return title
        
        # Pattern 2: After indicators like "film:", "movie:", etc.
        indicator_pattern = r'(?:film|movie|short|watch|presenting):\s*([A-Z][^\n.!?]{2,60})'
        match = re.search(indicator_pattern, tweet_text, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            logger.info(f"✓ Fallback found after indicator: {title}")
            return title
        
        # Pattern 3: Capitalized phrase at start of tweet
        start_pattern = r'^([A-Z][A-Za-z\s\-]{2,50})(?:\s*-|\s*:|\s*by)'
        match = re.search(start_pattern, tweet_text)
        if match:
            title = match.group(1).strip()
            logger.info(f"✓ Fallback found at start: {title}")
            return title
        
        logger.warning("⚠️ Fallback extraction found nothing")
        return 'Unknown Title'
    
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
        
        # Remove common prefixes (Turkish + English)
        title = re.sub(
            r'^(Film title:|Film adı:|Film başlığı:|Title:|Başlık:|Answer:|Response:|Cevap:)\s*',
            '',
            title,
            flags=re.IGNORECASE
        )
        title = re.sub(r'[.!?]+$', '', title)
        title = title.strip(' "\'«»""')
        
        # Check for "Unknown" responses (multi-language)
        unknown_patterns = [
            'unknown', 'none', 'n/a', 'not found', 'no title', 'no film',
            'bilinmiyor', 'yok', 'bulunamadı', 'başlık yok'
        ]
        if title.lower() in unknown_patterns:
            return {
                'title': 'Unknown Title',
                'confidence': 'none',
                'raw_response': raw_response
            }
        
        # Validate and calculate confidence
        confidence = self._calculate_confidence(title, original_tweet, raw_response)
        
        # If confidence is none or title is invalid, mark as unknown
        if confidence == 'none' or len(title) < 2 or len(title) > 150:
            title = 'Unknown Title'
            confidence = 'none'
        
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
        # Basic validation
        if not title or len(title) < 2:
            return 'none'
        
        if len(title) > 150:  # Too long
            return 'low'
        
        # Normalize for comparison
        title_lower = title.lower()
        tweet_lower = original_tweet.lower()
        
        # HIGH: Title appears verbatim in tweet
        if title_lower in tweet_lower:
            return 'high'
        
        # MEDIUM: Most words overlap
        title_words = set(title_lower.split())
        tweet_words = set(tweet_lower.split())
        
        if len(title_words) > 0:
            overlap_ratio = len(title_words & tweet_words) / len(title_words)
            
            if overlap_ratio >= 0.7:
                return 'high'
            elif overlap_ratio >= 0.4:
                return 'medium'
            elif overlap_ratio >= 0.2:
                return 'low'
        
        # MEDIUM: Looks like a proper title (capitalized, reasonable length)
        if title[0].isupper() and 3 <= len(title) <= 80:
            return 'medium'
        
        # LOW: Everything else
        return 'low'
    
    def extract_title_batch(self, tweet_texts: list, timeout: int = 30) -> list:
        """
        Extract titles from multiple tweets
        
        Args:
            tweet_texts: List of tweet texts
            timeout: Per-request timeout in seconds
            
        Returns:
            List of extraction results
        """
        results = []
        
        for idx, tweet_text in enumerate(tweet_texts, 1):
            logger.info(f"Processing tweet {idx}/{len(tweet_texts)}")
            result = self.extract_title(tweet_text, timeout=timeout)
            results.append(result)
        
        return results


# ✅ Example usage
if __name__ == "__main__":
    # Test the extractor
    extractor = GeminiTitleExtractor()
    
    test_tweets = [
        'Just watched "Inception" - mind-blowing!',
        'Amelie is such a beautiful film 🎬',
        'Yeni izlediğim film "Bir Zamanlar Anadolu\'da" muhteşemdi',
        'Great cinematography but no clear title here'
    ]
    
    for tweet in test_tweets:
        result = extractor.extract_title(tweet)
        print(f"\nTweet: {tweet}")
        print(f"Title: {result['title']}")
        print(f"Confidence: {result['confidence']}")