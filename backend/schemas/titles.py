"""
Hardened Pydantic schemas for titles with comprehensive validation
"""
import re
from typing import List, Optional
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    constr,
    ConfigDict
)
import bleach


class TitleBase(BaseModel):
    """Base title schema with common fields"""
    
    title: constr(min_length=1, max_length=200, strip_whitespace=True) = Field(
        description="Title name (1-200 characters)"
    )
    
    slug: Optional[constr(pattern=r'^[a-z0-9-]+$', max_length=250)] = Field(
        default=None,
        description="URL-friendly slug (auto-generated if not provided)"
    )
    
    description: constr(max_length=5000, strip_whitespace=True) = Field(
        description="Detailed description (max 5000 characters)"
    )
    
    logline: Optional[constr(max_length=500, strip_whitespace=True)] = Field(
        default=None,
        description="Short logline/tagline (max 500 characters)"
    )
    
    external_url: Optional[HttpUrl] = Field(
        default=None,
        description="External URL (must be valid HTTP/HTTPS)"
    )
    
    type: constr(pattern=r'^(movie|series|short)$') = Field(
        default='movie',
        description="Content type (movie/series/short)"
    )
    
    status: constr(pattern=r'^(draft|pending|completed|rejected)$') = Field(
        default='pending',
        description="Status (draft/pending/completed/rejected)"
    )
    
    genres: List[str] = Field(
        default=[],
        max_items=10,
        description="List of genres (max 10)"
    )
    
    tags: List[str] = Field(
        default=[],
        max_items=20,
        description="List of tags (max 20)"
    )
    
    moods: List[str] = Field(
        default=[],
        max_items=10,
        description="List of moods (max 10)"
    )
    
    year: Optional[int] = Field(
        default=None,
        ge=1888,  # First film ever made
        le=2100,
        description="Release year (1888-2100)"
    )
    
    duration: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Duration in minutes (1-1000)"
    )
    
    @field_validator('title', 'description', 'logline')
    @classmethod
    def sanitize_html(cls, v: Optional[str]) -> Optional[str]:
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Strips all HTML tags and potentially dangerous content.
        """
        if v is None:
            return v
        # Strip all HTML tags, no exceptions
        return bleach.clean(v, tags=[], strip=True)
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v: Optional[str], info) -> Optional[str]:
        """
        Auto-generate slug from title if not provided.
        
        Creates URL-friendly slug by:
        - Converting to lowercase
        - Replacing non-alphanumeric with hyphens
        - Removing leading/trailing hyphens
        - Limiting to 250 characters
        """
        if v:
            # If slug is provided, return as-is (will be validated by pattern)
            return v
        
        # Auto-generate from title
        if 'title' in info.data:
            title = info.data['title']
            # Convert to lowercase and replace non-alphanumeric with hyphens
            slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
            # Remove leading/trailing hyphens
            slug = slug.strip('-')
            # Limit length
            return slug[:250] if slug else None
        
        return v
    
    @field_validator('genres', 'tags', 'moods')
    @classmethod
    def clean_array_items(cls, v: List[str]) -> List[str]:
        """
        Clean and validate array items.
        
        - Strips whitespace
        - Removes empty strings
        - Removes duplicates
        - Limits length of each item to 50 characters
        """
        if not v:
            return []
        
        # Clean each item
        cleaned = []
        seen = set()
        
        for item in v:
            if isinstance(item, str):
                # Strip whitespace and limit length
                item = item.strip()[:50]
                
                # Skip empty or duplicate items
                if item and item.lower() not in seen:
                    cleaned.append(item)
                    seen.add(item.lower())
        
        return cleaned

    model_config = ConfigDict(
        extra='forbid',  # Reject extra fields not in schema
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "AI Generated Short Film",
                "description": "A stunning AI-generated film exploring the nature of consciousness.",
                "logline": "An AI discovers what it means to be alive.",
                "external_url": "https://youtube.com/watch?v=example",
                "type": "short",
                "status": "pending",
                "genres": ["Sci-Fi", "Drama"],
                "tags": ["AI", "Consciousness", "Philosophy"],
                "moods": ["Thoughtful", "Melancholic"],
                "year": 2024,
                "duration": 15
            }
        }
    )


class TitleCreate(TitleBase):
    """Schema for creating a new title"""
    
    # Override status to always be 'pending' for user-created content
    status: constr(pattern=r'^(draft|pending)$') = Field(
        default='pending',
        description="Status for new titles (draft/pending only)"
    )
    
    @field_validator('status')
    @classmethod
    def validate_create_status(cls, v: str) -> str:
        """
        Ensure user-created titles start as 'pending' or 'draft'.
        
        Only admins can directly create 'completed' titles.
        """
        if v not in ['draft', 'pending']:
            # Force to pending for security
            return 'pending'
        return v

    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "My AI Film",
                "description": "An experimental AI-generated film.",
                "type": "short",
                "genres": ["Experimental"],
                "tags": ["AI", "Art"]
            }
        }
    )


class TitleUpdate(BaseModel):
    """Schema for updating an existing title (partial updates allowed)"""
    
    title: Optional[constr(min_length=1, max_length=200, strip_whitespace=True)] = None
    description: Optional[constr(max_length=5000, strip_whitespace=True)] = None
    logline: Optional[constr(max_length=500, strip_whitespace=True)] = None
    external_url: Optional[HttpUrl] = None
    type: Optional[constr(pattern=r'^(movie|series|short)$')] = None
    genres: Optional[List[str]] = Field(default=None, max_items=10)
    tags: Optional[List[str]] = Field(default=None, max_items=20)
    moods: Optional[List[str]] = Field(default=None, max_items=10)
    year: Optional[int] = Field(default=None, ge=1888, le=2100)
    duration: Optional[int] = Field(default=None, ge=1, le=1000)
    
    @field_validator('title', 'description', 'logline')
    @classmethod
    def sanitize_html(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize HTML content"""
        if v is None:
            return v
        return bleach.clean(v, tags=[], strip=True)
    
    @field_validator('genres', 'tags', 'moods')
    @classmethod
    def clean_array_items(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Clean array items"""
        if not v:
            return v
        
        cleaned = []
        seen = set()
        
        for item in v:
            if isinstance(item, str):
                item = item.strip()[:50]
                if item and item.lower() not in seen:
                    cleaned.append(item)
                    seen.add(item.lower())
        
        return cleaned if cleaned else None
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "Updated Title",
                "description": "Updated description",
                "genres": ["Sci-Fi", "Thriller"]
            }
        }
    )


class TitleResponse(TitleBase):
    """Schema for title responses"""
    
    id: str = Field(description="Title UUID")
    uploaded_by: Optional[str] = Field(default=None, description="Uploader user ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Additional computed fields
    rating_average: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    rating_count: Optional[int] = Field(default=0, ge=0)
    view_count: Optional[int] = Field(default=0, ge=0)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "AI Generated Short Film",
                "slug": "ai-generated-short-film",
                "description": "A stunning AI-generated film.",
                "type": "short",
                "status": "completed",
                "genres": ["Sci-Fi"],
                "created_at": "2024-01-20T10:00:00Z",
                "rating_average": 8.5,
                "view_count": 1250
            }
        }
    )
