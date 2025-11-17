"""
Complete Audio Analysis Module
Transcription with Whisper + Audio features with Librosa
"""
import logging
from typing import Dict, List
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
    """Complete audio analysis with transcription and mood detection"""
    
    def __init__(self, whisper_model: str = "base", language: str = "en"):
        """
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            language: Target language for transcription
        """
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
    
    def analyze_complete(self, audio_path: str) -> Dict:
        """
        Complete audio analysis
        
        Returns:
            Dict with transcription and audio features
        """
        logger.info("🎵 Starting complete audio analysis...")
        
        result = {}
        
        # 1. Transcription
        transcript_data = self.transcribe(audio_path)
        result['transcript'] = transcript_data
        
        # 2. Audio features
        audio_features = self.analyze_audio_features(audio_path)
        result['audio_features'] = audio_features
        
        # 3. Generate text embedding for similarity
        if transcript_data['text']:
            text_embedding = self.generate_text_embedding(transcript_data['text'])
            result['text_embedding'] = text_embedding
        
        # 4. Generate audio embedding (simple features)
        audio_embedding = self.generate_audio_embedding(audio_features)
        result['audio_embedding'] = audio_embedding
        
        logger.info("✓ Complete audio analysis finished")
        
        return result
    
    def transcribe(self, audio_path: str) -> Dict:
        """Transcribe audio to text using Whisper"""
        if not self.whisper_model:
            logger.warning("Whisper not available")
            return {
                'text': '',
                'segments': [],
                'language': 'unknown',
                'word_count': 0
            }
        
        try:
            logger.info("🎤 Transcribing audio with Whisper...")
            
            result = self.whisper_model.transcribe(
                audio_path,
                language=self.language if self.language != "auto" else None,
                task='transcribe',
                verbose=False,
                fp16=False  # Disable FP16 for CPU compatibility
            )
            
            transcript = result.get('text', '').strip()
            segments = result.get('segments', [])
            detected_language = result.get('language', self.language)
            
            # Process segments
            processed_segments = []
            for seg in segments:
                processed_segments.append({
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'text': seg.get('text', '').strip(),
                })
            
            word_count = len(transcript.split()) if transcript else 0
            
            logger.info(f"✓ Transcribed {len(transcript)} chars, {word_count} words")
            
            return {
                'text': transcript,
                'segments': processed_segments,
                'language': detected_language,
                'word_count': word_count,
                'num_segments': len(segments)
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                'text': '',
                'segments': [],
                'language': 'unknown',
                'word_count': 0
            }
    
    def analyze_audio_features(self, audio_path: str) -> Dict:
        """Extract audio features for mood/pacing analysis"""
        if not LIBROSA_AVAILABLE:
            logger.warning("Librosa not available")
            return self._default_features()
        
        try:
            logger.info("🎵 Analyzing audio features with Librosa...")
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050, duration=300)  # Max 5 min
            
            # 1. Tempo & Beats
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            tempo = float(tempo)
            
            # 2. Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            
            # 3. Energy (RMS)
            rms = librosa.feature.rms(y=y)[0]
            
            # 4. Zero Crossing Rate (speech indicator)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            # 5. MFCC (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            
            # Calculate statistics
            features = {
                'tempo': tempo,
                'avg_energy': float(np.mean(rms)),
                'max_energy': float(np.max(rms)),
                'spectral_brightness': float(np.mean(spectral_centroids)),
                'spectral_rolloff': float(np.mean(spectral_rolloff)),
                'speech_ratio': float(np.mean(zcr > 0.1)),
                'dynamic_range': float(np.max(rms) - np.min(rms)),
            }
            
            # Classify mood based on features
            features['mood'] = self._classify_mood(features)
            features['intensity'] = self._calculate_intensity(features)
            features['pacing'] = self._classify_pacing(features)
            
            logger.info(f"✓ Audio features extracted (mood: {features['mood']}, pacing: {features['pacing']})")
            
            return features
            
        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return self._default_features()
    
    def _classify_mood(self, features: Dict) -> str:
        """Classify overall mood from audio features"""
        tempo = features['tempo']
        energy = features['avg_energy']
        brightness = features['spectral_brightness']
        
        # Simple heuristic classification
        if tempo > 140 and energy > 0.15:
            return "energetic"
        elif tempo < 70 and energy < 0.08:
            return "melancholic"
        elif energy > 0.2 or brightness > 3000:
            return "tense"
        elif tempo < 80:
            return "calm"
        elif tempo > 120:
            return "upbeat"
        else:
            return "neutral"
    
    def _calculate_intensity(self, features: Dict) -> float:
        """Calculate overall audio intensity (0-1)"""
        # Normalize features
        tempo_norm = min(features['tempo'] / 180, 1.0)
        energy_norm = min(features['avg_energy'] / 0.3, 1.0)
        brightness_norm = min(features['spectral_brightness'] / 4000, 1.0)
        
        # Weighted average
        intensity = (tempo_norm * 0.4 + energy_norm * 0.4 + brightness_norm * 0.2)
        
        return float(np.clip(intensity, 0.0, 1.0))
    
    def _classify_pacing(self, features: Dict) -> str:
        """Classify pacing from tempo"""
        tempo = features['tempo']
        
        if tempo < 70:
            return "very slow"
        elif tempo < 90:
            return "slow"
        elif tempo < 110:
            return "moderate"
        elif tempo < 130:
            return "fast"
        else:
            return "very fast"
    
    def _default_features(self) -> Dict:
        """Default features when Librosa unavailable"""
        return {
            'tempo': 120.0,
            'avg_energy': 0.1,
            'max_energy': 0.3,
            'spectral_brightness': 2000.0,
            'spectral_rolloff': 3000.0,
            'speech_ratio': 0.5,
            'dynamic_range': 0.2,
            'mood': 'neutral',
            'intensity': 0.5,
            'pacing': 'moderate'
        }
    
    def generate_text_embedding(self, text: str) -> np.ndarray:
        """
        Generate text embedding for similarity search
        Uses sentence-transformers if available, otherwise simple embedding
        """
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text)
            
            return embedding.astype(np.float32)
            
        except ImportError:
            # Fallback: simple TF-IDF-like embedding
            logger.warning("sentence-transformers not available, using simple embedding")
            
            # Simple word-based embedding (384-dim to match expected size)
            words = text.lower().split()
            embedding = np.zeros(384)
            
            for i, word in enumerate(words[:384]):
                embedding[i % 384] += hash(word) % 100 / 100.0
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding.astype(np.float32)
    
    def generate_audio_embedding(self, features: Dict) -> np.ndarray:
        """Generate audio embedding from features (128-dim)"""
        # Create feature vector
        feature_vector = np.array([
            features.get('tempo', 120) / 200,
            features.get('avg_energy', 0.1),
            features.get('spectral_brightness', 2000) / 4000,
            features.get('intensity', 0.5),
            # Pad to 128 dimensions
        ])
        
        # Pad to 128-dim
        embedding = np.zeros(128)
        embedding[:len(feature_vector)] = feature_vector
        
        # Add some variation based on mood
        mood_map = {
            'energetic': 1.0,
            'calm': 0.2,
            'tense': 0.8,
            'melancholic': 0.3,
            'upbeat': 0.9,
            'neutral': 0.5,
        }
        
        mood_val = mood_map.get(features.get('mood', 'neutral'), 0.5)
        embedding[10:20] = mood_val
        
        return embedding.astype(np.float32)
