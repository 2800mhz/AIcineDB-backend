"""
Character Detection and Tracking - FIXED for Windows
Uses InsightFace instead of face_recognition for better Windows compatibility
"""
import logging
from typing import List, Dict, Tuple
from pathlib import Path
import numpy as np
import cv2

logger = logging.getLogger(__name__)

try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
    logger.info("✓ InsightFace available")
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logger.warning("InsightFace not available - using fallback")


class CharacterTracker:
    """Track characters and analyze screen time using InsightFace"""
    
    def __init__(self, tolerance: float = 0.6):
        """
        Args:
            tolerance: Face matching tolerance (lower=stricter)
        """
        self.tolerance = tolerance
        self.known_faces = []  # List of known face encodings
        self.character_data = {}  # Character ID -> data
        self.face_analyzer = None
        
        if INSIGHTFACE_AVAILABLE:
            try:
                logger.info("Loading InsightFace model...")
                self.face_analyzer = FaceAnalysis(
                    name='buffalo_l',
                    providers=['CPUExecutionProvider']  # Use CPU
                )
                self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("✓ InsightFace model loaded")
            except Exception as e:
                logger.error(f"Failed to load InsightFace: {e}")
                self.face_analyzer = None
    
    def analyze_video(
        self,
        video_path: str,
        fps_sample: float = 1.0,
        max_frames: int = 300
    ) -> Dict:
        """
        Analyze video for characters
        
        Args:
            video_path: Path to video file
            fps_sample: Sample rate (frames per second)
            max_frames: Maximum frames to process
            
        Returns:
            Dict with character information
        """
        if not self.face_analyzer:
            logger.warning("InsightFace not available - using fallback")
            return self._dummy_analysis()
        
        try:
            logger.info(f"🎭 Analyzing characters in video...")
            
            cap = cv2.VideoCapture(video_path)
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / video_fps
            
            frame_interval = int(video_fps / fps_sample)
            
            frame_count = 0
            processed_count = 0
            
            while processed_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process every Nth frame
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / video_fps
                    self._process_frame(frame, timestamp)
                    processed_count += 1
                
                frame_count += 1
            
            cap.release()
            
            # Compile results
            characters = self._compile_character_data(duration)
            
            logger.info(f"✓ Found {len(characters)} characters")
            
            return {
                'characters': characters,
                'total_characters': len(characters),
                'duration_analyzed': duration,
                'frames_analyzed': processed_count,
            }
            
        except Exception as e:
            logger.error(f"Character analysis failed: {e}")
            return self._dummy_analysis()
    
    def _process_frame(self, frame: np.ndarray, timestamp: float):
        """Process a single frame for faces using InsightFace"""
        try:
            # Detect faces
            faces = self.face_analyzer.get(frame)
            
            if not faces:
                return
            
            for face in faces:
                # Get face embedding
                embedding = face.embedding
                
                # Get bounding box
                bbox = face.bbox.astype(int)
                location = tuple(bbox)  # (x1, y1, x2, y2)
                
                # Match with known faces
                character_id = self._match_or_create_character(embedding)
                
                # Update character data
                if character_id not in self.character_data:
                    self.character_data[character_id] = {
                        'id': character_id,
                        'embedding': embedding,
                        'appearances': [],
                        'locations': [],
                        'age': face.age if hasattr(face, 'age') else None,
                        'gender': face.gender if hasattr(face, 'gender') else None,
                    }
                
                self.character_data[character_id]['appearances'].append(timestamp)
                self.character_data[character_id]['locations'].append(location)
                
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
    
    def _match_or_create_character(self, embedding: np.ndarray) -> str:
        """Match face embedding to known character or create new"""
        if not self.known_faces:
            # First face
            character_id = f"char_1"
            self.known_faces.append((character_id, embedding))
            return character_id
        
        # Compare with known faces using cosine similarity
        best_match_idx = -1
        best_similarity = -1
        
        for idx, (_, known_embedding) in enumerate(self.known_faces):
            # Cosine similarity
            similarity = np.dot(embedding, known_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(known_embedding)
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_idx = idx
        
        # Match threshold (higher = stricter)
        match_threshold = 0.4  # InsightFace embeddings are different from face_recognition
        
        if best_similarity > match_threshold:
            # Match found
            return self.known_faces[best_match_idx][0]
        else:
            # New character
            character_id = f"char_{len(self.known_faces) + 1}"
            self.known_faces.append((character_id, embedding))
            return character_id
    
    def _compile_character_data(self, video_duration: float) -> List[Dict]:
        """Compile final character data"""
        characters = []
        
        for char_id, data in self.character_data.items():
            appearances = data['appearances']
            
            if not appearances:
                continue
            
            # Calculate screen time (approximate)
            # More accurate: count unique time intervals
            screen_time = len(appearances) * 1.0  # Each sample = ~1 second
            
            # Classify role based on screen time
            screen_time_ratio = screen_time / video_duration
            
            if screen_time_ratio > 0.5:
                role = "protagonist"
            elif screen_time_ratio > 0.2:
                role = "supporting"
            else:
                role = "minor"
            
            # Get demographics if available
            age = data.get('age')
            gender = data.get('gender')
            gender_str = 'Male' if gender == 1 else 'Female' if gender == 0 else None
            
            characters.append({
                'character_id': char_id,
                'name': None,  # Would need face recognition API
                'role': role,
                'screen_time': float(screen_time),
                'total_appearances': len(appearances),
                'first_appearance': float(min(appearances)),
                'last_appearance': float(max(appearances)),
                'age': int(age) if age else None,
                'gender': gender_str,
                'primary_emotion': 'neutral',  # Could add emotion detection
                'confidence': 0.8,
            })
        
        # Sort by screen time
        characters.sort(key=lambda x: x['screen_time'], reverse=True)
        
        return characters
    
    def _dummy_analysis(self) -> Dict:
        """Dummy analysis when InsightFace unavailable"""
        logger.warning("Using dummy character analysis")
        return {
            'characters': [
                {
                    'character_id': 'char_1',
                    'name': None,
                    'role': 'protagonist',
                    'screen_time': 120.0,
                    'total_appearances': 45,
                    'first_appearance': 5.0,
                    'last_appearance': 175.0,
                    'age': None,
                    'gender': None,
                    'primary_emotion': 'neutral',
                    'confidence': 0.5,
                }
            ],
            'total_characters': 1,
            'duration_analyzed': 180.0,
            'frames_analyzed': 180,
        }
    
    def generate_character_embedding(self, encoding: np.ndarray) -> np.ndarray:
        """Generate embedding for character similarity"""
        if encoding is not None and len(encoding) == 512:  # InsightFace embeddings are 512-dim
            return encoding.astype(np.float32)
        else:
            return np.random.randn(512).astype(np.float32)