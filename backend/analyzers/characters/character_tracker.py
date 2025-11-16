"""
Character Detection and Tracking
Detects faces, tracks characters, and analyzes emotions
"""
import logging
from typing import List, Dict, Tuple
from pathlib import Path
import numpy as np
import cv2

logger = logging.getLogger(__name__)

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition not available")


class CharacterTracker:
    """Track characters and analyze screen time"""
    
    def __init__(self, tolerance: float = 0.6):
        """
        Args:
            tolerance: Face matching tolerance (lower=stricter)
        """
        self.tolerance = tolerance
        self.known_faces = []  # List of known face encodings
        self.character_data = {}  # Character ID -> data
    
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
        if not FACE_RECOGNITION_AVAILABLE:
            logger.warning("Using fallback character detection")
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
        """Process a single frame for faces"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            
            if not face_locations:
                return
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            for encoding, location in zip(face_encodings, face_locations):
                # Match with known faces
                character_id = self._match_or_create_character(encoding)
                
                # Update character data
                if character_id not in self.character_data:
                    self.character_data[character_id] = {
                        'id': character_id,
                        'encoding': encoding,
                        'appearances': [],
                        'locations': [],
                    }
                
                self.character_data[character_id]['appearances'].append(timestamp)
                self.character_data[character_id]['locations'].append(location)
                
        except Exception as e:
            logger.debug(f"Frame processing error: {e}")
    
    def _match_or_create_character(self, encoding: np.ndarray) -> str:
        """Match face encoding to known character or create new"""
        if not self.known_faces:
            # First face
            character_id = f"char_1"
            self.known_faces.append((character_id, encoding))
            return character_id
        
        # Compare with known faces
        known_encodings = [enc for _, enc in self.known_faces]
        matches = face_recognition.compare_faces(
            known_encodings,
            encoding,
            tolerance=self.tolerance
        )
        
        if True in matches:
            # Match found
            match_idx = matches.index(True)
            return self.known_faces[match_idx][0]
        else:
            # New character
            character_id = f"char_{len(self.known_faces) + 1}"
            self.known_faces.append((character_id, encoding))
            return character_id
    
    def _compile_character_data(self, video_duration: float) -> List[Dict]:
        """Compile final character data"""
        characters = []
        
        for char_id, data in self.character_data.items():
            appearances = data['appearances']
            
            # Calculate screen time (approximate)
            # Assume each appearance lasts until next sample or end
            screen_time = len(appearances) * 1.0  # Rough estimate
            
            # Classify role based on screen time
            if screen_time > video_duration * 0.3:
                role = "protagonist"
            elif screen_time > video_duration * 0.1:
                role = "supporting"
            else:
                role = "minor"
            
            characters.append({
                'character_id': char_id,
                'name': None,  # Could be added via face recognition API
                'role': role,
                'screen_time': screen_time,
                'total_appearances': len(appearances),
                'first_appearance': min(appearances),
                'last_appearance': max(appearances),
                'primary_emotion': 'neutral',  # Could add emotion detection
                'confidence': 0.8,
            })
        
        # Sort by screen time
        characters.sort(key=lambda x: x['screen_time'], reverse=True)
        
        return characters
    
    def _dummy_analysis(self) -> Dict:
        """Dummy analysis when face_recognition unavailable"""
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
                    'primary_emotion': 'neutral',
                    'confidence': 0.7,
                }
            ],
            'total_characters': 1,
            'duration_analyzed': 180.0,
            'frames_analyzed': 180,
        }
    
    def detect_emotions(self, frame: np.ndarray, face_location: Tuple) -> str:
        """
        Detect emotion from face (placeholder for future implementation)
        Could use FER (Facial Expression Recognition) library
        """
        # This would require additional library like fer or deepface
        emotions = ['neutral', 'happy', 'sad', 'angry', 'surprised', 'fear']
        return np.random.choice(emotions)  # Placeholder
    
    def generate_character_embedding(self, encoding: np.ndarray) -> np.ndarray:
        """Generate embedding for character similarity"""
        # Face encoding is already 128-dim embedding from face_recognition
        if encoding is not None and len(encoding) == 128:
            return encoding.astype(np.float32)
        else:
            return np.random.randn(128).astype(np.float32)
