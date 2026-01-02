"""
Festival API Endpoints
Handles all festival-related HTTP endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging

from backend.models.schemas import (
    FestivalCreate,
    FestivalUpdate,
    FestivalResponse,
    FestivalApplicationCreate,
    FestivalApplicationResponse,
    FestivalSubmissionCreate,
    FestivalSubmissionResponse,
    FestivalOrganizerCreate,
    FestivalEventCreate,
    FestivalFilmScrapeRequest,
    FestivalFilmScrapeResponse,
    ScrapedFilmData,
)
from backend.utils.auth import verify_admin, verify_creator, get_current_user
from backend.services.festival_service import FestivalService, get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_festival_service() -> FestivalService:
    """Get festival service instance"""
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(
            status_code=503,
            detail="Festival service unavailable. Supabase not configured."
        )
    return FestivalService(supabase)


# ============================================================================
# FESTIVAL CRUD
# ============================================================================

@router.post("/festivals", status_code=201)
async def create_festival(
    festival: FestivalCreate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    Create a new festival
    - Admin creates approved festival directly
    - Creator creates pending festival (requires admin approval)
    """
    try:
        is_admin = current_user.get("is_admin", False)
        
        result = await festival_service.create_festival(
            festival_data=festival.dict(),
            user_id=current_user["id"],
            is_admin=is_admin
        )
        
        if is_admin:
            logger.info(f"✅ Admin created festival: {result['id']}")
            return {
                "message": "Festival created successfully",
                "festival": result
            }
        else:
            logger.info(f"✅ Creator submitted festival for approval: {result['id']}")
            return {
                "message": "Festival submitted for admin approval",
                "festival": result,
                "note": "Your festival will be visible once approved by an administrator"
            }
    
    except Exception as e:
        logger.error(f"❌ Failed to create festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals")
