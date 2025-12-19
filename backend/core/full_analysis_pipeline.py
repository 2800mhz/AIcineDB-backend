"""
Complete Film Analysis Pipeline
Orchestrates all analysis modules and saves to database
"""
import os
import logging
from typing import Dict
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Import all analyzers
from backend.core.video_processor import VideoProcessor
from backend.analyzers.cinematography. shot_detector import ShotDetector
from backend.analyzers.cinematography.style_classifier import StyleClassifier
from backend. analyzers.audio. audio_analyzer import AudioAnalyzer
from backend.analyzers.characters.character_tracker import CharacterTracker
from backend.analyzers.narrative.gemini_analyzer import GeminiNarrativeAnalyzer
from backend.services.supabase_sync import SupabaseSyncService

# Import Gemini title extractor for Twitter
try:
    from backend.analyzers.gemini_title_extractor import GeminiTitleExtractor
    TITLE_EXTRACTOR_AVAILABLE = True
except ImportError:
    TITLE_EXTRACTOR_AVAILABLE = False
    logger.warning("Gemini title extractor not available")


class FullAnalysisPipeline:
    """Complete film analysis pipeline"""
    
    def __init__(self, output_base_dir: str = "./analyses"):
        """
        Args:
            output_base_dir: Base directory for analysis outputs
        """
        self. output_base_dir = Path(output_base_dir)
        self.output_base_dir. mkdir(parents=True, exist_ok=True)
        
        # Initialize analyzers
        self.video_processor = VideoProcessor()
        self. shot_detector = ShotDetector()
        self.style_classifier = StyleClassifier()
        self.audio_analyzer = AudioAnalyzer()
        self.character_tracker = CharacterTracker()
        
        # Gemini analyzer (may fail if API key not set)
        try:
            self.narrative_analyzer = GeminiNarrativeAnalyzer()
        except Exception as e:
            logger.warning(f"Gemini analyzer unavailable: {e}")
            self.narrative_analyzer = None
        
        # Gemini title extractor for Twitter (may fail if API key not set)
        try:
            if TITLE_EXTRACTOR_AVAILABLE:
                self.title_extractor = GeminiTitleExtractor()
            else:
                self.title_extractor = None
        except Exception as e:
            logger.warning(f"Gemini title extractor unavailable: {e}")
            self.title_extractor = None
        
        # Supabase sync service (optional - disabled if not configured)
        self.supabase_sync = SupabaseSyncService()
    
    async def analyze_film(
        self,
        url: str,
        job_id: int,
        progress_callback=None
    ) -> Dict:
        """
        Complete film analysis pipeline
        
        Args:
            url: Video URL
            job_id: Job ID for tracking
            progress_callback: Function to call with progress updates
            
        Returns:
            Complete analysis results
        """
        try:
            # Create job directory
            job_dir = self. output_base_dir / f"job_{job_id}"
            job_dir.mkdir(parents=True, exist_ok=True)
            
            video_id = f"video_{job_id}"
            
            # ============================================================
            # STAGE 1: Download Video (0-15%)
            # ============================================================
            self._update_progress(progress_callback, 0.05, "📥 Downloading video...")
            
            video_info = self.video_processor.download_video(url, video_id)
            video_path = video_info['video_path']
            platform = video_info.get('platform', 'other')
            
            # Extract film title from tweet if this is a Twitter video
            extracted_title = None
            if platform == 'twitter' and self.title_extractor:
                tweet_text = video_info.get('tweet_text', '')
                if tweet_text:
                    self._update_progress(progress_callback, 0.10, "🎬 Extracting film title from tweet...")
                    try:
                        title_result = self.title_extractor.extract_title(tweet_text)
                        extracted_title = title_result.get('title')
                        confidence = title_result.get('confidence', 'none')
                        
                        logger.info(f"🎬 Title extraction result: '{extracted_title}' (confidence: {confidence})")
                        
                        # Use extracted title if confidence is acceptable
                        if confidence in ['high', 'medium'] and extracted_title != 'Unknown Title':
                            video_info['extracted_title'] = extracted_title
                            video_info['title'] = extracted_title
                            video_info['title_extraction_confidence'] = confidence
                            logger.info(f"✅ Using Gemini-extracted title: '{extracted_title}'")
                        else:
                            logger.info(f"⚠️ Title extraction confidence too low ({confidence}), using fallback")
                            # Use yt-dlp title or generic fallback
                            fallback_title = video_info.get('title', 'Untitled Film')
                            video_info['title'] = fallback_title
                            video_info['title_extraction_confidence'] = 'none'
                            
                    except Exception as e:
                        logger. warning(f"⚠️ Title extraction failed: {e}")
                        video_info['title'] = video_info.get('title', 'Untitled Film')
                        video_info['title_extraction_confidence'] = 'error'
            
            self._update_progress(progress_callback, 0.15, f"✓ Downloaded: {video_info['title']}")
            
            # ============================================================
            # STAGE 2: Extract Frames (15-25%)
            # ============================================================
            self._update_progress(progress_callback, 0.18, "🎞️ Extracting frames...")
            
            frames_dir = job_dir / "frames"
            frames_info = self.video_processor.extract_frames(
                video_path,
                video_id,
                fps=1.0
            )
            
            self._update_progress(progress_callback, 0.25, f"✓ Extracted {frames_info['total_extracted']} frames")
            
            # ============================================================
            # STAGE 3: Detect Shots (25-35%)
            # ============================================================
            self._update_progress(progress_callback, 0.28, "🎬 Detecting shots...")
            
            keyframes_dir = job_dir / "keyframes"
            keyframes_dir.mkdir(parents=True, exist_ok=True)
            
            shots = self.shot_detector.detect_shots(
                video_path,
                output_dir=str(keyframes_dir)
            )
            
            shot_stats = self.shot_detector.calculate_shot_statistics(shots)
            
            self._update_progress(progress_callback, 0.35, f"✓ Detected {len(shots)} shots")

            keyframe_count = len(list(keyframes_dir.glob("shot_*. jpg")))
            logger.info(f"✅ Saved {keyframe_count} keyframes to {keyframes_dir}")
            
            # ============================================================
            # STAGE 4: Classify Visual Style (35-45%)
            # ============================================================
            self._update_progress(progress_callback, 0.38, "🎨 Classifying visual style...")
            
            keyframe_paths = [s['keyframe_path'] for s in shots if s. get('keyframe_path')]
            
            style_result = self.style_classifier.classify_style(keyframe_paths)
            visual_embedding = self.style_classifier.generate_visual_embedding(keyframe_paths)
            color_palette = self.style_classifier.analyze_color_palette(keyframe_paths)
            
            self._update_progress(progress_callback, 0.45, f"✓ Style: {style_result['top_style']}")
            
            # ============================================================
            # STAGE 5: Extract & Analyze Audio (45-60%)
            # ============================================================
            self._update_progress(progress_callback, 0.48, "🎵 Extracting audio...")
            
            audio_path = self.video_processor.extract_audio(video_path, video_id)
            
            self._update_progress(progress_callback, 0.50, "🎤 Transcribing & analyzing audio...")
            
            audio_analysis = self.audio_analyzer.analyze_complete(audio_path)
            
            transcript = audio_analysis['transcript']
            audio_features = audio_analysis['audio_features']
            text_embedding = audio_analysis. get('text_embedding')
            audio_embedding = audio_analysis.get('audio_embedding')
            
            self._update_progress(
                progress_callback,
                0.60,
                f"✓ Transcribed {transcript['word_count']} words"
            )
            
            # ============================================================
            # STAGE 6: Analyze Narrative (60-75%)
            # ============================================================
            if self.narrative_analyzer and transcript['text']:
                self._update_progress(progress_callback, 0.63, "📖 Analyzing narrative with Gemini AI...")
                
                visual_context = {
                    'total_shots': len(shots),
                    'colors': color_palette. get('palette', [])[:5],
                    'lighting': shots[0].get('lighting', 'unknown') if shots else 'unknown',
                }
                
                narrative = await self.narrative_analyzer.analyze_narrative(
                    transcript=transcript['text'],
                    title=video_info['title'],
                    duration=video_info['duration'],
                    visual_context=visual_context
                )
                
                self._update_progress(progress_callback, 0.75, "✓ Narrative analysis complete")
            else:
                narrative = None
                self._update_progress(progress_callback, 0.75, "⚠ Narrative analysis skipped")
            
            # ============================================================
            # STAGE 7: Track Characters (75-85%)
            # ============================================================
            self._update_progress(progress_callback, 0.78, "🎭 Tracking characters...")
            
            character_analysis = self.character_tracker.analyze_video(
                video_path,
                fps_sample=2.0,
                max_frames=200
            )
            
            characters = character_analysis['characters']
            
            self._update_progress(progress_callback, 0.85, f"✓ Found {len(characters)} characters")
            
            # ============================================================
            # STAGE 8: Detect Scenes (85-90%)
            # ============================================================
            self._update_progress(progress_callback, 0.87, "🎞️ Detecting scenes...")
            
            scenes = self._detect_scenes_from_shots(shots, audio_features)
            
            self._update_progress(progress_callback, 0.90, f"✓ Detected {len(scenes)} scenes")
            
            # ============================================================
            # STAGE 9: Compile Results (90-95%)
            # ============================================================
            self._update_progress(progress_callback, 0.92, "📊 Compiling results...")
            
            analysis_result = {
                'job_id': job_id,
                'video_id': video_id,
                'url': url,
                'video_url': url,  # Original URL for playback
                
                # Video metadata
                'title': video_info['title'],
                'duration': video_info['duration'],
                'uploader': video_info.get('uploader'),
                'resolution': f"{video_info.get('width', 0)}x{video_info.get('height', 0)}",
                'fps': video_info.get('fps', 30),
                'platform': video_info.get('platform', 'other'),
                
                # Twitter-specific metadata (if applicable)
                'tweet_text': video_info.get('tweet_text'),
                'extracted_title': video_info.get('extracted_title'),
                'thumbnail_path': video_info.get('thumbnail_path'),  # Local poster path
                
                # Cinematography
                'shots': shots,
                'shot_statistics': shot_stats,
                'total_shots': len(shots),
                
                # Visual style
                'style': style_result,
                'color_palette': color_palette,
                'style_fingerprint': style_result['fingerprint'],
                
                # Embeddings
                'visual_embedding': visual_embedding. tolist() if visual_embedding is not None else None,
                'text_embedding': text_embedding.tolist() if text_embedding is not None else None,
                'audio_embedding': audio_embedding.tolist() if audio_embedding is not None else None,
                
                # Audio
                'transcript': transcript,
                'audio_features': audio_features,
                
                # Narrative
                'narrative': narrative,
                
                # Characters
                'characters': characters,
                'total_characters': len(characters),
                
                # Scenes
                'scenes': scenes,
                'total_scenes': len(scenes),
                
                # Paths
                'video_path': str(video_path),
                'frames_dir': str(frames_dir),
                'audio_path': str(audio_path),
                'keyframes_dir': str(keyframes_dir),
            }
            
            # Save to JSON
            result_path = job_dir / "analysis_result. json"
            with open(result_path, 'w') as f:
                json.dump(analysis_result, f, indent=2, default=str)
            
            self._update_progress(progress_callback, 0.95, "✓ Results compiled")
                        
            # ============================================================
            # STAGE 10: Save to Database (95-97%)
            # ============================================================
            self._update_progress(progress_callback, 0.96, "💾 Saving to database...")

            from backend.database.connection import get_task_db
            from backend.database.database_operations import DatabaseOperations

            async with get_task_db() as db:
                db_ops = DatabaseOperations(db)
                
                # Save film and get film_id
                film_id = await db_ops.create_film(analysis_result)
                
                logger.info(f"💾 Film saved with ID: {film_id}")
                
                # Update analysis_result with film_id
                analysis_result['film_id'] = film_id
                
                # Update job with film_id
                await db_ops.update_job_status(
                    job_id,
                    status='processing',
                    progress=0.97,
                    current_stage='Database save complete',
                    film_id=film_id
                )

            self._update_progress(progress_callback, 0.97, "✓ Saved to database")
            
            # ============================================================
            # STAGE 11: Sync to Supabase (REMOVED - Now handled in video_tasks.py)
            # ============================================================
            # NOTE: Supabase sync has been moved to video_tasks.py (after analysis completes)
            # This ensures we have access to the title_id from the frontend and prevents
            # duplicate title creation. The sync in video_tasks.py handles:
            # - Syncing with proper title_id (no duplicates)
            # - Proper user_id/uploaded_by attribution
            # - Frame uploads
            # - Poster uploads
            
            supabase_title_id = None  # Not used anymore - kept for backward compatibility
            self._update_progress(progress_callback, 0.97, "✓ Analysis complete - sync will happen in next stage")
            
            # ============================================================
            # STAGE 11.5: Upload Keyframes to Supabase (REMOVED - Now handled in video_tasks.py)
            # ============================================================
            # NOTE: Keyframe uploads have been moved to video_tasks.py
            # This prevents duplicate uploads and ensures proper title_id is used
            
            logger.info(f"✅ Complete analysis finished for: {video_info['title']}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Analysis pipeline failed: {e}")
            raise
    
    def _detect_scenes_from_shots(self, shots: list, audio_features: dict) -> list:
        """
        Detect scenes by grouping shots based on visual/audio continuity
        Simple heuristic: group consecutive shots with similar lighting
        """
        if not shots:
            return []
        
        scenes = []
        current_scene = {
            'scene_number': 1,
            'start_time': shots[0]['start_time'],
            'shots': [shots[0]],
        }
        
        for i in range(1, len(shots)):
            shot = shots[i]
            prev_shot = shots[i - 1]
            
            time_gap = shot['start_time'] - prev_shot['end_time']
            same_lighting = shot. get('lighting') == prev_shot.get('lighting')
            
            if time_gap < 5.0 and same_lighting:
                current_scene['shots'].append(shot)
            else:
                current_scene['end_time'] = prev_shot['end_time']
                current_scene['duration'] = current_scene['end_time'] - current_scene['start_time']
                current_scene['num_shots'] = len(current_scene['shots'])
                
                lightings = [s.get('lighting', 'unknown') for s in current_scene['shots']]
                current_scene['lighting'] = max(set(lightings), key=lightings.count)
                
                scenes.append(current_scene)
                
                current_scene = {
                    'scene_number': len(scenes) + 1,
                    'start_time': shot['start_time'],
                    'shots': [shot],
                }
        
        # Add final scene
        if current_scene['shots']:
            current_scene['end_time'] = shots[-1]['end_time']
            current_scene['duration'] = current_scene['end_time'] - current_scene['start_time']
            current_scene['num_shots'] = len(current_scene['shots'])
            
            lightings = [s.get('lighting', 'unknown') for s in current_scene['shots']]
            current_scene['lighting'] = max(set(lightings), key=lightings.count)
            
            scenes.append(current_scene)
        
        return scenes
    
    def _update_progress(self, callback, progress: float, status: str):
        """Update progress via callback"""
        if callback:
            callback(progress, status)
        # Convert to percentage manually to avoid format specifier issues
        progress_pct = int(progress * 100)
        logger.info(f"[{progress_pct}%] {status}")  # ✅ DÜZELTİLDİ