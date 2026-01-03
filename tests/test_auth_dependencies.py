"""
Tests for authentication dependencies
"""
import pytest
from fastapi import HTTPException
from unittest.mock import Mock, patch, AsyncMock
from backend.auth.dependencies import (
    get_current_user,
    require_admin,
    verify_ownership,
)


class TestGetCurrentUser:
    """Tests for get_current_user dependency"""
    
    @pytest.mark.asyncio
    async def test_valid_token_returns_user_data(self):
        """Test that valid JWT returns user data"""
        # Mock credentials
        mock_credentials = Mock()
        mock_credentials.credentials = "valid_token"
        
        # Mock Supabase client response
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"role": "user"}
        
        mock_user_response = Mock()
        mock_user_response.user = mock_user
        
        # Patch get_supabase_client
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.return_value = mock_user_response
            mock_get_client.return_value = mock_client
            
            # Call the function
            result = await get_current_user(mock_credentials)
            
            # Assertions
            assert result["id"] == "user-123"
            assert result["email"] == "test@example.com"
            assert result["role"] == "user"
            assert result["is_admin"] is False
    
    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Test that invalid JWT raises 401"""
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"
        
        # Mock Supabase client to return None
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.return_value = None
            mock_get_client.return_value = mock_client
            
            # Should raise HTTPException with 401
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials)
            
            assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_admin_user_detected(self):
        """Test that admin users are properly detected"""
        mock_credentials = Mock()
        mock_credentials.credentials = "admin_token"
        
        # Mock admin user
        mock_user = Mock()
        mock_user.id = "admin-123"
        mock_user.email = "admin@example.com"
        mock_user.user_metadata = {"role": "admin"}
        
        mock_user_response = Mock()
        mock_user_response.user = mock_user
        
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            with patch('backend.auth.dependencies.get_admin_emails', return_value=["admin@example.com"]):
                mock_client = Mock()
                mock_client.auth.get_user.return_value = mock_user_response
                mock_get_client.return_value = mock_client
                
                result = await get_current_user(mock_credentials)
                
                assert result["is_admin"] is True


class TestRequireAdmin:
    """Tests for require_admin dependency"""
    
    @pytest.mark.asyncio
    async def test_admin_user_allowed(self):
        """Test that admin users pass the check"""
        mock_user = {
            "id": "admin-123",
            "email": "admin@example.com",
            "role": "admin",
            "is_admin": True
        }
        
        result = await require_admin(mock_user)
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_non_admin_user_raises_403(self):
        """Test that non-admin users are rejected"""
        mock_user = {
            "id": "user-123",
            "email": "user@example.com",
            "role": "user",
            "is_admin": False
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(mock_user)
        
        assert exc_info.value.status_code == 403


class TestVerifyOwnership:
    """Tests for verify_ownership factory"""
    
    @pytest.mark.asyncio
    async def test_owner_can_access_resource(self):
        """Test that resource owner can access their resource"""
        # Create dependency function
        dependency = verify_ownership("titles", "title_id", "uploaded_by")
        
        mock_user = {
            "id": "user-123",
            "email": "user@example.com",
            "is_admin": False
        }
        
        # Mock Supabase response
        mock_resource = {
            "id": "title-456",
            "title": "My Title",
            "uploaded_by": "user-123"
        }
        
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [mock_resource]
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await dependency("title-456", mock_user)
            
            assert result == mock_resource
    
    @pytest.mark.asyncio
    async def test_non_owner_raises_403(self):
        """Test that non-owners are rejected"""
        dependency = verify_ownership("titles", "title_id", "uploaded_by")
        
        mock_user = {
            "id": "user-123",
            "email": "user@example.com",
            "is_admin": False
        }
        
        # Resource owned by different user
        mock_resource = {
            "id": "title-456",
            "title": "Someone Else's Title",
            "uploaded_by": "other-user-789"
        }
        
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [mock_resource]
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await dependency("title-456", mock_user)
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_admin_can_bypass_ownership(self):
        """Test that admins can access any resource"""
        dependency = verify_ownership("titles", "title_id", "uploaded_by")
        
        mock_admin = {
            "id": "admin-123",
            "email": "admin@example.com",
            "is_admin": True
        }
        
        # Resource owned by different user
        mock_resource = {
            "id": "title-456",
            "title": "Someone's Title",
            "uploaded_by": "user-789"
        }
        
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [mock_resource]
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await dependency("title-456", mock_admin)
            
            assert result == mock_resource
    
    @pytest.mark.asyncio
    async def test_nonexistent_resource_raises_404(self):
        """Test that missing resources raise 404"""
        dependency = verify_ownership("titles", "title_id", "uploaded_by")
        
        mock_user = {
            "id": "user-123",
            "email": "user@example.com",
            "is_admin": False
        }
        
        with patch('backend.auth.dependencies.get_supabase_client') as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = []  # No resource found
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await dependency("nonexistent", mock_user)
            
            assert exc_info.value.status_code == 404
