"""
Tests for hardened Pydantic schemas
"""
import pytest
from pydantic import ValidationError
from backend.schemas.titles import TitleCreate, TitleUpdate
from backend.schemas.festivals import FestivalCreate, FestivalUpdate
from datetime import datetime, timedelta


class TestTitleSchemas:
    """Tests for title schema validation"""
    
    def test_title_create_with_valid_data(self):
        """Test creating title with valid data"""
        data = {
            "title": "My AI Film",
            "description": "A great AI-generated film about consciousness.",
            "type": "short",
            "genres": ["Sci-Fi", "Drama"],
            "tags": ["AI", "Philosophy"]
        }
        
        title = TitleCreate(**data)
        
        assert title.title == "My AI Film"
        assert title.description == "A great AI-generated film about consciousness."
        assert title.type == "short"
        assert title.status == "pending"  # Default value
        assert len(title.genres) == 2
        assert len(title.tags) == 2
    
    def test_title_create_auto_generates_slug(self):
        """Test that slug is auto-generated from title"""
        data = {
            "title": "My Great AI Film!",
            "description": "Description here",
        }
        
        title = TitleCreate(**data)
        
        assert title.slug == "my-great-ai-film"
    
    def test_title_create_html_sanitization(self):
        """Test that HTML is sanitized from inputs"""
        data = {
            "title": "Title <script>alert('xss')</script>",
            "description": "<b>Bold</b> and <script>dangerous</script>",
            "logline": "<a href='evil'>Click</a>",
        }
        
        title = TitleCreate(**data)
        
        # HTML should be stripped
        assert "<script>" not in title.title
        assert "<b>" not in title.description
        assert "<a " not in title.logline
        # Text should remain
        assert "Title" in title.title
        assert "Bold" in title.description
    
    def test_title_create_rejects_extra_fields(self):
        """Test that extra fields are rejected"""
        data = {
            "title": "My Film",
            "description": "Description",
            "extra_field": "Should be rejected"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(**data)
        
        errors = exc_info.value.errors()
        assert any("extra_forbidden" in str(error) for error in errors)
    
    def test_title_create_validates_type(self):
        """Test that type field only accepts valid values"""
        data = {
            "title": "My Film",
            "description": "Description",
            "type": "invalid_type"
        }
        
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(**data)
        
        assert "type" in str(exc_info.value)
    
    def test_title_create_validates_status(self):
        """Test that status is restricted to draft/pending for users"""
        # Valid status
        data1 = {
            "title": "My Film",
            "description": "Description",
            "status": "pending"
        }
        title1 = TitleCreate(**data1)
        assert title1.status == "pending"
        
        # Another valid status
        data2 = {
            "title": "My Film",
            "description": "Description",
            "status": "draft"
        }
        title2 = TitleCreate(**data2)
        assert title2.status == "draft"
        
        # Invalid status should be rejected
        data3 = {
            "title": "My Film",
            "description": "Description",
            "status": "completed"  # Not allowed for user creation
        }
        with pytest.raises(ValidationError):
            TitleCreate(**data3)
    
    def test_title_create_enforces_length_limits(self):
        """Test that string length limits are enforced"""
        # Title too long (>200 chars)
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(
                title="a" * 201,
                description="Description"
            )
        assert "title" in str(exc_info.value)
        
        # Description too long (>5000 chars)
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(
                title="Title",
                description="a" * 5001
            )
        assert "description" in str(exc_info.value)
    
    def test_title_create_enforces_array_limits(self):
        """Test that array size limits are enforced"""
        # Too many genres (>10)
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(
                title="Title",
                description="Description",
                genres=["genre" + str(i) for i in range(11)]
            )
        assert "genres" in str(exc_info.value)
        
        # Too many tags (>20)
        with pytest.raises(ValidationError) as exc_info:
            TitleCreate(
                title="Title",
                description="Description",
                tags=["tag" + str(i) for i in range(21)]
            )
        assert "tags" in str(exc_info.value)
    
    def test_title_create_cleans_arrays(self):
        """Test that arrays are cleaned (duplicates removed, whitespace stripped)"""
        data = {
            "title": "Title",
            "description": "Description",
            "genres": ["  Sci-Fi  ", "Drama", "sci-fi", "  Drama  "],
            "tags": ["AI", "  AI  ", "Philosophy", ""]
        }
        
        title = TitleCreate(**data)
        
        # Duplicates should be removed (case-insensitive)
        assert len(title.genres) == 2
        assert len(title.tags) == 2
        
        # Whitespace should be stripped
        assert all(not g.startswith(" ") and not g.endswith(" ") for g in title.genres)
        assert all(not t.startswith(" ") and not t.endswith(" ") for t in title.tags)
        
        # Empty strings should be removed
        assert "" not in title.tags
    
    def test_title_create_validates_year(self):
        """Test that year validation works"""
        # Valid year
        data1 = {
            "title": "Title",
            "description": "Description",
            "year": 2024
        }
        title1 = TitleCreate(**data1)
        assert title1.year == 2024
        
        # Year too old
        with pytest.raises(ValidationError):
            TitleCreate(
                title="Title",
                description="Description",
                year=1800  # Before first film (1888)
            )
        
        # Year too far in future
        with pytest.raises(ValidationError):
            TitleCreate(
                title="Title",
                description="Description",
                year=2101  # After limit (2100)
            )
    
    def test_title_update_allows_partial(self):
        """Test that TitleUpdate allows partial updates"""
        # Should work with just one field
        update = TitleUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.description is None
        
        # Should work with multiple fields
        update2 = TitleUpdate(
            title="New Title",
            description="New Description"
        )
        assert update2.title == "New Title"
        assert update2.description == "New Description"


class TestFestivalSchemas:
    """Tests for festival schema validation"""
    
    def test_festival_create_with_valid_data(self):
        """Test creating festival with valid data"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        data = {
            "name": "AI Film Festival 2024",
            "description": "A festival for AI-generated films",
            "start_date": start,
            "end_date": end,
            "location": "Istanbul, Turkey",
            "categories": ["short", "feature"]
        }
        
        festival = FestivalCreate(**data)
        
        assert festival.name == "AI Film Festival 2024"
        assert festival.start_date == start
        assert festival.end_date == end
    
    def test_festival_create_auto_generates_slug(self):
        """Test that slug is auto-generated from name"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        data = {
            "name": "AI Film Festival 2024!",
            "description": "Description",
            "start_date": start,
            "end_date": end
        }
        
        festival = FestivalCreate(**data)
        
        assert festival.slug == "ai-film-festival-2024"
    
    def test_festival_create_validates_dates(self):
        """Test that date validation works"""
        start = datetime.now() + timedelta(days=30)
        wrong_end = datetime.now() + timedelta(days=20)  # Before start
        
        # End date before start date should fail
        with pytest.raises(ValidationError) as exc_info:
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=wrong_end
            )
        
        assert "end_date" in str(exc_info.value)
    
    def test_festival_create_validates_submission_deadline(self):
        """Test that submission deadline is validated"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        late_deadline = datetime.now() + timedelta(days=35)  # After start
        
        # Submission deadline after start should fail
        with pytest.raises(ValidationError) as exc_info:
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=end,
                submission_end_date=late_deadline
            )
        
        assert "submission_end_date" in str(exc_info.value)
    
    def test_festival_create_sanitizes_html(self):
        """Test that HTML is sanitized"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        data = {
            "name": "Festival <script>alert('xss')</script>",
            "description": "<b>Bold</b> description",
            "tagline": "<a href='evil'>Click</a>",
            "start_date": start,
            "end_date": end
        }
        
        festival = FestivalCreate(**data)
        
        assert "<script>" not in festival.name
        assert "<b>" not in festival.description
        assert "<a " not in festival.tagline
    
    def test_festival_create_validates_entry_fee(self):
        """Test entry fee validation"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        # Negative fee should fail
        with pytest.raises(ValidationError):
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=end,
                entry_fee=-10
            )
        
        # Very large fee should fail (>10000)
        with pytest.raises(ValidationError):
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=end,
                entry_fee=10001
            )
    
    def test_festival_create_validates_email(self):
        """Test that email validation works"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        # Valid email
        data1 = {
            "name": "Festival",
            "description": "Description",
            "start_date": start,
            "end_date": end,
            "contact_email": "valid@example.com"
        }
        festival1 = FestivalCreate(**data1)
        assert festival1.contact_email == "valid@example.com"
        
        # Invalid email
        with pytest.raises(ValidationError):
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=end,
                contact_email="not-an-email"
            )
    
    def test_festival_create_validates_url(self):
        """Test that URL validation works"""
        start = datetime.now() + timedelta(days=30)
        end = datetime.now() + timedelta(days=37)
        
        # Valid URL
        data1 = {
            "name": "Festival",
            "description": "Description",
            "start_date": start,
            "end_date": end,
            "website": "https://festival.com"
        }
        festival1 = FestivalCreate(**data1)
        assert str(festival1.website) == "https://festival.com/"
        
        # Invalid URL
        with pytest.raises(ValidationError):
            FestivalCreate(
                name="Festival",
                description="Description",
                start_date=start,
                end_date=end,
                website="not-a-url"
            )
