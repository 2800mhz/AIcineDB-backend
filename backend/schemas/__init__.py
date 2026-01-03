"""
Hardened Pydantic Schemas for AIcineDB Backend
Includes comprehensive validation, sanitization, and security controls
"""
from backend.schemas.titles import (
    TitleBase,
    TitleCreate,
    TitleUpdate,
    TitleResponse,
)

from backend.schemas.festivals import (
    FestivalBase,
    FestivalCreate,
    FestivalUpdate,
    FestivalResponse,
    FestivalApplicationCreate,
)

__all__ = [
    # Titles
    "TitleBase",
    "TitleCreate",
    "TitleUpdate",
    "TitleResponse",
    # Festivals
    "FestivalBase",
    "FestivalCreate",
    "FestivalUpdate",
    "FestivalResponse",
    "FestivalApplicationCreate",
]
