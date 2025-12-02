"""
AIcineDB Services Module
"""
from backend.services.supabase_sync import SupabaseSyncService
from backend.services.frame_uploader import FrameUploader  # ✅ EKLE

__all__ = ['SupabaseSyncService', 'FrameUploader']  # ✅ EKLE