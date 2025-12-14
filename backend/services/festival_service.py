"""
Festival Service Layer
Handles all festival-related database operations
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class FestivalService:
    """Service for festival operations with Supabase"""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    # ========================================================================
    # FESTIVAL CRUD
    # ========================================================================
    
    async def create_festival(
        self, 
        festival_data: Dict[str, Any], 
        user_id: str, 
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new festival
        - Admins create approved festivals directly
        - Creators create pending festivals (requires approval)
        """
        festival_id = str(uuid.uuid4())
        
        data = {
            "id": festival_id,
            "created_by": user_id,
            "status": "approved" if is_admin else "pending",
            "is_creator_festival": not is_admin,
            **festival_data,
            "created_at": datetime.now().isoformat(),
        }
        
        response = self.supabase.table("festivals").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Festival created: {festival_id} by {user_id}")
            return response.data[0]
        else:
            logger.error(f"❌ Failed to create festival")
            raise Exception("Failed to create festival")
    
    async def get_festival(self, festival_id: str) -> Optional[Dict[str, Any]]:
        """Get festival by ID"""
        response = self.supabase.table("festivals").select("*").eq("id", festival_id).execute()
        
        if response.data:
            festival = response.data[0]
            
            # Get stats
            submissions_count = self.supabase.table("festival_submissions")\
                .select("id", count="exact")\
                .eq("festival_id", festival_id)\
                .execute()
            
            followers_count = self.supabase.table("festival_followers")\
                .select("id", count="exact")\
                .eq("festival_id", festival_id)\
                .execute()
            
            festival["total_submissions"] = submissions_count.count if submissions_count else 0
            festival["total_followers"] = followers_count.count if followers_count else 0
            
            return festival
        
        return None
    
    async def list_festivals(
        self, 
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List festivals with optional filters"""
        query = self.supabase.table("festivals").select("*")
        
        if status_filter == "active":
            query = query.eq("status", "approved")\
                        .lte("start_date", datetime.now().isoformat())\
                        .gte("end_date", datetime.now().isoformat())
        elif status_filter == "upcoming":
            query = query.eq("status", "approved")\
                        .gt("start_date", datetime.now().isoformat())
        elif status_filter == "past":
            query = query.eq("status", "approved")\
                        .lt("end_date", datetime.now().isoformat())
        elif status_filter:
            query = query.eq("status", status_filter)
        else:
            # Default: only show approved festivals
            query = query.eq("status", "approved")
        
        response = query.order("created_at", desc=True)\
                       .range(skip, skip + limit - 1)\
                       .execute()
        
        return response.data if response.data else []
    
    async def update_festival(
        self, 
        festival_id: str, 
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update festival"""
        update_data["updated_at"] = datetime.now().isoformat()
        
        response = self.supabase.table("festivals")\
            .update(update_data)\
            .eq("id", festival_id)\
            .execute()
        
        if response.data:
            logger.info(f"✅ Festival updated: {festival_id}")
            return response.data[0]
        
        return None
    
    async def delete_festival(self, festival_id: str) -> bool:
        """Delete festival (admin only)"""
        response = self.supabase.table("festivals")\
            .delete()\
            .eq("id", festival_id)\
            .execute()
        
        logger.info(f"✅ Festival deleted: {festival_id}")
        return True
    
    # ========================================================================
    # FESTIVAL APPLICATIONS
    # ========================================================================
    
    async def create_application(
        self,
        user_id: str,
        festival_data: Dict[str, Any],
        motivation: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create festival application (creator → admin)"""
        application_id = str(uuid.uuid4())
        
        data = {
            "id": application_id,
            "user_id": user_id,
            "festival_data": festival_data,
            "motivation": motivation,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        response = self.supabase.table("festival_applications").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Festival application created: {application_id}")
            return response.data[0]
        
        raise Exception("Failed to create application")
    
    async def list_applications(
        self,
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        """List festival applications"""
        query = self.supabase.table("festival_applications").select("*")
        
        if not is_admin and user_id:
            # Creator sees only their own applications
            query = query.eq("user_id", user_id)
        
        response = query.order("created_at", desc=True).execute()
        
        return response.data if response.data else []
    
    async def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        """Get application by ID"""
        response = self.supabase.table("festival_applications")\
            .select("*")\
            .eq("id", application_id)\
            .execute()
        
        if response.data:
            return response.data[0]
        
        return None
    
    async def approve_application(
        self,
        application_id: str,
        admin_id: str,
        admin_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve festival application"""
        # Get application
        application = await self.get_application(application_id)
        if not application:
            raise Exception("Application not found")
        
        # Create festival from application data
        festival = await self.create_festival(
            festival_data=application["festival_data"],
            user_id=application["user_id"],
            is_admin=False  # It's a creator festival
        )
        
        # Update application status
        update_data = {
            "status": "approved",
            "festival_id": festival["id"],
            "reviewed_at": datetime.now().isoformat(),
            "reviewed_by": admin_id,
            "admin_notes": admin_notes
        }
        
        response = self.supabase.table("festival_applications")\
            .update(update_data)\
            .eq("id", application_id)\
            .execute()
        
        logger.info(f"✅ Application approved: {application_id} → Festival: {festival['id']}")
        
        return response.data[0] if response.data else {}
    
    async def reject_application(
        self,
        application_id: str,
        admin_id: str,
        admin_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject festival application"""
        update_data = {
            "status": "rejected",
            "reviewed_at": datetime.now().isoformat(),
            "reviewed_by": admin_id,
            "admin_notes": admin_notes
        }
        
        response = self.supabase.table("festival_applications")\
            .update(update_data)\
            .eq("id", application_id)\
            .execute()
        
        logger.info(f"✅ Application rejected: {application_id}")
        
        return response.data[0] if response.data else {}
    
    # ========================================================================
    # FILM SUBMISSIONS
    # ========================================================================
    
    async def create_submission(
        self,
        festival_id: str,
        film_id: int,
        user_id: str,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit film to festival"""
        submission_id = str(uuid.uuid4())
        
        data = {
            "id": submission_id,
            "festival_id": festival_id,
            "film_id": film_id,
            "user_id": user_id,
            "category": category,
            "notes": notes,
            "status": "pending",
            "submitted_at": datetime.now().isoformat()
        }
        
        response = self.supabase.table("festival_submissions").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Film {film_id} submitted to festival {festival_id}")
            return response.data[0]
        
        raise Exception("Failed to create submission")
    
    async def list_submissions(
        self,
        festival_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List submissions for a festival"""
        response = self.supabase.table("festival_submissions")\
            .select("*")\
            .eq("festival_id", festival_id)\
            .order("submitted_at", desc=True)\
            .range(skip, skip + limit - 1)\
            .execute()
        
        return response.data if response.data else []
    
    async def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Get submission by ID"""
        response = self.supabase.table("festival_submissions")\
            .select("*")\
            .eq("id", submission_id)\
            .execute()
        
        if response.data:
            return response.data[0]
        
        return None
    
    async def update_submission(
        self,
        submission_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update submission"""
        response = self.supabase.table("festival_submissions")\
            .update(update_data)\
            .eq("id", submission_id)\
            .execute()
        
        if response.data:
            logger.info(f"✅ Submission updated: {submission_id}")
            return response.data[0]
        
        return None
    
    async def accept_submission(
        self,
        submission_id: str,
        reviewer_id: str,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Accept film submission"""
        update_data = {
            "status": "accepted",
            "reviewed_at": datetime.now().isoformat(),
            "reviewed_by": reviewer_id,
            "feedback": feedback
        }
        
        return await self.update_submission(submission_id, update_data)
    
    async def reject_submission(
        self,
        submission_id: str,
        reviewer_id: str,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject film submission"""
        update_data = {
            "status": "rejected",
            "reviewed_at": datetime.now().isoformat(),
            "reviewed_by": reviewer_id,
            "feedback": feedback
        }
        
        return await self.update_submission(submission_id, update_data)
    
    # ========================================================================
    # FESTIVAL MANAGEMENT
    # ========================================================================
    
    async def add_organizer(
        self,
        festival_id: str,
        user_id: str,
        role: str = "organizer"
    ) -> Dict[str, Any]:
        """Add organizer to festival"""
        data = {
            "festival_id": festival_id,
            "user_id": user_id,
            "role": role,
            "added_at": datetime.now().isoformat()
        }
        
        response = self.supabase.table("festival_organizers").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Organizer {user_id} added to festival {festival_id}")
            return response.data[0]
        
        raise Exception("Failed to add organizer")
    
    async def list_organizers(self, festival_id: str) -> List[Dict[str, Any]]:
        """List festival organizers"""
        response = self.supabase.table("festival_organizers")\
            .select("*")\
            .eq("festival_id", festival_id)\
            .execute()
        
        return response.data if response.data else []
    
    async def remove_organizer(self, festival_id: str, user_id: str) -> bool:
        """Remove organizer from festival"""
        response = self.supabase.table("festival_organizers")\
            .delete()\
            .eq("festival_id", festival_id)\
            .eq("user_id", user_id)\
            .execute()
        
        logger.info(f"✅ Organizer {user_id} removed from festival {festival_id}")
        return True
    
    async def follow_festival(self, festival_id: str, user_id: str) -> Dict[str, Any]:
        """Follow a festival"""
        data = {
            "festival_id": festival_id,
            "user_id": user_id,
            "followed_at": datetime.now().isoformat()
        }
        
        response = self.supabase.table("festival_followers").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ User {user_id} followed festival {festival_id}")
            return response.data[0]
        
        raise Exception("Failed to follow festival")
    
    async def unfollow_festival(self, festival_id: str, user_id: str) -> bool:
        """Unfollow a festival"""
        response = self.supabase.table("festival_followers")\
            .delete()\
            .eq("festival_id", festival_id)\
            .eq("user_id", user_id)\
            .execute()
        
        logger.info(f"✅ User {user_id} unfollowed festival {festival_id}")
        return True
    
    async def list_followers(
        self,
        festival_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List festival followers"""
        response = self.supabase.table("festival_followers")\
            .select("*")\
            .eq("festival_id", festival_id)\
            .order("followed_at", desc=True)\
            .range(skip, skip + limit - 1)\
            .execute()
        
        return response.data if response.data else []
    
    # ========================================================================
    # FESTIVAL EVENTS
    # ========================================================================
    
    async def create_event(
        self,
        festival_id: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create festival event"""
        event_id = str(uuid.uuid4())
        
        data = {
            "id": event_id,
            "festival_id": festival_id,
            **event_data,
            "created_at": datetime.now().isoformat()
        }
        
        response = self.supabase.table("festival_events").insert(data).execute()
        
        if response.data:
            logger.info(f"✅ Event created for festival {festival_id}")
            return response.data[0]
        
        raise Exception("Failed to create event")
    
    async def list_events(self, festival_id: str) -> List[Dict[str, Any]]:
        """List festival events"""
        response = self.supabase.table("festival_events")\
            .select("*")\
            .eq("festival_id", festival_id)\
            .order("event_date", desc=False)\
            .execute()
        
        return response.data if response.data else []
    
    async def update_event(
        self,
        event_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update festival event"""
        response = self.supabase.table("festival_events")\
            .update(update_data)\
            .eq("id", event_id)\
            .execute()
        
        if response.data:
            logger.info(f"✅ Event updated: {event_id}")
            return response.data[0]
        
        return None
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete festival event"""
        response = self.supabase.table("festival_events")\
            .delete()\
            .eq("id", event_id)\
            .execute()
        
        logger.info(f"✅ Event deleted: {event_id}")
        return True
    
    # ========================================================================
    # PERMISSIONS
    # ========================================================================
    
    async def check_festival_permission(
        self,
        festival_id: str,
        user_id: str,
        is_admin: bool = False
    ) -> bool:
        """
        Check if user has permission to manage festival
        Returns True if user is:
        - Admin
        - Festival creator
        - Festival organizer
        """
        if is_admin:
            return True
        
        # Check if user is festival creator
        festival = await self.get_festival(festival_id)
        if festival and festival.get("created_by") == user_id:
            return True
        
        # Check if user is organizer
        organizers = await self.list_organizers(festival_id)
        for org in organizers:
            if org.get("user_id") == user_id:
                return True
        
        return False


# Cached Supabase client
_supabase_client_cache = None


def get_supabase_client():
    """
    Get Supabase client instance (cached for performance)
    Uses singleton pattern from SupabaseSyncService
    """
    global _supabase_client_cache
    
    if _supabase_client_cache is None:
        from backend.services.supabase_sync import SupabaseSyncService
        sync_service = SupabaseSyncService()
        _supabase_client_cache = sync_service.supabase
    
    return _supabase_client_cache
