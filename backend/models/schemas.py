"""
Pydantic Models for API Request/Response Schemas - FIXED
"""
from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import json


# ============================================================================
# ENUMS
# ============================================================================

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SimilarityType(str, Enum):
    VISUAL = "visual"
    NARRATIVE = "narrative"
    AUDIO = "audio"
    COMBINED = "combined"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request to analyze a video"""
    url: HttpUrl
    title_id: Optional[str] = None  # ✅ YENİ: Supabase title UUID
    priority: str = "normal"
    force_reanalyze: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title_id": "0343e566-498d-4ac5-b39d-da3453dcabcc",  # ✅ Example
                "priority": "normal",
                "force_reanalyze": False
            }
        }


class SearchFilters(BaseModel):
    """Filters for film search"""
    theme: Optional[str] = Field(None, description="Theme keyword (e.g., 'isolation', 'love')")
    genre: Optional[List[str]] = Field(None, description="Genre filter")
    min_duration: Optional[float] = Field(None, ge=0, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(None, ge=0, description="Maximum duration in seconds")
    style: Optional[str] = Field(None, description="Visual style (e.g., 'anime', 'noir')")
    mood: Optional[str] = Field(None, description="Audio mood (e.g., 'calm', 'tense')")
    
    class Config:
        schema_extra = {
            "example": {
                "theme": "isolation",
                "min_duration": 60,
                "max_duration": 600,
                "mood": "melancholic"
            }
        }


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str


class AnalysisJobResponse(BaseModel):
    """Analysis job status"""
    job_id: int
    url: str
    status: JobStatus
    progress: float = 0.0
    current_stage: Optional[str] = None
    film_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": 123,
                "url": "https://youtube.com/watch?v=abc",
                "status": "processing",
                "progress": 0.45,
                "current_stage": "Analyzing narrative",
                "created_at": "2024-01-20T10:30:00Z"
            }
        }


class Theme(BaseModel):
    """Theme with prevalence"""
    name: str
    description: Optional[str] = None
    prevalence: float = Field(ge=0.0, le=1.0)


class FilmSummary(BaseModel):
    """Film summary for list view"""
    id: int
    title: str
    duration: float
    url: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    style_fingerprint: Optional[str] = None
    themes: List[str] = []
    
    class Config:
        schema_extra = {
            "example": {
                "id": 456,
                "title": "AI Generated Short Film",
                "duration": 180.5,
                "analyzed_at": "2024-01-20T15:45:00Z",
                "style_fingerprint": "anime-cyberpunk-neon",
                "themes": ["isolation", "technology", "identity"]
            }
        }


class ShotInfo(BaseModel):
    """Shot information"""
    shot_number: int
    start_time: float
    end_time: float
    duration: float
    shot_type: Optional[str] = None
    lighting: Optional[str] = None
    brightness: Optional[float] = None
    colors: List[str] = []


class CharacterInfo(BaseModel):
    """Character information"""
    character_id: str
    name: Optional[str] = None
    role: Optional[str] = None
    screen_time: float
    total_appearances: int
    primary_emotion: Optional[str] = None


class SceneInfo(BaseModel):
    """Scene information"""
    scene_number: int
    start_time: float
    end_time: float
    duration: float
    lighting: Optional[str] = None
    emotion: Optional[str] = None
    pacing: Optional[str] = None
    description: Optional[str] = None


class NarrativeInfo(BaseModel):
    """Narrative analysis"""
    logline: Optional[str] = None
    synopsis: Optional[str] = None
    themes: List[Theme] = []
    genre: List[str] = []
    tone: List[str] = []
    conflict_type: Optional[str] = None
    emotional_arc: List[float] = []


class AudioInfo(BaseModel):
    """Audio features"""
    tempo: Optional[float] = None
    mood: Optional[str] = None
    intensity: Optional[float] = None
    pacing: Optional[str] = None
    speech_ratio: Optional[float] = None


class TranscriptInfo(BaseModel):
    """Transcript information"""
    text: Optional[str] = None
    language: Optional[str] = None
    word_count: Optional[int] = None


class FilmDetail(BaseModel):
    """Complete film analysis - FIXED for metadata field"""
    id: int
    title: str
    duration: float
    url: Optional[str] = None
    uploader: Optional[str] = None
    analyzed_at: Optional[datetime] = None
    
    # FIXED: metadata can be string (from DB) or dict
    metadata: Optional[Union[Dict[str, Any], str]] = None
    
    # Analysis results
    narrative: Optional[NarrativeInfo] = None
    transcript: Optional[TranscriptInfo] = None
    audio_features: Optional[AudioInfo] = None
    shots: List[ShotInfo] = []
    characters: List[CharacterInfo] = []
    scenes: List[SceneInfo] = []
    
    @validator('metadata', pre=True)
    def parse_metadata(cls, v):
        """Parse metadata if it's a JSON string"""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v if v is not None else {}
    
    class Config:
        schema_extra = {
            "example": {
                "id": 456,
                "title": "AI Generated Short Film",
                "duration": 180.5,
                "analyzed_at": "2024-01-20T15:45:00Z",
                "narrative": {
                    "logline": "A lone AI explores the meaning of consciousness.",
                    "themes": [
                        {"name": "identity", "prevalence": 0.8},
                        {"name": "technology", "prevalence": 0.6}
                    ],
                    "genre": ["sci-fi", "drama"],
                    "tone": ["melancholic", "philosophical"]
                }
            }
        }


class SimilarFilm(BaseModel):
    """Similar film result"""
    film_id: int
    title: str
    similarity: float = Field(ge=0.0, le=1.0)
    style_fingerprint: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "film_id": 789,
                "title": "Another AI Film",
                "similarity": 0.87,
                "style_fingerprint": "anime-cyberpunk-neon"
            }
        }


# ============================================================================
# INTERNAL MODELS (for analyzers)
# ============================================================================

class Shot(BaseModel):
    """Shot data class"""
    shot_number: int
    start_time: float
    end_time: float
    duration: float
    shot_type: str = "unknown"
    
    def to_dict(self) -> Dict:
        return self.dict()


class AnalysisResult(BaseModel):
    """Complete analysis result from pipeline"""
    film_id: int
    
    # Cinematography
    total_shots: int
    avg_shot_length: float
    shots: List[Shot]
    
    # Visual
    style_fingerprint: str
    color_palette: List[str]
    
    # Narrative
    narrative: Dict[str, Any]
    
    # Audio
    audio_features: Dict[str, Any]
    
    # Transcript
    transcript: Dict[str, Any]
    
    # Characters
    characters: List[Dict[str, Any]]
    
    # Scenes
    scenes: List[Dict[str, Any]]