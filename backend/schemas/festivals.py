"""
Hardened Pydantic schemas for festivals with comprehensive validation
"""
import re
from typing import List, Optional
from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    EmailStr,
    field_validator,
    constr,
    ConfigDict,
    ValidationInfo,
)
import bleach


class FestivalBase(BaseModel):
    """Base festival schema with common fields"""
    
    name: constr(min_length=1, max_length=255, strip_whitespace=True) = Field(
        description="Festival name (1-255 characters)"
    )
    
    slug: Optional[constr(pattern=r'^[a-z0-9-]+$', max_length=255)] = Field(
        default=None,
        description="URL-friendly slug (auto-generated if not provided)"
    )
    
    description: Optional[constr(max_length=5000, strip_whitespace=True)] = Field(
        default=None,
        description="Festival description (max 5000 characters)"
    )
    
    tagline: Optional[constr(max_length=255, strip_whitespace=True)] = Field(
        default=None,
        description="Festival tagline (max 255 characters)"
    )
    
    start_date: datetime = Field(
        description="Festival start date"
    )
    
    end_date: datetime = Field(
        description="Festival end date"
    )
    
    location: Optional[constr(max_length=255, strip_whitespace=True)] = Field(
        default=None,
        description="Festival location (city, country)"
    )
    
    venue: Optional[constr(max_length=255, strip_whitespace=True)] = Field(
        default=None,
        description="Festival venue"
    )
    
    categories: List[str] = Field(
        default=[],
        max_items=20,
        description="Festival categories (max 20)"
    )
    
    genres: List[str] = Field(
        default=[],
        max_items=20,
        description="Accepted genres (max 20)"
    )
    
    rules: Optional[constr(max_length=10000, strip_whitespace=True)] = Field(
        default=None,
        description="Festival rules and requirements (max 10000 characters)"
    )
    
    submission_start_date: Optional[datetime] = Field(
        default=None,
        description="Submission period start date"
    )
    
    submission_end_date: Optional[datetime] = Field(
        default=None,
        description="Submission deadline"
    )
    
    entry_fee: Optional[float] = Field(
        default=None,
        ge=0,
        le=10000,
        description="Entry fee (0-10000)"
    )
    
    website: Optional[HttpUrl] = Field(
        default=None,
        description="Festival website URL"
    )
    
    contact_email: Optional[EmailStr] = Field(
        default=None,
        description="Contact email address"
    )
    
    @field_validator('name', 'description', 'tagline', 'rules')
    @classmethod
    def sanitize_html(cls, v: Optional[str]) -> Optional[str]:
        """
        Sanitize HTML content to prevent XSS attacks.
        """
        if v is None:
            return v
        return bleach.clean(v, tags=[], strip=True)
    
    @field_validator('slug', mode='before')
    @classmethod
    def generate_slug(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """
        Auto-generate slug from name if not provided.
        """
        if v:
            return v
        
        if 'name' in info.data:
            name = info.data['name']
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower())
            slug = slug.strip('-')
            return slug[:255] if slug else None
        
        return v
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: datetime, info: ValidationInfo) -> datetime:
        """
        Ensure end_date is after start_date.
        """
        if 'start_date' in info.data:
            start_date = info.data['start_date']
            if v < start_date:
                raise ValueError('end_date must be after start_date')
        return v
    
    @field_validator('submission_end_date')
    @classmethod
    def validate_submission_end_date(cls, v: Optional[datetime], info: ValidationInfo) -> Optional[datetime]:
        """
        Ensure submission_end_date is before start_date.
        """
        if v is None:
            return v
        
        if 'start_date' in info.data:
            start_date = info.data['start_date']
            if v > start_date:
                raise ValueError('submission_end_date should be before festival start_date')
        
        return v
    
    @field_validator('categories', 'genres')
    @classmethod
    def clean_array_items(cls, v: List[str]) -> List[str]:
        """
        Clean and validate array items.
        """
        if not v:
            return []
        
        cleaned = []
        seen = set()
        
        for item in v:
            if isinstance(item, str):
                item = item.strip()[:100]
                if item and item.lower() not in seen:
                    cleaned.append(item)
                    seen.add(item.lower())
        
        return cleaned
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
        json_schema_extra={
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
                "submission_end_date": "2024-05-01T00:00:00Z",
                "entry_fee": 25.0,
                "website": "https://aicinemafest.com",
                "contact_email": "info@aicinemafest.com"
            }
        }
    )