async def list_festivals(
    filter: Optional[str] = Query(None, regex="^(active|upcoming|past|approved|pending)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    List festivals
    Filters:
    - active: Currently running festivals
    - upcoming: Future festivals
    - past: Finished festivals
    - approved: All approved festivals (default)
    - pending: Pending festivals (admin only)
    """
    try:
        festivals = await festival_service.list_festivals(
            status_filter=filter,
            skip=skip,
            limit=limit
        )
        
        return {
            "festivals": festivals,
            "count": len(festivals),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list festivals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/{festival_id}")
async def get_festival(
    festival_id: str,
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Get festival details"""
    try:
        festival = await festival_service.get_festival(festival_id)
        
        if not festival:
            raise HTTPException(status_code=404, detail="Festival not found")
        
        return festival
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/festivals/{festival_id}")
async def update_festival(
    festival_id: str,
    festival: FestivalUpdate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    Update festival
    Only accessible by festival owner, organizers, or admin
    """
    try:
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this festival"
            )
        
        # Update festival (only include non-None fields)
        update_data = {k: v for k, v in festival.dict().items() if v is not None}
        
        result = await festival_service.update_festival(festival_id, update_data)
        
        if not result:
            raise HTTPException(status_code=404, detail="Festival not found")
        
        logger.info(f"✅ Festival updated: {festival_id}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/festivals/{festival_id}")
async def delete_festival(
    festival_id: str,
    current_user: dict = Depends(verify_admin),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    Delete festival (admin only)
    """
    try:
        await festival_service.delete_festival(festival_id)
        
        logger.info(f"✅ Festival deleted: {festival_id}")
        return {"message": "Festival deleted successfully"}
    
    except Exception as e:
        logger.error(f"❌ Failed to delete festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL APPLICATIONS (Creator → Admin)
# ============================================================================

@router.get("/festivals/applications")
async def list_applications(
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    List festival applications
    - Admin sees all applications
    - Creator sees only their own applications
    """
    try:
        is_admin = current_user.get("is_admin", False)
        
        applications = await festival_service.list_applications(
            user_id=current_user["id"],
            is_admin=is_admin
        )
        
        return {
            "applications": applications,
            "count": len(applications)
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list applications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/applications/{application_id}")
async def get_application(
    application_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Get application details"""
    try:
        application = await festival_service.get_application(application_id)
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Check permissions
        is_admin = current_user.get("is_admin", False)
        is_owner = application.get("user_id") == current_user["id"]
        
        if not is_admin and not is_owner:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this application"
            )
        
        return application
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/applications/{application_id}/approve")
async def approve_application(
    application_id: str,
    admin_notes: Optional[str] = None,
    current_user: dict = Depends(verify_admin),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Approve festival application (admin only)"""
    try:
        result = await festival_service.approve_application(
            application_id=application_id,
            admin_id=current_user["id"],
            admin_notes=admin_notes
        )
        
        logger.info(f"✅ Application approved: {application_id}")
        return {
            "message": "Application approved and festival created",
            "application": result
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to approve application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/applications/{application_id}/reject")
async def reject_application(
    application_id: str,
    admin_notes: Optional[str] = None,
    current_user: dict = Depends(verify_admin),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Reject festival application (admin only)"""
    try:
        result = await festival_service.reject_application(
            application_id=application_id,
            admin_id=current_user["id"],
            admin_notes=admin_notes
        )
        
        logger.info(f"✅ Application rejected: {application_id}")
        return {
            "message": "Application rejected",
            "application": result
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to reject application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FILM SUBMISSIONS
# ============================================================================

@router.post("/festivals/{festival_id}/submissions", status_code=201)
async def submit_film(
    festival_id: str,
    submission: FestivalSubmissionCreate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Submit a film to a festival"""
    try:
        # Check if festival exists and is accepting submissions
        festival = await festival_service.get_festival(festival_id)
        if not festival:
            raise HTTPException(status_code=404, detail="Festival not found")
        
        if festival.get("status") != "approved":
            raise HTTPException(
                status_code=400,
                detail="Festival is not accepting submissions"
            )
        
        result = await festival_service.create_submission(
            festival_id=festival_id,
            film_id=submission.film_id,
            user_id=current_user["id"],
            category=submission.category,
            notes=submission.notes
        )
        
        logger.info(f"✅ Film {submission.film_id} submitted to festival {festival_id}")
        return {
            "message": "Film submitted successfully",
            "submission": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to submit film: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/{festival_id}/submissions")
async def list_submissions(
    festival_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    List submissions for a festival
    Accessible by festival organizers, admins, and submitters
    """
    try:
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view submissions"
            )
        
        submissions = await festival_service.list_submissions(
            festival_id=festival_id,
            skip=skip,
            limit=limit
        )
        
        return {
            "submissions": submissions,
            "count": len(submissions),
            "skip": skip,
            "limit": limit
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list submissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Get submission details"""
    try:
        submission = await festival_service.get_submission(submission_id)
        
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check permissions
        is_admin = current_user.get("is_admin", False)
        is_submitter = submission.get("user_id") == current_user["id"]
        has_festival_permission = await festival_service.check_festival_permission(
            festival_id=submission["festival_id"],
            user_id=current_user["id"],
            is_admin=is_admin
        )
        
        if not (is_admin or is_submitter or has_festival_permission):
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to view this submission"
            )
        
        return submission
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/festivals/submissions/{submission_id}")
async def update_submission_status(
    submission_id: str,
    status: str,
    feedback: Optional[str] = None,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Update submission status (festival organizer/admin only)"""
    try:
        submission = await festival_service.get_submission(submission_id)
        
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=submission["festival_id"],
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this submission"
            )
        
        update_data = {"status": status}
        if feedback:
            update_data["feedback"] = feedback
        
        result = await festival_service.update_submission(submission_id, update_data)
        
        logger.info(f"✅ Submission {submission_id} status updated to {status}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/submissions/{submission_id}/accept")
async def accept_submission(
    submission_id: str,
    feedback: Optional[str] = None,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Accept film submission"""
    try:
        submission = await festival_service.get_submission(submission_id)
        
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=submission["festival_id"],
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to accept submissions"
            )
        
        result = await festival_service.accept_submission(
            submission_id=submission_id,
            reviewer_id=current_user["id"],
            feedback=feedback
        )
        
        logger.info(f"✅ Submission accepted: {submission_id}")
        return {
            "message": "Submission accepted",
            "submission": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to accept submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    feedback: Optional[str] = None,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Reject film submission"""
    try:
        submission = await festival_service.get_submission(submission_id)
        
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=submission["festival_id"],
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to reject submissions"
            )
        
        result = await festival_service.reject_submission(
            submission_id=submission_id,
            reviewer_id=current_user["id"],
            feedback=feedback
        )
        
        logger.info(f"✅ Submission rejected: {submission_id}")
        return {
            "message": "Submission rejected",
            "submission": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reject submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL MANAGEMENT
# ============================================================================

@router.post("/festivals/{festival_id}/organizers", status_code=201)
async def add_organizer(
    festival_id: str,
    organizer: FestivalOrganizerCreate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Add organizer to festival"""
    try:
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to add organizers"
            )
        
        result = await festival_service.add_organizer(
            festival_id=festival_id,
            user_id=organizer.user_id,
            role=organizer.role
        )
        
        logger.info(f"✅ Organizer added to festival {festival_id}")
        return {
            "message": "Organizer added successfully",
            "organizer": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to add organizer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/{festival_id}/organizers")
async def list_organizers(
    festival_id: str,
    festival_service: FestivalService = Depends(get_festival_service)
):
    """List festival organizers"""
    try:
        organizers = await festival_service.list_organizers(festival_id)
        
        return {
            "organizers": organizers,
            "count": len(organizers)
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list organizers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/festivals/{festival_id}/organizers/{user_id}")
async def remove_organizer(
    festival_id: str,
    user_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Remove organizer from festival"""
    try:
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to remove organizers"
            )
        
        await festival_service.remove_organizer(festival_id, user_id)
        
        logger.info(f"✅ Organizer removed from festival {festival_id}")
        return {"message": "Organizer removed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to remove organizer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/festivals/{festival_id}/follow")
async def follow_festival(
    festival_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Follow a festival"""
    try:
        result = await festival_service.follow_festival(
            festival_id=festival_id,
            user_id=current_user["id"]
        )
        
        logger.info(f"✅ User {current_user['id']} followed festival {festival_id}")
        return {
            "message": "Festival followed successfully",
            "follow": result
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to follow festival: {e}")
        # Check if already following
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail="Already following this festival")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/festivals/{festival_id}/follow")
async def unfollow_festival(
    festival_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Unfollow a festival"""
    try:
        await festival_service.unfollow_festival(
            festival_id=festival_id,
            user_id=current_user["id"]
        )
        
        logger.info(f"✅ User {current_user['id']} unfollowed festival {festival_id}")
        return {"message": "Festival unfollowed successfully"}
    
    except Exception as e:
        logger.error(f"❌ Failed to unfollow festival: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/{festival_id}/followers")
async def list_followers(
    festival_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """List festival followers"""
    try:
        followers = await festival_service.list_followers(
            festival_id=festival_id,
            skip=skip,
            limit=limit
        )
        
        return {
            "followers": followers,
            "count": len(followers),
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list followers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL EVENTS
# ============================================================================

@router.post("/festivals/{festival_id}/events", status_code=201)
async def create_event(
    festival_id: str,
    event: FestivalEventCreate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Create festival event"""
    try:
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to create events"
            )
        
        result = await festival_service.create_event(
            festival_id=festival_id,
            event_data=event.dict()
        )
        
        logger.info(f"✅ Event created for festival {festival_id}")
        return {
            "message": "Event created successfully",
            "event": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals/{festival_id}/events")
async def list_events(
    festival_id: str,
    festival_service: FestivalService = Depends(get_festival_service)
):
    """List festival events"""
    try:
        events = await festival_service.list_events(festival_id)
        
        return {
            "events": events,
            "count": len(events)
        }
    
    except Exception as e:
        logger.error(f"❌ Failed to list events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/festivals/events/{event_id}")
async def update_event(
    event_id: str,
    event: FestivalEventCreate,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Update festival event"""
    try:
        # Get event to find its festival
        event_query = festival_service.supabase.table("festival_events")\
            .select("festival_id")\
            .eq("id", event_id)\
            .execute()
        
        if not event_query.data:
            raise HTTPException(status_code=404, detail="Event not found")
        
        festival_id = event_query.data[0]["festival_id"]
        
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to update this event"
            )
        
        result = await festival_service.update_event(
            event_id=event_id,
            update_data=event.dict()
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Event not found")
        
        logger.info(f"✅ Event updated: {event_id}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to update event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/festivals/events/{event_id}")
async def delete_event(
    event_id: str,
    current_user: dict = Depends(verify_creator),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """Delete festival event"""
    try:
        # Get event to find its festival
        event_query = festival_service.supabase.table("festival_events")\
            .select("festival_id")\
            .eq("id", event_id)\
            .execute()
        
        if not event_query.data:
            raise HTTPException(status_code=404, detail="Event not found")
        
        festival_id = event_query.data[0]["festival_id"]
        
        # Check permissions
        has_permission = await festival_service.check_festival_permission(
            festival_id=festival_id,
            user_id=current_user["id"],
            is_admin=current_user.get("is_admin", False)
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this event"
            )
        
        await festival_service.delete_event(event_id)
        
        logger.info(f"✅ Event deleted: {event_id}")
        return {"message": "Event deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FESTIVAL FILM SCRAPER
# ============================================================================

@router.post("/festivals/scrape-films")
async def scrape_festival_films(
    request: FestivalFilmScrapeRequest,
    current_user: dict = Depends(verify_admin),
    festival_service: FestivalService = Depends(get_festival_service)
):
    """
    Scrape films from a festival website (admin only)
    
    This endpoint:
    1. Scrapes the festival website for films with YouTube embeds
    2. Creates title records in the database for each film
    3. Links films to the festival via festival_submissions
    4. Returns statistics about the import
    
    Request:
    {
        "festival_url": "https://aiff.runwayml.com/2024",
        "festival_name": "Runway AI Film Festival 2024",  // optional
        "festival_id": "uuid"  // optional, to link to existing festival
    }
    
    Response:
    {
        "films_found": 15,
        "films_imported": 12,
        "films_skipped": 3,  // already exists
        "films": [...]
    }
    """
    from backend.services.festival_film_scraper import FestivalFilmScraper
    from backend.models.schemas import ScrapedFilmData, FestivalFilmScrapeResponse
    import uuid
    from datetime import datetime
    
    try:
        logger.info(f"🎬 Starting festival film scrape: {request.festival_url}")
        logger.info(f"   Requested by admin: {current_user['id']}")
        
        # Initialize scraper
        scraper = FestivalFilmScraper()
        
        # Scrape films from festival website
        scraped_films = await scraper.scrape_festival_films(str(request.festival_url))
        
        if not scraped_films:
            logger.warning(f"⚠️  No films found at {request.festival_url}")
            return FestivalFilmScrapeResponse(
                films_found=0,
                films_imported=0,
                films_skipped=0,
                films=[],
                errors=["No films found on the festival page"]
            )
        
        logger.info(f"✅ Scraped {len(scraped_films)} films from {request.festival_url}")
        
        # Import films to database
        films_imported = 0
        films_skipped = 0
        imported_films = []
        errors = []
        
        for film_data in scraped_films:
            try:
                # Check if film already exists by YouTube URL
                existing_title = festival_service.supabase.table("titles")\
                    .select("id, title, trailer_youtube_url")\
                    .eq("trailer_youtube_url", film_data["youtube_url"])\
                    .execute()
                
                if existing_title.data:
                    # Film already exists
                    logger.info(f"⏭️  Skipping existing film: {film_data['title']}")
                    films_skipped += 1
                    title_id = existing_title.data[0]["id"]
                else:
                    # Create new title record
                    title_id = str(uuid.uuid4())
                    
                    title_record = {
                        "id": title_id,
                        "title": film_data["title"],
                        "trailer_youtube_url": film_data["youtube_url"],
                        "description": film_data.get("description"),
                        "director": film_data.get("director"),
                        "festival_source_url": film_data["festival_source_url"],
                        "is_festival_film": True,
                        "uploaded_by": current_user["id"],
                        "status": "approved",  # Auto-approve festival films
                        "created_at": datetime.now().isoformat(),
                    }
                    
                    result = festival_service.supabase.table("titles")\
                        .insert(title_record)\
                        .execute()
                    
                    if result.data:
                        logger.info(f"✅ Created title: {film_data['title']} (ID: {title_id})")
                        films_imported += 1
                    else:
                        logger.error(f"❌ Failed to create title: {film_data['title']}")
                        errors.append(f"Failed to create title: {film_data['title']}")
                        continue
                
                # Link film to festival if festival_id provided
                if request.festival_id:
                    try:
                        # Import get_db for PostgreSQL access
                        from backend.database.connection import get_db
                        
                        # Check if submission already exists in PostgreSQL
                        async with get_db() as db:
                            existing = await db.fetch_one(
                                query="""
                                SELECT id FROM festival_submissions 
                                WHERE festival_id = :festival_id AND title_id = :title_id
                                """,
                                values={
                                    "festival_id": request.festival_id,
                                    "title_id": title_id
                                }
                            )
                            
                            if not existing:
                                submission_id = str(uuid.uuid4())
                                await db.execute(
                                    query="""
                                    INSERT INTO festival_submissions (
                                        id, festival_id, title_id, user_id, 
                                        category, status, is_winner, submitted_at
                                    ) VALUES (
                                        :id, :festival_id, :title_id, :user_id,
                                        :category, :status, :is_winner, NOW()
                                    )
                                    """,
                                    values={
                                        "id": submission_id,
                                        "festival_id": request.festival_id,
                                        "title_id": title_id,
                                        "user_id": current_user["id"],
                                        "category": film_data.get("category"),
                                        "status": "accepted",
                                        "is_winner": True if film_data.get("category") else False
                                    }
                                )
                                
                                logger.info(f"✅ Linked film to festival: {film_data['title']} → {request.festival_id}")
                    except Exception as e:
                        logger.warning(f"⚠️  Failed to link film to festival: {e}")
                        errors.append(f"Failed to link {film_data['title']} to festival: {str(e)}")
                
                # Add to imported films list
                imported_films.append(ScrapedFilmData(**film_data))
                
            except Exception as e:
                logger.error(f"❌ Failed to import film {film_data.get('title', 'Unknown')}: {e}")
                errors.append(f"Failed to import {film_data.get('title', 'Unknown')}: {str(e)}")
                continue
        
        logger.info(f"🎉 Import complete: {films_imported} imported, {films_skipped} skipped")
        
        return FestivalFilmScrapeResponse(
            films_found=len(scraped_films),
            films_imported=films_imported,
            films_skipped=films_skipped,
            films=imported_films,
            errors=errors
        )
    
    except Exception as e:
        logger.error(f"❌ Festival film scraping failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape festival films: {str(e)}"
        )
