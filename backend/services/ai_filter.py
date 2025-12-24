"""
AI Filter Service
AI-powered filtering and duplicate detection for festivals and news using OpenAI
"""
import os
import logging
from typing import List, Dict, Optional, Tuple
import asyncio
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Try to import OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ OpenAI library not available. AI filtering will be disabled.")


class AIFilter:
    """AI-powered filtering and duplicate detection service"""
    
    def __init__(self):
        self.enabled = os.getenv("AI_FILTER_ENABLED", "true").lower() == "true"
        self.festival_threshold = int(os.getenv("AI_RELEVANCE_THRESHOLD_FESTIVALS", "60"))
        self.news_threshold = int(os.getenv("AI_RELEVANCE_THRESHOLD_NEWS", "70"))
        self.duplicate_threshold = float(os.getenv("DUPLICATE_SIMILARITY_THRESHOLD", "0.95"))
        
        # Initialize OpenAI client
        self.client = None
        if OPENAI_AVAILABLE and self.enabled:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key)
                logger.info("✓ AI Filter initialized with OpenAI")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not set. AI filtering disabled.")
                self.enabled = False
        
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def calculate_prestige_score(self, festival: Dict) -> int:
        """
        Calculate prestige score for a festival using AI
        
        Args:
            festival: Festival dictionary
            
        Returns:
            Prestige score (0-100)
        """
        if not self.enabled or not self.client:
            return 50  # Default neutral score
        
        try:
            # Create a prompt for prestige evaluation
            prompt = f"""Rate the prestige of this film festival on a scale of 0-100, where:
- 90-100: Major international festivals (Cannes, Venice, Berlin, Sundance level)
- 70-89: Significant regional or specialized festivals
- 50-69: Mid-tier festivals with good reputation
- 30-49: Small local or emerging festivals
- 0-29: Unknown or very small festivals

Festival: {festival.get('name', '')}
Location: {festival.get('location', '')}
Description: {festival.get('description', '')[:500]}

Return only the numeric score (0-100), no explanation."""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a film festival expert who rates festival prestige."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50  # Increased to handle longer responses
            )
            
            score_text = response.choices[0].message.content.strip()
            # Extract first number from response
            import re
            match = re.search(r'\d+', score_text)
            if not match:
                logger.warning(f"Could not parse score from: {score_text}")
                return 50
            score = int(match.group())
            return max(0, min(100, score))  # Clamp to 0-100
            
        except Exception as e:
            logger.warning(f"Failed to calculate prestige score: {e}")
            return 50  # Default neutral score
    
    async def filter_festivals(self, festivals: List[Dict]) -> List[Dict]:
        """
        Filter festivals for AI-film relevance using AI
        
        Args:
            festivals: List of festival dictionaries
            
        Returns:
            Filtered list with AI relevance scores
        """
        if not self.enabled or not self.client:
            logger.info("AI filtering disabled, returning all festivals")
            return festivals
        
        logger.info(f"🤖 Filtering {len(festivals)} festivals for AI-film relevance...")
        
        filtered_festivals = []
        
        for festival in festivals:
            try:
                # Create prompt for relevance evaluation
                prompt = f"""Is this film festival AI-film friendly or relevant to AI-generated content? 
Rate the relevance on a scale of 0-100, where:
- 90-100: Specifically for AI/tech-generated films
- 70-89: Accepts AI films, welcomes experimental tech
- 50-69: General festival, likely accepts AI films
- 30-49: Traditional festival, may be skeptical of AI
- 0-29: Explicitly against or incompatible with AI films

Festival: {festival.get('name', '')}
Categories: {', '.join(festival.get('category', []))}
Description: {festival.get('description', '')[:500]}

Return only the numeric score (0-100), no explanation."""
                
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a film festival analyst specializing in AI-generated content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=50  # Increased to handle longer responses
                )
                
                score_text = response.choices[0].message.content.strip()
                # Extract first number from response
                import re
                match = re.search(r'\d+', score_text)
                if not match:
                    logger.warning(f"Could not parse relevance score from: {score_text}")
                    relevance_score = 50
                else:
                    relevance_score = int(match.group())
                    relevance_score = max(0, min(100, relevance_score))
                
                # Add scores to festival
                festival['ai_relevance_score'] = relevance_score
                festival['is_ai_film_friendly'] = relevance_score >= self.festival_threshold
                
                # Calculate prestige score
                prestige_score = await self.calculate_prestige_score(festival)
                festival['prestige_score'] = prestige_score
                
                # Generate embedding for duplicate detection
                text_for_embedding = f"{festival.get('name', '')} {festival.get('location', '')} {festival.get('description', '')[:200]}"
                embedding = await self.generate_embedding(text_for_embedding)
                if embedding:
                    festival['embedding'] = embedding
                
                # Only include if meets threshold
                if relevance_score >= self.festival_threshold:
                    filtered_festivals.append(festival)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to filter festival {festival.get('name', '')}: {e}")
                # Include festival with default scores on error
                festival['ai_relevance_score'] = 50
                festival['is_ai_film_friendly'] = False
                festival['prestige_score'] = 50
                continue
        
        logger.info(f"✓ Filtered to {len(filtered_festivals)}/{len(festivals)} AI-relevant festivals")
        return filtered_festivals
    
    async def filter_news(self, articles: List[Dict]) -> List[Dict]:
        """
        Filter news articles for AI/cinema relevance
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Filtered list with relevance scores
        """
        if not self.enabled or not self.client:
            logger.info("AI filtering disabled, returning all articles")
            return articles
        
        logger.info(f"🤖 Filtering {len(articles)} news articles for AI/cinema relevance...")
        
        filtered_articles = []
        
        for article in articles:
            try:
                # Create prompt for relevance evaluation
                prompt = f"""Is this article relevant to AI filmmaking, AI-generated content, or the intersection of AI and cinema?
Rate the relevance on a scale of 0-100, where:
- 90-100: Directly about AI filmmaking, AI-generated films
- 70-89: About technology in filmmaking, AI in entertainment
- 50-69: General film industry news with tech aspects
- 30-49: Film news with minimal AI/tech connection
- 0-29: Irrelevant to AI filmmaking

Title: {article.get('title', '')}
Summary: {article.get('summary', '')[:500]}

Return only the numeric score (0-100), no explanation."""
                
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a film technology analyst specializing in AI and cinema."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=50  # Increased to handle longer responses
                )
                
                score_text = response.choices[0].message.content.strip()
                # Extract first number from response
                import re
                match = re.search(r'\d+', score_text)
                if not match:
                    logger.warning(f"Could not parse relevance score from: {score_text}")
                    relevance_score = 50
                else:
                    relevance_score = int(match.group())
                    relevance_score = max(0, min(100, relevance_score))
                
                # Add scores to article
                article['ai_relevance_score'] = relevance_score
                article['is_ai_cinema_relevant'] = relevance_score >= self.news_threshold
                
                # Generate embedding for duplicate detection
                text_for_embedding = f"{article.get('title', '')} {article.get('summary', '')[:300]}"
                embedding = await self.generate_embedding(text_for_embedding)
                if embedding:
                    article['embedding'] = embedding
                
                # Only include if meets threshold
                if relevance_score >= self.news_threshold:
                    filtered_articles.append(article)
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Failed to filter article {article.get('title', '')}: {e}")
                # Include article with default score on error
                article['ai_relevance_score'] = 50
                article['is_ai_cinema_relevant'] = False
                continue
        
        logger.info(f"✓ Filtered to {len(filtered_articles)}/{len(articles)} AI-relevant articles")
        return filtered_articles
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def detect_duplicates(self, items: List[Dict]) -> List[Dict]:
        """
        Detect and mark duplicate items using embeddings
        
        Args:
            items: List of items (festivals or articles) with embeddings
            
        Returns:
            List with duplicates marked
        """
        logger.info(f"🔍 Detecting duplicates in {len(items)} items...")
        
        duplicates_found = 0
        processed = []
        
        for i, item in enumerate(items):
            if 'embedding' not in item:
                processed.append(item)
                continue
            
            is_duplicate = False
            
            # Compare with all previous items
            for prev_item in processed:
                if 'embedding' not in prev_item:
                    continue
                
                similarity = self.cosine_similarity(
                    item['embedding'],
                    prev_item['embedding']
                )
                
                if similarity >= self.duplicate_threshold:
                    is_duplicate = True
                    duplicates_found += 1
                    logger.info(f"  Duplicate found: {item.get('name') or item.get('title')} (similarity: {similarity:.3f})")
                    break
            
            if not is_duplicate:
                processed.append(item)
        
        logger.info(f"✓ Found {duplicates_found} duplicates, {len(processed)} unique items")
        return processed


# Convenience functions
async def filter_festivals(festivals: List[Dict]) -> List[Dict]:
    """Filter festivals for AI relevance"""
    ai_filter = AIFilter()
    return await ai_filter.filter_festivals(festivals)


async def filter_news(articles: List[Dict]) -> List[Dict]:
    """Filter news for AI/cinema relevance"""
    ai_filter = AIFilter()
    return await ai_filter.filter_news(articles)


if __name__ == "__main__":
    # Test the AI filter
    async def test():
        ai_filter = AIFilter()
        
        # Test festival filtering
        test_festivals = [
            {
                "name": "AI Film Festival",
                "description": "A festival celebrating AI-generated films and technology in cinema",
                "location": "San Francisco, USA"
            },
            {
                "name": "Traditional Cannes Film Festival",
                "description": "The most prestigious film festival in the world",
                "location": "Cannes, France"
            }
        ]
        
        filtered = await ai_filter.filter_festivals(test_festivals)
        print(f"\n✅ Filtered {len(filtered)}/{len(test_festivals)} festivals")
        for f in filtered:
            print(f"  - {f['name']}: {f['ai_relevance_score']}/100 (prestige: {f.get('prestige_score', 'N/A')})")
    
    asyncio.run(test())
