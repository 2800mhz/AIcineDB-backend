"""
SQLAlchemy Models for AIcineDB
Includes pgvector support for embeddings
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, 
    ForeignKey, JSON, Boolean, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

# pgvector support
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    # Fallback if pgvector not available
    PGVECTOR_AVAILABLE = False
    Vector = Text

Base = declarative_base()


class Film(Base):
    """Main films table with embeddings"""
    __tablename__ = 'films'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    duration = Column(Float)  # in seconds
    
    # Video metadata
    uploader = Column(String(200))
    resolution = Column(String(50))
    fps = Column(Float)
    
    # Embeddings for similarity search
    visual_embedding = Column(Vector(512) if PGVECTOR_AVAILABLE else Text)
    text_embedding = Column(Vector(384) if PGVECTOR_AVAILABLE else Text)
    audio_embedding = Column(Vector(128) if PGVECTOR_AVAILABLE else Text)
    
    # Style fingerprint (short string representation)
    style_fingerprint = Column(String(200))
    
    # JSON metadata
    metadata = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    narrative = relationship("Narrative", back_populates="film", uselist=False)
    transcript = relationship("Transcript", back_populates="film", uselist=False)
    audio_features = relationship("AudioFeature", back_populates="film", uselist=False)
    shots = relationship("Shot", back_populates="film", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="film", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="film", cascade="all, delete-orphan")


class AnalysisJob(Base):
    """Track analysis jobs"""
    __tablename__ = 'analysis_jobs'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(1000), nullable=False)
    status = Column(String(50), default='pending')  # pending, queued, processing, completed, failed
    priority = Column(Integer, default=5)
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    current_stage = Column(String(200))
    
    # Celery task info
    celery_task_id = Column(String(100))
    
    # Results
    film_id = Column(Integer, ForeignKey('films.id'), nullable=True)
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationship
    film = relationship("Film")


class Narrative(Base):
    """Narrative analysis from Gemini AI"""
    __tablename__ = 'narratives'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), unique=True, nullable=False)
    
    # Core narrative elements
    summary = Column(Text)
    genre = Column(String(100))
    themes = Column(ARRAY(String))
    tone = Column(String(100))
    
    # Three-act structure
    act1_description = Column(Text)
    act2_description = Column(Text)
    act3_description = Column(Text)
    
    # Story beats
    story_beats = Column(JSON)  # List of beat objects
    
    # Character analysis
    protagonist = Column(Text)
    antagonist = Column(Text)
    supporting_characters = Column(Text)
    
    # Analysis notes
    cinematography_notes = Column(Text)
    audio_notes = Column(Text)
    emotional_arc = Column(Text)
    
    # Key quotes
    key_quotes = Column(ARRAY(Text))
    
    # Raw AI response
    raw_analysis = Column(JSON)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="narrative")


class Transcript(Base):
    """Audio transcription"""
    __tablename__ = 'transcripts'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), unique=True, nullable=False)
    
    # Transcript data
    text = Column(Text)
    word_count = Column(Integer)
    language = Column(String(10))
    
    # Segments with timestamps
    segments = Column(JSON)  # List of segment objects with start/end/text
    
    # Whisper model used
    model_used = Column(String(50))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="transcript")


class AudioFeature(Base):
    """Audio features extracted with librosa"""
    __tablename__ = 'audio_features'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), unique=True, nullable=False)
    
    # Audio properties
    tempo = Column(Float)  # BPM
    key = Column(String(10))
    mode = Column(String(20))  # major/minor
    
    # Mood/energy
    energy = Column(Float)  # 0-1
    valence = Column(Float)  # 0-1 (sad to happy)
    
    # Rhythm
    beat_count = Column(Integer)
    rhythm_complexity = Column(Float)
    
    # Spectral features
    spectral_centroid_mean = Column(Float)
    spectral_rolloff_mean = Column(Float)
    zero_crossing_rate_mean = Column(Float)
    
    # MFCC features (JSON array)
    mfcc_features = Column(JSON)
    
    # Raw features
    raw_features = Column(JSON)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="audio_features")


class Shot(Base):
    """Individual shots detected"""
    __tablename__ = 'shots'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), nullable=False)
    
    shot_number = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float)
    
    # Shot classification
    shot_type = Column(String(50))  # close-up, medium, wide, etc.
    camera_movement = Column(String(50))  # static, pan, tilt, tracking, etc.
    lighting = Column(String(50))  # high-key, low-key, natural, etc.
    
    # Keyframe info
    keyframe_path = Column(String(500))
    keyframe_timestamp = Column(Float)
    
    # Visual features
    dominant_colors = Column(JSON)  # List of RGB colors
    brightness = Column(Float)
    contrast = Column(Float)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="shots")


class Character(Base):
    """Characters detected and tracked"""
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), nullable=False)
    
    character_number = Column(Integer, nullable=False)
    
    # Appearance info
    first_appearance = Column(Float)  # timestamp
    last_appearance = Column(Float)
    screen_time = Column(Float)  # total seconds
    
    # Detection info
    total_detections = Column(Integer)
    confidence_avg = Column(Float)
    
    # Visual features
    face_encoding = Column(JSON)  # Face embedding
    sample_image_path = Column(String(500))
    
    # Analysis
    prominent_emotions = Column(ARRAY(String))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="characters")


class Scene(Base):
    """Scenes (groups of shots)"""
    __tablename__ = 'scenes'
    
    id = Column(Integer, primary_key=True)
    film_id = Column(Integer, ForeignKey('films.id'), nullable=False)
    
    scene_number = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float)
    
    # Scene properties
    num_shots = Column(Integer)
    lighting = Column(String(50))
    location_type = Column(String(100))  # interior/exterior, day/night
    
    # Characters present
    character_ids = Column(ARRAY(Integer))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    film = relationship("Film", back_populates="scenes")


# Database initialization SQL for pgvector
INIT_SQL = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS films_visual_embedding_idx ON films USING ivfflat (visual_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS films_text_embedding_idx ON films USING ivfflat (text_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS films_audio_embedding_idx ON films USING ivfflat (audio_embedding vector_cosine_ops);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS analysis_jobs_status_idx ON analysis_jobs(status);
CREATE INDEX IF NOT EXISTS analysis_jobs_created_at_idx ON analysis_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS films_analyzed_at_idx ON films(analyzed_at DESC) WHERE analyzed_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS shots_film_id_idx ON shots(film_id, shot_number);
CREATE INDEX IF NOT EXISTS characters_film_id_idx ON characters(film_id);
CREATE INDEX IF NOT EXISTS scenes_film_id_idx ON scenes(film_id, scene_number);
"""
