"""
Database Operations for Film Analysis
CRUD operations for all tables
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Database CRUD operations"""
    
    def __init__(self, db):
        """
        Args:
            db: Database connection (from databases library)
        """
        self.db = db
    
    # ============================================================================
    # FILMS
    # ============================================================================
    
    async def create_film(self, analysis_result: Dict) -> int:
        """
        Create film record with complete analysis
        
        Args:
            analysis_result: Complete analysis result from pipeline
            
        Returns:
            Film ID
        """
        try:
            # Prepare metadata
            metadata = {
                'resolution': analysis_result.get('resolution'),
                'fps': analysis_result.get('fps'),
                'style_fingerprint': analysis_result.get('style_fingerprint'),
                'shot_statistics': analysis_result.get('shot_statistics'),
                'style': analysis_result.get('style'),
                'color_palette': analysis_result.get('color_palette'),
            }
            
            # Convert embeddings to pgvector format
            visual_emb = self._prepare_embedding(analysis_result.get('visual_embedding'))
            text_emb = self._prepare_embedding(analysis_result.get('text_embedding'))
            audio_emb = self._prepare_embedding(analysis_result.get('audio_embedding'))
            
            # Insert film
            query = """
                INSERT INTO films (
                    title, url, duration, uploader,
                    metadata,
                    visual_embedding, text_embedding, audio_embedding,
                    analyzed_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                RETURNING id
            """
            
            film_id = await self.db.fetch_val(
                query,
                analysis_result['title'],
                analysis_result['url'],
                analysis_result['duration'],
                analysis_result.get('uploader'),
                json.dumps(metadata),
                visual_emb,
                text_emb,
                audio_emb
            )
            
            logger.info(f"✓ Created film record: {film_id}")
            
            # Create related records
            await self._create_shots(film_id, analysis_result.get('shots', []))
            await self._create_characters(film_id, analysis_result.get('characters', []))
            await self._create_scenes(film_id, analysis_result.get('scenes', []))
            
            if analysis_result.get('narrative'):
                await self._create_narrative(film_id, analysis_result['narrative'])
            
            if analysis_result.get('transcript'):
                await self._create_transcript(film_id, analysis_result['transcript'])
            
            if analysis_result.get('audio_features'):
                await self._create_audio_features(film_id, analysis_result['audio_features'])
            
            return film_id
            
        except Exception as e:
            logger.error(f"Failed to create film: {e}")
            raise
    
    async def get_film(self, film_id: int) -> Optional[Dict]:
        """Get complete film data"""
        query = "SELECT * FROM films WHERE id = $1"
        film = await self.db.fetch_one(query, film_id)
        
        if not film:
            return None
        
        return dict(film)
    
    async def update_film_embeddings(
        self,
        film_id: int,
        visual_emb: List = None,
        text_emb: List = None,
        audio_emb: List = None
    ):
        """Update film embeddings"""
        updates = []
        params = []
        param_idx = 1
        
        if visual_emb:
            updates.append(f"visual_embedding = ${param_idx}")
            params.append(self._prepare_embedding(visual_emb))
            param_idx += 1
        
        if text_emb:
            updates.append(f"text_embedding = ${param_idx}")
            params.append(self._prepare_embedding(text_emb))
            param_idx += 1
        
        if audio_emb:
            updates.append(f"audio_embedding = ${param_idx}")
            params.append(self._prepare_embedding(audio_emb))
            param_idx += 1
        
        if not updates:
            return
        
        params.append(film_id)
        query = f"""
            UPDATE films
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = ${param_idx}
        """
        
        await self.db.execute(query, *params)
    
    # ============================================================================
    # JOBS
    # ============================================================================
    
    async def create_job(self, url: str, priority: int = 5) -> int:
        """Create analysis job"""
        query = """
            INSERT INTO analysis_jobs (url, status, priority)
            VALUES (:url, 'pending', :priority)
            RETURNING id
        """
        result = await self.db.fetch_one(query, values={"url": url, "priority": priority})
        return result['id'] if result else None
    
    async def update_job_status(
        self,
        job_id: int,
        status: str,
        progress: float = None,
        current_stage: str = None,
        film_id: int = None,
        error_message: str = None,
        celery_task_id: str = None
    ):
        """Update job status"""
        updates = ["status = $2"]
        params = [job_id, status]
        param_idx = 3
        
        if progress is not None:
            updates.append(f"progress = ${param_idx}")
            params.append(progress)
            param_idx += 1
        
        if current_stage:
            updates.append(f"current_stage = ${param_idx}")
            params.append(current_stage)
            param_idx += 1
        
        if film_id:
            updates.append(f"film_id = ${param_idx}")
            params.append(film_id)
            param_idx += 1
        
        if error_message:
            updates.append(f"error_message = ${param_idx}")
            params.append(error_message)
            param_idx += 1
        
        if celery_task_id:
            updates.append(f"celery_task_id = ${param_idx}")
            params.append(celery_task_id)
            param_idx += 1
        
        if status == 'processing':
            updates.append(f"started_at = NOW()")
        elif status in ['completed', 'failed']:
            updates.append(f"completed_at = NOW()")
        
        updates.append("updated_at = NOW()")
        
        query = f"""
            UPDATE analysis_jobs
            SET {', '.join(updates)}
            WHERE id = $1
        """
        
        await self.db.execute(query, *params)
    
    # ============================================================================
    # RELATED RECORDS
    # ============================================================================
    
    async def _create_shots(self, film_id: int, shots: List[Dict]):
        """Create shot records"""
        if not shots:
            return
        
        query = """
            INSERT INTO shots (
                film_id, shot_number, start_time, end_time, duration,
                shot_type, lighting, brightness, colors, keyframe_path
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        
        for shot in shots:
            await self.db.execute(
                query,
                film_id,
                shot['shot_number'],
                shot['start_time'],
                shot['end_time'],
                shot['duration'],
                shot.get('shot_type'),
                shot.get('lighting'),
                shot.get('brightness'),
                shot.get('colors', []),
                shot.get('keyframe_path')
            )
        
        logger.info(f"✓ Created {len(shots)} shot records")
    
    async def _create_characters(self, film_id: int, characters: List[Dict]):
        """Create character records"""
        if not characters:
            return
        
        query = """
            INSERT INTO characters (
                film_id, character_id, name, role,
                screen_time, total_appearances,
                primary_emotion, confidence
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        for char in characters:
            await self.db.execute(
                query,
                film_id,
                char['character_id'],
                char.get('name'),
                char.get('role'),
                char.get('screen_time', 0),
                char.get('total_appearances', 0),
                char.get('primary_emotion'),
                char.get('confidence', 0.7)
            )
        
        logger.info(f"✓ Created {len(characters)} character records")
    
    async def _create_scenes(self, film_id: int, scenes: List[Dict]):
        """Create scene records"""
        if not scenes:
            return
        
        query = """
            INSERT INTO scenes (
                film_id, scene_number, start_time, end_time, duration,
                lighting, description
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        for scene in scenes:
            await self.db.execute(
                query,
                film_id,
                scene['scene_number'],
                scene['start_time'],
                scene['end_time'],
                scene['duration'],
                scene.get('lighting'),
                f"Scene with {scene.get('num_shots', 0)} shots"
            )
        
        logger.info(f"✓ Created {len(scenes)} scene records")
    
    async def _create_narrative(self, film_id: int, narrative: Dict):
        """Create narrative record"""
        query = """
            INSERT INTO narratives (
                film_id, logline, synopsis,
                themes, genre, tone,
                conflict_type, emotional_arc,
                story_beats, act_structure
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        
        await self.db.execute(
            query,
            film_id,
            narrative.get('logline'),
            narrative.get('synopsis'),
            json.dumps(narrative.get('themes', [])),
            narrative.get('genre', []),
            narrative.get('tone', []),
            narrative.get('conflict_type'),
            narrative.get('emotional_arc', []),
            json.dumps(narrative.get('story_beats', [])),
            json.dumps(narrative.get('act_structure', {}))
        )
        
        logger.info("✓ Created narrative record")
    
    async def _create_transcript(self, film_id: int, transcript: Dict):
        """Create transcript record"""
        query = """
            INSERT INTO transcripts (
                film_id, text, language, word_count, segments
            )
            VALUES ($1, $2, $3, $4, $5)
        """
        
        await self.db.execute(
            query,
            film_id,
            transcript.get('text'),
            transcript.get('language'),
            transcript.get('word_count', 0),
            json.dumps(transcript.get('segments', []))
        )
        
        logger.info("✓ Created transcript record")
    
    async def _create_audio_features(self, film_id: int, features: Dict):
        """Create audio features record"""
        query = """
            INSERT INTO audio_features (
                film_id, tempo, mood, intensity, pacing,
                avg_energy, spectral_brightness, speech_ratio
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        
        await self.db.execute(
            query,
            film_id,
            features.get('tempo'),
            features.get('mood'),
            features.get('intensity'),
            features.get('pacing'),
            features.get('avg_energy'),
            features.get('spectral_brightness'),
            features.get('speech_ratio')
        )
        
        logger.info("✓ Created audio features record")
    
    # ============================================================================
    # SIMILARITY SEARCH
    # ============================================================================
    
    async def find_similar_films(
        self,
        film_id: int,
        similarity_type: str = "combined",
        limit: int = 10
    ) -> List[Dict]:
        """Find similar films using vector similarity"""
        
        if similarity_type == "visual":
            query = """
                SELECT 
                    f.id, f.title,
                    1 - (f.visual_embedding <=> ref.visual_embedding) as similarity
                FROM films f
                CROSS JOIN (SELECT visual_embedding FROM films WHERE id = $1) ref
                WHERE f.id != $1 AND f.visual_embedding IS NOT NULL
                ORDER BY f.visual_embedding <=> ref.visual_embedding
                LIMIT $2
            """
        elif similarity_type == "narrative":
            query = """
                SELECT 
                    f.id, f.title,
                    1 - (f.text_embedding <=> ref.text_embedding) as similarity
                FROM films f
                CROSS JOIN (SELECT text_embedding FROM films WHERE id = $1) ref
                WHERE f.id != $1 AND f.text_embedding IS NOT NULL
                ORDER BY f.text_embedding <=> ref.text_embedding
                LIMIT $2
            """
        else:  # combined
            query = """
                SELECT 
                    f.id, f.title,
                    (
                        COALESCE(1 - (f.visual_embedding <=> ref.visual_embedding), 0) +
                        COALESCE(1 - (f.text_embedding <=> ref.text_embedding), 0) +
                        COALESCE(1 - (f.audio_embedding <=> ref.audio_embedding), 0)
                    ) / 3.0 as similarity
                FROM films f
                CROSS JOIN (
                    SELECT visual_embedding, text_embedding, audio_embedding 
                    FROM films WHERE id = $1
                ) ref
                WHERE f.id != $1
                ORDER BY similarity DESC
                LIMIT $2
            """
        
        results = await self.db.fetch_all(query, film_id, limit)
        return [dict(r) for r in results]
    
    # ============================================================================
    # HELPERS
    # ============================================================================
    
    def _prepare_embedding(self, embedding: List) -> Optional[str]:
        """Convert embedding list to pgvector format"""
        if not embedding:
            return None
        
        # pgvector expects string like '[1.0, 2.0, 3.0]'
        return f"[{','.join(map(str, embedding))}]"
