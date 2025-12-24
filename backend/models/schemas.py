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


# ============================================================================
# FESTIVAL MODELS
# ============================================================================

class FestivalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class FestivalBase(BaseModel):
    """Base model for festival"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=255)
    start_date: datetime
    end_date: datetime
    location: Optional[str] = None
    venue: Optional[str] = None
    categories: List[str] = []
    genres: List[str] = []
    rules: Optional[str] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    entry_fee: Optional[float] = Field(None, ge=0)
    website: Optional[str] = None
    contact_email: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "AI Cinema International Festival 2024",
                "slug": "ai-cinema-2024",
                "description": "Annual festival celebrating AI-generated films",
                "tagline": "The Future of Cinema",
                "start_date": "2024-06-01T00:00:00Z",
                "end_date": "2024-06-07T00:00:00Z",
                "location": "Istanbul, Turkey",
                "venue": "Digital Arts Center",
                "categories": ["short", "feature", "experimental"],
                "genres": ["sci-fi", "drama", "documentary"],
                "submission_end_date": "2024-05-01T00:00:00Z"
            }
        }


class FestivalCreate(FestivalBase):
    """Model for creating a festival"""
    pass


class FestivalUpdate(BaseModel):
    """Model for updating a festival (partial update)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tagline: Optional[str] = Field(None, max_length=255)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    categories: Optional[List[str]] = None
    genres: Optional[List[str]] = None
    rules: Optional[str] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    entry_fee: Optional[float] = Field(None, ge=0)
    website: Optional[str] = None
    contact_email: Optional[str] = None


class FestivalResponse(FestivalBase):
    """Model for festival response"""
    id: str
    created_by: str
    status: FestivalStatus
    is_creator_festival: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Stats
    total_submissions: int = 0
    total_followers: int = 0
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI Cinema International Festival 2024",
                "slug": "ai-cinema-2024",
                "status": "approved",
                "is_creator_festival": False,
                "created_by": "admin@example.com",
                "created_at": "2024-01-20T10:00:00Z",
                "total_submissions": 42,
                "total_followers": 128
            }
        }


class FestivalApplicationCreate(BaseModel):
    """Model for creator festival application"""
    festival_data: FestivalCreate
    motivation: Optional[str] = Field(None, description="Why you want to create this festival")
    
    class Config:
        schema_extra = {
            "example": {
                "festival_data": {
                    "name": "Turkish AI Film Festival",
                    "slug": "turkish-ai-festival",
                    "description": "Celebrating Turkish AI filmmakers"
                },
                "motivation": "I want to promote Turkish AI cinema"
            }
        }


class FestivalApplicationResponse(BaseModel):
    """Model for festival application response"""
    id: str
    user_id: str
    festival_data: Dict[str, Any]
    motivation: Optional[str] = None
    status: FestivalStatus
    festival_id: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None


class FestivalSubmissionCreate(BaseModel):
    """Model for submitting a film to a festival"""
    film_id: int
    category: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "film_id": 123,
                "category": "short",
                "notes": "This is my debut AI-generated film"
            }
        }


class FestivalSubmissionResponse(BaseModel):
    """Model for festival submission response"""
    id: str
    festival_id: str
    film_id: int
    user_id: str
    category: Optional[str] = None
    notes: Optional[str] = None
    status: SubmissionStatus
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    feedback: Optional[str] = None


class FestivalOrganizerCreate(BaseModel):
    """Model for adding a festival organizer"""
    user_id: str
    role: str = Field(default="organizer", description="Role of the organizer")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "organizer"
            }
        }


class FestivalEventCreate(BaseModel):
    """Model for creating a festival event"""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    event_date: datetime
    location: Optional[str] = None
    event_type: str = Field(default="screening", description="Type of event")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Opening Ceremony",
                "description": "Festival opening with keynote speech",
                "event_date": "2024-06-01T19:00:00Z",
                "location": "Main Hall",
                "event_type": "ceremony"
            }
        }


# ============================================================================
# CONTENT AGGREGATION MODELS
# ============================================================================

