"""
Database operations for AIcineDB - FIXED
"""
import logging
from typing import Dict, List, Optional, Any
import json
import numpy as np
from databases import Database

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Database operations handler"""
    
    def __init__(self, database: Database):
        self.db = database
    
    def _prepare_embedding(self, embedding) -> List[float]:
        """Convert embedding to list format for pgvector"""
        if embedding is None:
            return None
        
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
        elif isinstance(embedding, list):
            return embedding
        else:
            raise ValueError(f"Unsupported embedding type: {type(embedding)}")
    
    # ============================================================================
    # JOBS - FIXED METHOD
    # ============================================================================
    
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
        """
        Update job status - FIXED VERSION
        
        CRITICAL: Uses named parameters with 'values' dict
        NOT positional parameters with list
        """
        
        # Build the UPDATE query parts
        updates = ["status = :status"]
        values = {"job_id": job_id, "status": status}
        
        if progress is not None:
            updates.append("progress = :progress")
            values["progress"] = progress
        
        if current_stage is not None:
            updates.append("current_stage = :current_stage")
            values["current_stage"] = current_stage
        
        if film_id is not None:
            updates.append("film_id = :film_id")
            values["film_id"] = film_id
        
        if error_message is not None:
            updates.append("error_message = :error_message")
            values["error_message"] = error_message
        
        if celery_task_id is not None:
            updates.append("celery_task_id = :celery_task_id")
            values["celery_task_id"] = celery_task_id
        
        # Add timestamp updates based on status
        if status == 'processing':
            updates.append("started_at = NOW()")
        elif status in ['completed', 'failed']:
            updates.append("completed_at = NOW()")
        
        updates.append("updated_at = NOW()")
        
        # Build final query
        query = f"""
            UPDATE analysis_jobs
            SET {', '.join(updates)}
            WHERE id = :job_id
        """
        
        # Execute with named parameters
        await self.db.execute(query=query, values=values)
    
    # ============================================================================
    # FILMS
    # ============================================================================
    
    async def create_film(self, analysis_result: Dict) -> int:
        """Create film record from analysis result"""
        
        # Extract basic metadata
        metadata = {
            'uploader': analysis_result.get('uploader'),
            'upload_date': analysis_result.get('upload_date'),
            'view_count': analysis_result.get('view_count'),
            'like_count': analysis_result.get('like_count'),
            'description': analysis_result.get('description'),
            'tags': analysis_result.get('tags', []),
            'style': analysis_result.get('style', {}),
            'style_fingerprint': analysis_result.get('style_fingerprint'),
            'shot_statistics': analysis_result.get('shot_statistics', {})
        }
        
        # Prepare embeddings
        visual_emb = self._prepare_embedding(analysis_result.get('visual_embedding'))
        text_emb = self._prepare_embedding(analysis_result.get('text_embedding'))
        audio_emb = self._prepare_embedding(analysis_result.get('audio_embedding'))
        
        query = """
            INSERT INTO films (
                title, url, duration, uploader,
                metadata,
                visual_embedding, text_embedding, audio_embedding,
                analyzed_at
            )
            VALUES (:title, :url, :duration, :uploader, :metadata, :visual_emb, :text_emb, :audio_emb, NOW())
            RETURNING id
        """
        
        result = await self.db.fetch_one(
            query=query,
            values={
                "title": analysis_result.get('title'),
                "url": analysis_result.get('url'),
                "duration": analysis_result.get('duration'),
                "uploader": metadata.get('uploader'),
                "metadata": json.dumps(metadata),
                "visual_emb": visual_emb,
                "text_emb": text_emb,
                "audio_emb": audio_emb
            }
        )
        
        film_id = result['id']
        
        # Create related records
        await self._create_shots(film_id, analysis_result.get('shots', []))
        await self._create_characters(film_id, analysis_result.get('characters', []))
        await self._create_scenes(film_id, analysis_result.get('scenes', []))
        await self._create_narrative(film_id, analysis_result.get('narrative'))
        await self._create_transcript(film_id, analysis_result.get('transcript', {}))
        await self._create_audio_features(film_id, analysis_result.get('audio_features', {}))
        
        return film_id
    
    async def get_film(self, film_id: int) -> Dict:
        """Get complete film data"""
        query = "SELECT * FROM films WHERE id = :film_id"
        film = await self.db.fetch_one(query, values={"film_id": film_id})
        
        if not film:
            return None
        
        result = dict(film)
        
        # Get related data
        result['shots'] = await self._get_shots(film_id)
        result['characters'] = await self._get_characters(film_id)
        result['scenes'] = await self._get_scenes(film_id)
        result['narrative'] = await self._get_narrative(film_id)
        result['transcript'] = await self._get_transcript(film_id)
        result['audio_features'] = await self._get_audio_features(film_id)
        
        return result
    
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
    
    async def get_job(self, job_id: int) -> Dict:
        """Get job status"""
        query = "SELECT * FROM analysis_jobs WHERE id = :job_id"
        result = await self.db.fetch_one(query, values={"job_id": job_id})
        return dict(result) if result else None
    
    # ============================================================================
    # RELATED RECORDS
    # ============================================================================
    
    async def _create_shots(self, film_id: int, shots: List[Dict]):
        """Create shot records"""
        if not shots:
            return
        
        for shot in shots:
            query = """
                INSERT INTO shots (
                    film_id, shot_number, start_time, end_time, duration,
                    shot_type, lighting, brightness, colors, keyframe_path
                )
                VALUES (:film_id, :shot_number, :start_time, :end_time, :duration,
                        :shot_type, :lighting, :brightness, :colors, :keyframe_path)
            """
            
            await self.db.execute(
                query=query,
                values={
                    "film_id": film_id,
                    "shot_number": shot['shot_number'],
                    "start_time": shot['start_time'],
                    "end_time": shot['end_time'],
                    "duration": shot['duration'],
                    "shot_type": shot.get('shot_type'),
                    "lighting": shot.get('lighting'),
                    "brightness": shot.get('brightness'),
                    "colors": shot.get('colors', []),
                    "keyframe_path": shot.get('keyframe_path')
                }
            )
    
    async def _create_characters(self, film_id: int, characters: List[Dict]):
        """Create character records"""
        if not characters:
            return
        
        for char in characters:
            query = """
                INSERT INTO characters (
                    film_id, character_id, name, role,
                    screen_time, total_appearances,
                    primary_emotion, confidence, face_embedding
                )
                VALUES (:film_id, :character_id, :name, :role,
                        :screen_time, :total_appearances,
                        :primary_emotion, :confidence, :face_embedding)
            """
            
            await self.db.execute(
                query=query,
                values={
                    "film_id": film_id,
                    "character_id": char['character_id'],
                    "name": char.get('name'),
                    "role": char.get('role'),
                    "screen_time": char.get('screen_time', 0),
                    "total_appearances": char.get('total_appearances', 0),
                    "primary_emotion": char.get('primary_emotion'),
                    "confidence": char.get('confidence'),
                    "face_embedding": self._prepare_embedding(char.get('face_embedding'))
                }
            )
    
    async def _create_scenes(self, film_id: int, scenes: List[Dict]):
        """Create scene records"""
        if not scenes:
            return
        
        for scene in scenes:
            query = """
                INSERT INTO scenes (
                    film_id, scene_number, start_time, end_time, duration,
                    lighting, emotion, pacing, description
                )
                VALUES (:film_id, :scene_number, :start_time, :end_time, :duration,
                        :lighting, :emotion, :pacing, :description)
            """
            
            await self.db.execute(
                query=query,
                values={
                    "film_id": film_id,
                    "scene_number": scene['scene_number'],
                    "start_time": scene['start_time'],
                    "end_time": scene['end_time'],
                    "duration": scene['duration'],
                    "lighting": scene.get('lighting'),
                    "emotion": scene.get('emotion'),
                    "pacing": scene.get('pacing'),
                    "description": scene.get('description')
                }
            )
    
    async def _create_narrative(self, film_id: int, narrative: Dict):
        """Create narrative record"""
        if not narrative:
            return
        
        query = """
            INSERT INTO narratives (
                film_id, logline, synopsis, themes, genre, tone,
                conflict_type, emotional_arc, story_beats, act_structure
            )
            VALUES (:film_id, :logline, :synopsis, :themes, :genre, :tone,
                    :conflict_type, :emotional_arc, :story_beats, :act_structure)
        """
        
        await self.db.execute(
            query=query,
            values={
                "film_id": film_id,
                "logline": narrative.get('logline'),
                "synopsis": narrative.get('synopsis'),
                "themes": json.dumps(narrative.get('themes', [])),
                "genre": narrative.get('genre', []),
                "tone": narrative.get('tone', []),
                "conflict_type": narrative.get('conflict_type'),
                "emotional_arc": narrative.get('emotional_arc', []),
                "story_beats": json.dumps(narrative.get('story_beats', [])),
                "act_structure": json.dumps(narrative.get('act_structure', {}))
            }
        )
    
    async def _create_transcript(self, film_id: int, transcript: Dict):
        """Create transcript record"""
        if not transcript:
            return
        
        query = """
            INSERT INTO transcripts (
                film_id, text, language, word_count, segments
            )
            VALUES (:film_id, :text, :language, :word_count, :segments)
        """
        
        await self.db.execute(
            query=query,
            values={
                "film_id": film_id,
                "text": transcript.get('text'),
                "language": transcript.get('language'),
                "word_count": transcript.get('word_count'),
                "segments": json.dumps(transcript.get('segments', []))
            }
        )
    
    async def _create_audio_features(self, film_id: int, audio_features: Dict):
        """Create audio features record"""
        if not audio_features:
            return
        
        query = """
            INSERT INTO audio_features (
                film_id, tempo, mood, intensity, pacing,
                avg_energy, spectral_brightness, speech_ratio
            )
            VALUES (:film_id, :tempo, :mood, :intensity, :pacing,
                    :avg_energy, :spectral_brightness, :speech_ratio)
        """
        
        await self.db.execute(
            query=query,
            values={
                "film_id": film_id,
                "tempo": audio_features.get('tempo'),
                "mood": audio_features.get('mood'),
                "intensity": audio_features.get('intensity'),
                "pacing": audio_features.get('pacing'),
                "avg_energy": audio_features.get('avg_energy'),
                "spectral_brightness": audio_features.get('spectral_brightness'),
                "speech_ratio": audio_features.get('speech_ratio')
            }
        )
    
    # Getter methods
    async def _get_shots(self, film_id: int) -> List[Dict]:
        query = "SELECT * FROM shots WHERE film_id = :film_id ORDER BY shot_number"
        results = await self.db.fetch_all(query, values={"film_id": film_id})
        return [dict(row) for row in results]
    
    async def _get_characters(self, film_id: int) -> List[Dict]:
        query = "SELECT * FROM characters WHERE film_id = :film_id"
        results = await self.db.fetch_all(query, values={"film_id": film_id})
        return [dict(row) for row in results]
    
    async def _get_scenes(self, film_id: int) -> List[Dict]:
        query = "SELECT * FROM scenes WHERE film_id = :film_id ORDER BY scene_number"
        results = await self.db.fetch_all(query, values={"film_id": film_id})
        return [dict(row) for row in results]
    
    async def _get_narrative(self, film_id: int) -> Dict:
        query = "SELECT * FROM narratives WHERE film_id = :film_id"
        result = await self.db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}
    
    async def _get_transcript(self, film_id: int) -> Dict:
        query = "SELECT * FROM transcripts WHERE film_id = :film_id"
        result = await self.db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}
    
    async def _get_audio_features(self, film_id: int) -> Dict:
        query = "SELECT * FROM audio_features WHERE film_id = :film_id"
        result = await self.db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}