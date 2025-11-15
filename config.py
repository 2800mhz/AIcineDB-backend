# Configuration for AI Cine Analyzer

class Config:
    # Video Processing
    VIDEO_PROCESSING = {
        'enabled': True,
        'settings': {
            'resolution': '1080p',
            'frame_rate': 30,
            'codec': 'h264'
        }
    }

    # Face Detection
    FACE_DETECTION = {
        'enabled': True,
        'model': 'frontal_face_cascade.xml',
        'confidence_threshold': 0.75
    }

    # Scene Detection
    SCENE_DETECTION = {
        'enabled': True,
        'model': 'scene_detect_model.h5'
    }

    # Natural Language Processing (NLP)
    NLP = {
        'enabled': True,
        'model': 'nlp_model.bin',
        'language': 'en'
    }

    # Audio Analysis
    AUDIO_ANALYSIS = {
        'enabled': True,
        'settings': {
            'sample_rate': 44100,
            'channels': 2
        }
    }

    # Emotion Detection
    EMOTION_DETECTION = {
        'enabled': True,
        'model': 'emotion_model.h5'
    }

    # Character Analysis
    CHARACTER_ANALYSIS = {
        'enabled': True,
        'model': 'character_model.bin'
    }

    # Logging
    LOGGING = {
        'level': 'DEBUG',
        'file_path': 'logs/ai_cine_analyzer.log'
    }

    # Database Settings
    DATABASE = {
        'db_type': 'sqlite',
        'connection_string': 'sqlite:///ai_cine.db'
    }

    # API Settings
    API = {
        'enabled': True,
        'base_url': 'http://localhost:5000/api',
        'timeout': 30
    }