class DiscoveredFestivalResponse(BaseModel):
    """Model for discovered festival response"""
    id: str
    name: str
    external_url: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    location: Optional[str] = None
    country: Optional[str] = None
    category: List[str] = []
    genres: List[str] = []
    entry_fee: Optional[float] = None
    currency: Optional[str] = None
    ai_relevance_score: Optional[int] = None
    is_ai_film_friendly: bool = False
    prestige_score: Optional[int] = None
    source: Optional[str] = None
    status: str = "pending"
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI Cinema Festival 2024",
                "external_url": "https://example.com/festival",
                "description": "Festival celebrating AI-generated films",
                "location": "San Francisco, USA",
                "ai_relevance_score": 85,
                "is_ai_film_friendly": True,
                "prestige_score": 65,
                "status": "pending"
            }
        }


class DiscoveredFestivalApproval(BaseModel):
    """Model for approving/rejecting discovered festivals"""
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: Optional[str] = Field(None, description="Required if action is 'reject'")
    
    class Config:
        schema_extra = {
            "example": {
                "action": "approve"
            }
        }


class NewsArticleResponse(BaseModel):
    """Model for news article response"""
    id: str
    title: str
    summary: Optional[str] = None
    external_url: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    source_name: Optional[str] = None
    category: List[str] = []
    tags: List[str] = []
    ai_relevance_score: Optional[int] = None
    is_ai_cinema_relevant: bool = False
    published_at: Optional[datetime] = None
    is_archived: bool = False
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "AI-Generated Films Take Cannes by Storm",
                "summary": "This year's festival features unprecedented AI content...",
                "external_url": "https://variety.com/article",
                "image_url": "https://example.com/image.jpg",
                "source_name": "Variety",
                "ai_relevance_score": 92,
                "is_ai_cinema_relevant": True,
                "category": ["festivals", "technology"],
                "tags": ["ai", "cannes", "filmmaking"]
            }
        }


class NewsSourceResponse(BaseModel):
    """Model for news source response"""
    id: str
    name: str
    url: str
    source_type: str = "rss"
    is_active: bool = True
    fetch_interval_hours: int = 6
    last_fetched_at: Optional[datetime] = None
    total_articles_fetched: int = 0
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Variety",
                "url": "https://variety.com/feed/",
                "source_type": "rss",
                "is_active": True,
                "total_articles_fetched": 1250
            }
        }


class NewsSourceCreate(BaseModel):
    """Model for creating a news source"""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    source_type: str = Field(default="rss", description="'rss', 'api', or 'scraper'")
    is_active: bool = True
    fetch_interval_hours: int = Field(default=6, ge=1, le=168)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Custom Film Blog",
                "url": "https://example.com/feed.xml",
                "source_type": "rss",
                "is_active": True,
                "fetch_interval_hours": 12
            }
        }


class FestivalSourceResponse(BaseModel):
    """Model for festival source response"""
    id: str
    name: str
    url: str
    source_type: str = "scraper"
    is_active: bool = True
    scrape_interval_hours: int = 24
    last_scraped_at: Optional[datetime] = None
    total_festivals_found: int = 0
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "FilmFreeway",
                "url": "https://filmfreeway.com/festivals",
                "source_type": "scraper",
                "is_active": True,
                "total_festivals_found": 450
            }
        }


class FestivalSourceCreate(BaseModel):
    """Model for creating a festival source"""
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1)
    source_type: str = Field(default="scraper", description="'scraper', 'rss', or 'api'")
    is_active: bool = True
    scrape_interval_hours: int = Field(default=24, ge=1, le=168)
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Custom Festival Directory",
                "url": "https://example.com/festivals",
                "source_type": "scraper",
                "is_active": True,
                "scrape_interval_hours": 48
            }
        }


class ScrapingJobResponse(BaseModel):
    """Model for scraping job response"""
    id: str
    job_type: str
    source: Optional[str] = None
    status: str
    items_found: int = 0
    items_new: int = 0
    items_updated: int = 0
    items_duplicates: int = 0
    items_filtered: int = 0
    error_message: Optional[str] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "job_type": "festivals",
                "source": "all",
                "status": "completed",
                "items_found": 150,
                "items_new": 42,
                "items_duplicates": 18,
                "items_filtered": 90,
                "duration_seconds": 245,
                "started_at": "2024-01-20T03:00:00Z",
                "completed_at": "2024-01-20T03:04:05Z"
            }
        }


class ManualTriggerResponse(BaseModel):
    """Response for manually triggered tasks"""
    task_id: str
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "abc123-def456",
                "message": "Festival scraping task started"
            }
        }