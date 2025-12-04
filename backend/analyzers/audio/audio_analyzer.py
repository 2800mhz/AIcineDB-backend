"""
Complete Audio Analysis Module
Transcription with Whisper + Audio features with Librosa
"""
import logging
import os  # ⚠️ BU EKSİKTİ - MUTLAKA EKLEYİN!
from typing import Dict, List
import numpy as np

# Compatibility fix for scipy >= 1.8.0
# scipy.signal.hann was moved to scipy.signal.windows.hann
try:
    import scipy
    import scipy.signal
    if not hasattr(scipy.signal, 'hann'):
        scipy.signal.hann = scipy.signal.windows.hann
except ImportError:
    pass  # scipy not installed, will be handled later

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
        """Complete audio analysis"""
        logger.info("🎵 Starting complete audio analysis...")
        
        result = {}
        
        # 1. Transcription
        transcript_data = self.transcribe(audio_path)
        result['transcript'] = transcript_data
        
        # 2. Audio features - DETAYLI HATA YAKALAMA
        try:
            audio_features = self.analyze_audio_features(audio_path)
            result['audio_features'] = audio_features
            logger.info(f"✅ Audio features: tempo={audio_features.get('tempo', 'N/A')}")
        except Exception as e:
            logger.error(f"❌ CRITICAL: analyze_audio_features crashed: {e}", exc_info=True)
            result['audio_features'] = self._default_features()
        
        # 3. Generate text embedding
        if transcript_data['text']:
            text_embedding = self.generate_text_embedding(transcript_data['text'])
            result['text_embedding'] = text_embedding
        
        # 4. Generate audio embedding
        audio_embedding = self.generate_audio_embedding(result['audio_features'])
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
            # YOL NORMALİZASYONU EKLENDİ
            normalized_path = os.path.normpath(audio_path)
            logger.info(f"🎤 Transcribing: {normalized_path}")
            
            result = self.whisper_model.transcribe(
                normalized_path,
                language=self.language if self.language != "auto" else None,
                task='transcribe',
                verbose=False,
                fp16=False
            )
            
            transcript = result.get('text', '').strip()
            segments = result.get('segments', [])
            detected_language = result.get('language', self.language)
            
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
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return {
                'text': '',
                'segments': [],
                'language': 'unknown',
                'word_count': 0
            }
    
    def analyze_audio_features(self, audio_path: str) -> Dict:
        """Extract audio features with EXTENSIVE debugging"""
        
        # ===== KRİTİK DEBUG BAŞLANGIÇ =====
        print("\n" + "="*70)
        print("🔍 AUDIO ANALYSIS DEBUG START")
        print("="*70)
        print(f"LIBROSA_AVAILABLE: {LIBROSA_AVAILABLE}")
        print(f"Received audio_path: '{audio_path}'")
        
        logger.error("="*70)
        logger.error("🔍 AUDIO ANALYSIS DEBUG START")
        logger.error(f"LIBROSA_AVAILABLE: {LIBROSA_AVAILABLE}")
        logger.error(f"Received audio_path: '{audio_path}'")
        
        if not LIBROSA_AVAILABLE:
            print("❌ LIBROSA NOT INSTALLED!")
            logger.error("❌ LIBROSA NOT INSTALLED!")
            print("="*70 + "\n")
            logger.error("="*70)
            return self._default_features("Librosa not installed")
        
        try:
            # ===== YOL NORMALİZASYONU =====
            normalized_path = os.path.normpath(audio_path)
            abs_path = os.path.abspath(normalized_path)
            
            print(f"📂 Original path: '{audio_path}'")
            print(f"📂 Normalized path: '{normalized_path}'")
            print(f"📂 Absolute path: '{abs_path}'")
            
            logger.error(f"📂 Original: '{audio_path}'")
            logger.error(f"📂 Normalized: '{normalized_path}'")
            logger.error(f"📂 Absolute: '{abs_path}'")
            
            # ===== DOSYA VAR MI? =====
            exists = os.path.exists(normalized_path)
            print(f"📋 File exists: {exists}")
            logger.error(f"📋 File exists: {exists}")
            
            if not exists:
                print(f"❌ FILE NOT FOUND: {normalized_path}")
                logger.error(f"❌ FILE NOT FOUND: {normalized_path}")
                
                # Alternatif yolları dene
                alternatives = [
                    audio_path.replace('\\\\', '\\'),
                    audio_path.replace('\\app\\', 'app\\'),
                    'data\\audio\\' + os.path.basename(audio_path),
                ]
                
                print("🔍 Trying alternatives:")
                logger.error("🔍 Trying alternatives:")
                
                for alt in alternatives:
                    alt_exists = os.path.exists(alt)
                    print(f"  - {alt}: {alt_exists}")
                    logger.error(f"  - {alt}: {alt_exists}")
                
                print("="*70 + "\n")
                logger.error("="*70)
                return self._default_features(f"File not found: {normalized_path}")
            
            # ===== DOSYA BOYUTU =====
            file_size = os.path.getsize(normalized_path)
            print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            logger.error(f"📊 File size: {file_size:,} bytes")
            
            if file_size < 10000:
                print(f"⚠️ File too small: {file_size} bytes")
                logger.error(f"⚠️ File too small: {file_size} bytes")
                print("="*70 + "\n")
                logger.error("="*70)
                return self._default_features(f"File too small: {file_size} bytes")
            
            # ===== LIBROSA YÜKLEME =====
            print("🎵 Loading with librosa...")
            logger.error("🎵 Loading with librosa...")
            
            y, sr = librosa.load(normalized_path, sr=22050, duration=300)
            
            duration_sec = len(y) / sr
            print(f"✅ Audio loaded: {len(y):,} samples, {sr}Hz, {duration_sec:.1f}s")
            logger.error(f"✅ Audio loaded: {len(y):,} samples, {sr}Hz")
            
            # ===== ÖZELLİK ÇIKARIMI =====
            print("🎼 Extracting features...")
            logger.error("🎼 Extracting features...")
            
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            tempo = float(tempo)
            
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            rms = librosa.feature.rms(y=y)[0]
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            
            features = {
                'tempo': tempo,
                'avg_energy': float(np.mean(rms)),
                'max_energy': float(np.max(rms)),
                'spectral_brightness': float(np.mean(spectral_centroids)),
                'spectral_rolloff': float(np.mean(spectral_rolloff)),
                'speech_ratio': float(np.mean(zcr > 0.1)),
                'dynamic_range': float(np.max(rms) - np.min(rms)),
            }
            
            features['mood'] = self._classify_mood(features)
            features['intensity'] = self._calculate_intensity(features)
            features['pacing'] = self._classify_pacing(features)
            
            print(f"✅ Features extracted:")
            print(f"   - Tempo: {features['tempo']:.1f} BPM")
            print(f"   - Energy: {features['avg_energy']:.3f}")
            print(f"   - Mood: {features['mood']}")
            print("="*70 + "\n")
            
            logger.error(f"✅ Features: tempo={features['tempo']:.1f}, mood={features['mood']}")
            logger.error("="*70)
            
            return features
            
        except Exception as e:
            print(f"❌ EXCEPTION: {type(e).__name__}: {e}")
            print("="*70 + "\n")
            
            logger.error(f"❌ EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            logger.error("="*70)
            
            return self._default_features(str(e))
    
    def _classify_mood(self, features: Dict) -> str:
        tempo = features['tempo']
        energy = features['avg_energy']
        brightness = features['spectral_brightness']
        
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
        tempo_norm = min(features['tempo'] / 180, 1.0)
        energy_norm = min(features['avg_energy'] / 0.3, 1.0)
        brightness_norm = min(features['spectral_brightness'] / 4000, 1.0)
        
        intensity = (tempo_norm * 0.4 + energy_norm * 0.4 + brightness_norm * 0.2)
        
        return float(np.clip(intensity, 0.0, 1.0))
    
    def _classify_pacing(self, features: Dict) -> str:
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
    
    def _default_features(self, error_message: str = None) -> Dict:
        print("⚠️ Returning DEFAULT features")
        logger.warning("⚠️ Returning DEFAULT audio features")
        result = {
            'tempo': 120.0,
            'avg_energy': 0.1,
            'max_energy': 0.3,
            'spectral_brightness': 2000.0,
            'spectral_rolloff': 3000.0,
            'speech_ratio': 0.5,
            'dynamic_range': 0.2,
            'mood': 'neutral',
            'intensity': 0.5,
            'pacing': 'moderate',
            'energy': 0.5,
            'valence': 0.5
        }
        if error_message:
            result['error'] = f"Audio analysis failed: {error_message}"
        return result
    
    def generate_text_embedding(self, text: str) -> np.ndarray:
        """Generate text embedding"""
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(text)
            return embedding.astype(np.float32)
        except ImportError:
            logger.warning("sentence-transformers not available")
            words = text.lower().split()
            embedding = np.zeros(384)
            for i, word in enumerate(words[:384]):
                embedding[i % 384] += hash(word) % 100 / 100.0
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            return embedding.astype(np.float32)
    
    def generate_audio_embedding(self, features: Dict) -> np.ndarray:
        """Generate audio embedding from features"""
        feature_vector = np.array([
            features.get('tempo', 120) / 200,
            features.get('avg_energy', 0.1),
            features.get('spectral_brightness', 2000) / 4000,
            features.get('intensity', 0.5),
        ])
        
        embedding = np.zeros(128)
        embedding[:len(feature_vector)] = feature_vector
        
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