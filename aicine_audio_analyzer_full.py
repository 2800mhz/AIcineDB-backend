"""
Audio Analysis Module
Handles transcription and audio feature extraction
"""
import logging
from typing import Dict
import numpy as np

logger = logging.getLogger(__name__)

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("Librosa not available")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class AudioAnalyzer:
    """Audio analysis including transcription and mood detection"""
    
    def __init__(self, whisper_model: str = "base", language: str = "en"):
        self.whisper_model_name = whisper_model
        self.language = language
        self.whisper_model = None
        
        if WHISPER_AVAILABLE:
            try:
                device = "cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
                logger.info(f"Loading Whisper model '{whisper_model}' on {device}...")
                self.whisper_model = whisper.load_model(whisper_model, device=device)
                logger.info("✓ Whisper model loaded")
            except Exception as e:
                logger.error(f"Failed to load Whisper: {e}")
    
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio to text"""
        if not self.whisper_model:
            logger.warning("Whisper not available")
            return {'text': '', 'segments': [], 'language': 'unknown'}
        
        try:
            logger.info("🎤 Transcribing audio...")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language=self.language,
                task='transcribe',
                verbose=False
            )
            
            transcript = result.get('text', '')
            segments = result.get('segments', [])
            
            logger.info(f"✓ Transcribed {len(transcript)} characters")
            
            return {
                'text': transcript,
                'segments': segments,
                'language': result.get('language', self.language),
                'num_segments': len(segments)
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {'text': '', 'segments': [], 'language': 'unknown'}
    
    def analyze_audio_features(self, audio_path: str) -> Dict:
        """Extract audio features for mood analysis"""
        if not LIBROSA_AVAILABLE:
            logger.warning("Librosa not available")
            return self._default_features()
        
        try:
            logger.info("🎵 Analyzing audio features...")
            
            y, sr = librosa.load(audio_path, sr=22050)
            
            # Tempo
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            
            # Energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Zero crossing rate
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            features = {
                'tempo': float(tempo),
                'avg_energy': float(np.mean(rms)),
                'spectral_brightness': float(np.mean(spectral_centroids)),
                'speech_ratio': float(np.mean(zcr > 0.1))
            }
            
            # Classify mood
            features['mood'] = self._classify_mood(features)
            features['intensity'] = self._calculate_intensity(features)
            features['pacing'] = self._classify_pacing(features)
            
            logger.info(f"✓ Audio features extracted (mood: {features['mood']})")
            
            return features
            
        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return self._default_features()
    
    def _classify_mood(self, features: Dict) -> str:
        """Classify mood from features"""
        tempo = features['tempo']
        energy = features['avg_energy']
        
        if tempo > 140 and energy > 0.1:
            return "energetic"
        elif tempo < 80:
            return "calm"
        elif energy > 0.15:
            return "tense"
        else:
            return "neutral"
    
    def _calculate_intensity(self, features: Dict) -> float:
        """Calculate overall intensity"""
        tempo_norm = min(features['tempo'] / 180, 1.0)
        energy_norm = min(features['avg_energy'] / 0.2, 1.0)
        return float((tempo_norm + energy_norm) / 2)
    
    def _classify_pacing(self, features: Dict) -> str:
        """Classify pacing"""
        tempo = features['tempo']
        
        if tempo < 80:
            return "slow"
        elif tempo < 120:
            return "moderate"
        else:
            return "fast"
    
    def _default_features(self) -> Dict:
        """Default features when analysis fails"""
        return {
            'tempo': 120.0,
            'avg_energy': 0.1,
            'spectral_brightness': 2000.0,
            'speech_ratio': 0.5,
            'mood': 'neutral',
            'intensity': 0.5,
            'pacing': 'moderate'
        }
