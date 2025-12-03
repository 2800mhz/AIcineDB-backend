"""
Database operations for AIcineDB - FIXED for pgvector + duplicate URL handling
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
    
    def _prepare_embedding(self, embedding) -> Optional[str]:
        """
        Convert embedding to pgvector string format
        
        CRITICAL: pgvector expects string format like '[0.1, 0.2, 0.3]'
        NOT a Python list
        """
        if embedding is None:
            return None
        
        # Convert to list if numpy array
        if isinstance(embedding, np. ndarray):
            embedding = embedding.tolist()
        elif not isinstance(embedding, list):
            logger.warning(f"Unexpected embedding type: {type(embedding)}")
            return None
        
        # Convert to pgvector string format
        embedding_str = '[' + ','.join(str(float(x)) for x in embedding) + ']'
        
        return embedding_str
    
    # ============================================================================
    # JOBS
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
        """Update job status - FIXED VERSION"""
        
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
            updates. append("error_message = :error_message")
            values["error_message"] = error_message
        
        if celery_task_id is not None:
            updates.append("celery_task_id = :celery_task_id")
            values["celery_task_id"] = celery_task_id
        
        if status == 'processing':
            updates. append("started_at = NOW()")
        elif status in ['completed', 'failed']:
            updates.append("completed_at = NOW()")
        
        updates. append("updated_at = NOW()")
        
        query = f"""
            UPDATE analysis_jobs
            SET {', '. join(updates)}
            WHERE id = :job_id
        """
        
        await self.db. execute(query=query, values=values)
    
    # ============================================================================
    # FILMS
    # ============================================================================
    
    async def create_film(self, analysis_result: Dict) -> int:
        """Create or replace film record from analysis result"""
        
        url = analysis_result. get('url')
        
        # ✅ CHECK IF FILM WITH THIS URL ALREADY EXISTS - DELETE IT FIRST
        existing = await self.db. fetch_one(
            "SELECT id FROM films WHERE url = :url",
            values={"url": url}
        )
        
        if existing:
            old_film_id = existing['id']
            logger.warning(f"⚠️ Film already exists with URL, deleting old record (id: {old_film_id})")
            
            # Delete old film and all related records (CASCADE should handle this)
            await self.db. execute(
                "DELETE FROM films WHERE id = :film_id",
                values={"film_id": old_film_id}
            )
            logger.info(f"✓ Deleted old film record: {old_film_id}")
        
        # Extract basic metadata
        metadata = {
            'uploader': analysis_result.get('uploader'),
            'upload_date': analysis_result.get('upload_date'),
            'view_count': analysis_result.get('view_count'),
            'like_count': analysis_result.get('like_count'),
            'description': analysis_result. get('description'),
            'tags': analysis_result.get('tags', []),
            'style': analysis_result. get('style', {}),
            'style_fingerprint': analysis_result.get('style_fingerprint'),
            'shot_statistics': analysis_result. get('shot_statistics', {})
        }
        
        # Prepare embeddings in pgvector string format
        visual_emb = self._prepare_embedding(analysis_result.get('visual_embedding'))
        text_emb = self._prepare_embedding(analysis_result.get('text_embedding'))
        audio_emb = self._prepare_embedding(analysis_result.get('audio_embedding'))
        
        logger.info(f"💾 Saving film: {analysis_result.get('title')}")
        
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
        
        result = await self. db.fetch_one(
            query=query,
            values={
                "title": analysis_result.get('title'),
                "url": analysis_result.get('url'),
                "duration": analysis_result.get('duration'),
                "uploader": metadata. get('uploader'),
                "metadata": json.dumps(metadata),
                "visual_emb": visual_emb,
                "text_emb": text_emb,
                "audio_emb": audio_emb
            }
        )
        
        film_id = result['id']
        logger.info(f"✓ Film created with ID: {film_id}")
        
        # Create related records
        await self._create_shots(film_id, analysis_result.get('shots', []))
        await self._create_characters(film_id, analysis_result. get('characters', []))
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
    
    # database_operations.py içinde

    async def get_job(self, job_id: int) -> Dict:
        """Get job status"""
        query = "SELECT * FROM analysis_jobs WHERE id = :job_id"
        result = await self.db.fetch_one(query, values={"job_id": job_id})
        return dict(result) if result else None

    # ✅ BURAYA EKLEYİN:
    async def get_film_id_from_job(self, job_id: int) -> Optional[int]:
        """
        Get film_id associated with a job
        
        Args:
            job_id: Job ID
            
        Returns:
            Film ID or None if not found
        """
        try:
            result = await self.db.fetch_one(
                "SELECT film_id FROM analysis_jobs WHERE id = :job_id",
                values={"job_id": job_id}
            )
            
            if result and result['film_id']:
                logger.info(f"📊 Found film_id {result['film_id']} for job {job_id}")
                return result['film_id']
            else:
                logger.warning(f"⚠️ No film_id found for job {job_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting film_id from job {job_id}: {e}")
            return None

    # ============================================================================
    # RELATED RECORDS
    # ============================================================================
    
    async def _create_shots(self, film_id: int, shots: List[Dict]):
        """Create shot records"""
        if not shots:
            return
        
        logger.info(f"💾 Saving {len(shots)} shots...")
        
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
                    "shot_type": shot. get('shot_type'),
                    "lighting": shot.get('lighting'),
                    "brightness": shot. get('brightness'),
                    "colors": shot.get('colors', []),
                    "keyframe_path": shot.get('keyframe_path')
                }
            )
    
    async def _create_characters(self, film_id: int, characters: List[Dict]):
        """Create character records"""
        if not characters:
            return
        
        logger.info(f"💾 Saving {len(characters)} characters...")
        
        for char in characters:
            face_emb = self._prepare_embedding(char.get('face_embedding'))
            
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
                    "name": char. get('name'),
                    "role": char.get('role'),
                    "screen_time": char.get('screen_time', 0),
                    "total_appearances": char.get('total_appearances', 0),
                    "primary_emotion": char.get('primary_emotion'),
                    "confidence": char.get('confidence'),
                    "face_embedding": face_emb
                }
            )
    
    async def _create_scenes(self, film_id: int, scenes: List[Dict]):
        """Create scene records"""
        if not scenes:
            return
        
        logger. info(f"💾 Saving {len(scenes)} scenes...")
        
        for scene in scenes:
            query = """
                INSERT INTO scenes (
                    film_id, scene_number, start_time, end_time, duration,
                    lighting, emotion, pacing, description
                )
                VALUES (:film_id, :scene_number, :start_time, :end_time, :duration,
                        :lighting, :emotion, :pacing, :description)
            """
            
            await self. db.execute(
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
        """Create narrative record - FIXED for databases library"""
        if not narrative:
            logger.info("ℹ️ No narrative data to save")
            return
        
        logger.info(f"💾 Saving narrative analysis...")
        
        # Extract and convert values
        logline = narrative.get('logline') or narrative.get('summary') or None
        synopsis = narrative. get('synopsis') or narrative.get('summary') or None
        conflict_type = narrative.get('conflict_type')
        
        # Handle JSONB columns - convert to JSON string
        themes_value = narrative.get('themes', [])
        if isinstance(themes_value, list):
            themes = json.dumps(themes_value)
        elif isinstance(themes_value, str):
            themes = themes_value
        else:
            themes = '[]'
        
        story_beats_value = narrative.get('story_beats', [])
        if isinstance(story_beats_value, list):
            story_beats = json.dumps(story_beats_value)
        elif isinstance(story_beats_value, str):
            story_beats = story_beats_value
        else:
            story_beats = '[]'
        
        act_structure_value = narrative.get('act_structure') or narrative.get('structure', {})
        if isinstance(act_structure_value, dict):
            act_structure = json.dumps(act_structure_value)
        elif isinstance(act_structure_value, str):
            act_structure = act_structure_value
        else:
            act_structure = '{}'
        
        # Handle TEXT[] columns - convert to list
        genre_value = narrative.get('genre', [])
        if isinstance(genre_value, str):
            genre = [genre_value]
        elif isinstance(genre_value, list):
            genre = [str(x) for x in genre_value]
        else:
            genre = []
        
        tone_value = narrative.get('tone', [])
        if isinstance(tone_value, str):
            tone = [tone_value]
        elif isinstance(tone_value, list):
            tone = [str(x) for x in tone_value]
        else:
            tone = []
        
        # Handle FLOAT[] columns - convert to float list
        emotional_arc_value = narrative.get('emotional_arc', [])
        if isinstance(emotional_arc_value, str):
            try:
                emotional_arc = [float(x) for x in json.loads(emotional_arc_value)]
            except:
                emotional_arc = []
        elif isinstance(emotional_arc_value, list):
            emotional_arc = []
            for val in emotional_arc_value:
                try:
                    emotional_arc.append(float(val))
                except:
                    continue
        else:
            emotional_arc = []
        
        # Use raw SQL with proper escaping
        query = """
            INSERT INTO narratives (
                film_id, logline, synopsis, themes, genre, tone,
                conflict_type, emotional_arc, story_beats, act_structure
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9::jsonb, $10::jsonb)
        """
        
        try:
            # Use fetch instead of execute for better parameter handling
            await self.db.execute(
                query,
                film_id,
                logline,
                synopsis,
                themes,
                genre,
                tone,
                conflict_type,
                emotional_arc,
                story_beats,
                act_structure
            )
            logger.info(f"✓ Narrative saved successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to save narrative: {e}")
            logger.error(f"   film_id={film_id}")
            logger.error(f"   themes={themes[:100] if themes else None}")
            logger.error(f"   genre={genre}")
            logger.error(f"   tone={tone}")
            logger.error(f"   emotional_arc={emotional_arc[:5] if emotional_arc else []}")
            raise
    
    async def _create_transcript(self, film_id: int, transcript: Dict):
        """Create transcript record"""
        if not transcript:
            return
        
        logger. info(f"💾 Saving transcript...")
        
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
                "word_count": transcript. get('word_count'),
                "segments": json.dumps(transcript. get('segments', []))
            }
        )
    
    async def _create_audio_features(self, film_id: int, audio_features: Dict):
        """Create audio features record"""
        if not audio_features:
            return
        
        logger.info(f"💾 Saving audio features...")
        
        query = """
            INSERT INTO audio_features (
                film_id, tempo, mood, intensity, pacing,
                avg_energy, spectral_brightness, speech_ratio
            )
            VALUES (:film_id, :tempo, :mood, :intensity, :pacing,
                    :avg_energy, :spectral_brightness, :speech_ratio)
        """
        
        await self.db. execute(
            query=query,
            values={
                "film_id": film_id,
                "tempo": audio_features.get('tempo'),
                "mood": audio_features. get('mood'),
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
        results = await self.db. fetch_all(query, values={"film_id": film_id})
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
        result = await self. db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}
    
    async def _get_transcript(self, film_id: int) -> Dict:
        query = "SELECT * FROM transcripts WHERE film_id = :film_id"
        result = await self.db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}
    
    async def _get_audio_features(self, film_id: int) -> Dict:
        query = "SELECT * FROM audio_features WHERE film_id = :film_id"
        result = await self.db.fetch_one(query, values={"film_id": film_id})
        return dict(result) if result else {}