class FestivalCreate(FestivalBase):
    """Schema for creating a new festival"""
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "name": "Turkish AI Film Festival",
                "description": "Celebrating Turkish AI filmmakers",
                "start_date": "2024-09-15T00:00:00Z",
                "end_date": "2024-09-20T00:00:00Z",
                "location": "Istanbul, Turkey",
                "categories": ["short", "feature"],
                "genres": ["sci-fi", "drama"]
            }
        }
    )


class FestivalUpdate(BaseModel):
    """Schema for updating an existing festival (partial updates allowed)"""
    
    name: Optional[constr(min_length=1, max_length=255, strip_whitespace=True)] = None
    description: Optional[constr(max_length=5000, strip_whitespace=True)] = None
    tagline: Optional[constr(max_length=255, strip_whitespace=True)] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[constr(max_length=255, strip_whitespace=True)] = None
    venue: Optional[constr(max_length=255, strip_whitespace=True)] = None
    categories: Optional[List[str]] = Field(default=None, max_items=20)
    genres: Optional[List[str]] = Field(default=None, max_items=20)
    rules: Optional[constr(max_length=10000, strip_whitespace=True)] = None
    submission_start_date: Optional[datetime] = None
    submission_end_date: Optional[datetime] = None
    entry_fee: Optional[float] = Field(default=None, ge=0, le=10000)
    website: Optional[HttpUrl] = None
    contact_email: Optional[EmailStr] = None
    
    @field_validator('name', 'description', 'tagline', 'rules')
    @classmethod
    def sanitize_html(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize HTML content"""
        if v is None:
            return v
        return bleach.clean(v, tags=[], strip=True)
    
    @field_validator('categories', 'genres')
    @classmethod
    def clean_array_items(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Clean array items"""
        if not v:
            return v
        
        cleaned = []
        seen = set()
        
        for item in v:
            if isinstance(item, str):
                item = item.strip()[:100]
                if item and item.lower() not in seen:
                    cleaned.append(item)
                    seen.add(item.lower())
        
        return cleaned if cleaned else None
    
    model_config = ConfigDict(
        extra='forbid',
        str_strip_whitespace=True
    )


class FestivalResponse(FestivalBase):
    """Schema for festival responses"""
    
    id: str = Field(description="Festival UUID")
    created_by: Optional[str] = Field(default=None, description="Creator user ID")
    status: constr(pattern=r'^(active|inactive|cancelled|completed)$') = Field(
        default='active',
        description="Festival status"
    )
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    # Stats
    total_submissions: Optional[int] = Field(default=0, ge=0)
    total_followers: Optional[int] = Field(default=0, ge=0)
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "AI Cinema International Festival 2024",
                "slug": "ai-cinema-2024",
                "status": "active",
                "start_date": "2024-06-01T00:00:00Z",
                "end_date": "2024-06-07T00:00:00Z",
                "created_by": "user-uuid",
                "created_at": "2024-01-20T10:00:00Z",
                "total_submissions": 42,
                "total_followers": 128
            }
        }
    )


class FestivalApplicationCreate(BaseModel):
    """Schema for creator festival application"""
    
    festival_data: FestivalCreate = Field(
        description="Festival details"
    )
    
    motivation: Optional[constr(max_length=2000, strip_whitespace=True)] = Field(
        default=None,
        description="Why you want to create this festival (max 2000 characters)"
    )
    
    @field_validator('motivation')
    @classmethod
    def sanitize_motivation(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize motivation text"""
        if v is None:
            return v
        return bleach.clean(v, tags=[], strip=True)
    
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            "example": {
                "festival_data": {
                    "name": "Turkish AI Film Festival",
                    "description": "Celebrating Turkish AI filmmakers",
                    "start_date": "2024-09-15T00:00:00Z",
                    "end_date": "2024-09-20T00:00:00Z",
                    "location": "Istanbul, Turkey"
                },
                "motivation": "I want to promote Turkish AI cinema internationally"
            }
        }
    )
