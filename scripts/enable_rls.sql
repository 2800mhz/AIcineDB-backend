-- ============================================================================
-- Row Level Security (RLS) Setup for AIcineDB
-- ============================================================================
-- This script enables Row Level Security on all tables and creates
-- comprehensive RLS policies for user data protection.
--
-- RLS ensures that users can only access data they own or that is public,
-- while admins and moderators have broader access.
--
-- Execute this script after creating your Supabase tables.
-- ============================================================================

-- ============================================================================
-- Enable RLS on all tables
-- ============================================================================

ALTER TABLE IF EXISTS titles ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS user_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS list_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS title_frames ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS title_cast ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS festivals ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS festival_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS profiles ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM profiles
    WHERE id = user_id
    AND role IN ('admin', 'moderator')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to check if user is creator
CREATE OR REPLACE FUNCTION is_creator(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM profiles
    WHERE id = user_id
    AND role IN ('creator', 'admin', 'moderator')
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- Titles Table Policies
-- ============================================================================

-- Public read access for completed/approved titles
CREATE POLICY "titles_public_read"
  ON titles
  FOR SELECT
  USING (
    status IN ('completed', 'approved')
    OR
    uploaded_by = auth.uid()
    OR
    is_admin(auth.uid())
  );

-- Users can create titles (status forced to 'pending' by application)
CREATE POLICY "titles_authenticated_create"
  ON titles
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND uploaded_by = auth.uid()
    AND status IN ('draft', 'pending')
  );

-- Users can update their own titles or admins can update any
CREATE POLICY "titles_owner_or_admin_update"
  ON titles
  FOR UPDATE
  USING (
    uploaded_by = auth.uid()
    OR is_admin(auth.uid())
  )
  WITH CHECK (
    uploaded_by = auth.uid()
    OR is_admin(auth.uid())
  );

-- Users can delete their own titles or admins can delete any
CREATE POLICY "titles_owner_or_admin_delete"
  ON titles
  FOR DELETE
  USING (
    uploaded_by = auth.uid()
    OR is_admin(auth.uid())
  );

-- ============================================================================
-- Reviews Table Policies
-- ============================================================================

-- Public read access for approved reviews
CREATE POLICY "reviews_public_read"
  ON reviews
  FOR SELECT
  USING (
    status = 'approved'
    OR
    user_id = auth.uid()
    OR
    is_admin(auth.uid())
  );

-- Authenticated users can create reviews
CREATE POLICY "reviews_authenticated_create"
  ON reviews
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND user_id = auth.uid()
    AND status = 'pending'  -- Force pending status
  );

-- Users can update their own reviews
CREATE POLICY "reviews_owner_update"
  ON reviews
  FOR UPDATE
  USING (user_id = auth.uid() OR is_admin(auth.uid()))
  WITH CHECK (user_id = auth.uid() OR is_admin(auth.uid()));

-- Users can delete their own reviews
CREATE POLICY "reviews_owner_delete"
  ON reviews
  FOR DELETE
  USING (user_id = auth.uid() OR is_admin(auth.uid()));

-- ============================================================================
-- Ratings Table Policies
-- ============================================================================

-- Public read access for all ratings (anonymized)
CREATE POLICY "ratings_public_read"
  ON ratings
  FOR SELECT
  USING (true);

-- Authenticated users can create ratings
CREATE POLICY "ratings_authenticated_create"
  ON ratings
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND user_id = auth.uid()
  );

-- Users can update their own ratings
CREATE POLICY "ratings_owner_update"
  ON ratings
  FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Users can delete their own ratings
CREATE POLICY "ratings_owner_delete"
  ON ratings
  FOR DELETE
  USING (user_id = auth.uid());

-- ============================================================================
-- Watchlist Table Policies
-- ============================================================================

-- Users can only see their own watchlist
CREATE POLICY "watchlist_owner_read"
  ON watchlist
  FOR SELECT
  USING (user_id = auth.uid());

-- Users can add to their own watchlist
CREATE POLICY "watchlist_owner_create"
  ON watchlist
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND user_id = auth.uid()
  );

-- Users can remove from their own watchlist
CREATE POLICY "watchlist_owner_delete"
  ON watchlist
  FOR DELETE
  USING (user_id = auth.uid());

-- ============================================================================
-- User Lists Table Policies
-- ============================================================================

-- Public read for public lists, private read for owners
CREATE POLICY "user_lists_read"
  ON user_lists
  FOR SELECT
  USING (
    is_public = true
    OR
    user_id = auth.uid()
    OR
    is_admin(auth.uid())
  );

-- Users can create their own lists
CREATE POLICY "user_lists_create"
  ON user_lists
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND user_id = auth.uid()
  );

-- Users can update their own lists
CREATE POLICY "user_lists_update"
  ON user_lists
  FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Users can delete their own lists
CREATE POLICY "user_lists_delete"
  ON user_lists
  FOR DELETE
  USING (user_id = auth.uid());

-- ============================================================================
-- List Items Table Policies
-- ============================================================================

-- Read access follows list visibility
CREATE POLICY "list_items_read"
  ON list_items
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM user_lists
      WHERE user_lists.id = list_items.list_id
      AND (
        user_lists.is_public = true
        OR user_lists.user_id = auth.uid()
        OR is_admin(auth.uid())
      )
    )
  );

-- Users can add items to their own lists
CREATE POLICY "list_items_create"
  ON list_items
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM user_lists
      WHERE user_lists.id = list_items.list_id
      AND user_lists.user_id = auth.uid()
    )
  );

-- Users can remove items from their own lists
CREATE POLICY "list_items_delete"
  ON list_items
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM user_lists
      WHERE user_lists.id = list_items.list_id
      AND user_lists.user_id = auth.uid()
    )
  );

-- ============================================================================
-- Title Frames Table Policies
-- ============================================================================

-- Public read for frames of visible titles
CREATE POLICY "title_frames_public_read"
  ON title_frames
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM titles
      WHERE titles.id = title_frames.title_id
      AND (
        titles.status IN ('completed', 'approved')
        OR titles.uploaded_by = auth.uid()
        OR is_admin(auth.uid())
      )
    )
  );

-- Only title owners or admins can manage frames
CREATE POLICY "title_frames_owner_or_admin_manage"
  ON title_frames
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM titles
      WHERE titles.id = title_frames.title_id
      AND (
        titles.uploaded_by = auth.uid()
        OR is_admin(auth.uid())
      )
    )
  );

-- ============================================================================
-- Title Cast Table Policies
-- ============================================================================

-- Public read for cast of visible titles
CREATE POLICY "title_cast_public_read"
  ON title_cast
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM titles
      WHERE titles.id = title_cast.title_id
      AND (
        titles.status IN ('completed', 'approved')
        OR titles.uploaded_by = auth.uid()
        OR is_admin(auth.uid())
      )
    )
  );

-- Only title owners or admins can manage cast
CREATE POLICY "title_cast_owner_or_admin_manage"
  ON title_cast
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM titles
      WHERE titles.id = title_cast.title_id
      AND (
        titles.uploaded_by = auth.uid()
        OR is_admin(auth.uid())
      )
    )
  );

-- ============================================================================
-- Festivals Table Policies
-- ============================================================================

-- Public read for active festivals
CREATE POLICY "festivals_public_read"
  ON festivals
  FOR SELECT
  USING (
    status = 'active'
    OR
    created_by = auth.uid()
    OR
    is_admin(auth.uid())
  );

-- Creators can create festivals (pending approval)
CREATE POLICY "festivals_creator_create"
  ON festivals
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND created_by = auth.uid()
    AND is_creator(auth.uid())
    AND status = 'pending'
  );

-- Festival creators or admins can update
CREATE POLICY "festivals_owner_or_admin_update"
  ON festivals
  FOR UPDATE
  USING (
    created_by = auth.uid()
    OR is_admin(auth.uid())
  );

-- Only admins can delete festivals
CREATE POLICY "festivals_admin_delete"
  ON festivals
  FOR DELETE
  USING (is_admin(auth.uid()));

-- ============================================================================
-- Festival Submissions Table Policies
-- ============================================================================

-- Users see their own submissions, festival organizers see all for their festivals
CREATE POLICY "festival_submissions_read"
  ON festival_submissions
  FOR SELECT
  USING (
    user_id = auth.uid()
    OR
    EXISTS (
      SELECT 1 FROM festivals
      WHERE festivals.id = festival_submissions.festival_id
      AND festivals.created_by = auth.uid()
    )
    OR
    is_admin(auth.uid())
  );

-- Authenticated users can submit to festivals
CREATE POLICY "festival_submissions_create"
  ON festival_submissions
  FOR INSERT
  WITH CHECK (
    auth.uid() IS NOT NULL
    AND user_id = auth.uid()
    AND status = 'pending'
  );

-- Users can withdraw their own submissions
CREATE POLICY "festival_submissions_owner_update"
  ON festival_submissions
  FOR UPDATE
  USING (
    user_id = auth.uid()
    OR
    EXISTS (
      SELECT 1 FROM festivals
      WHERE festivals.id = festival_submissions.festival_id
      AND festivals.created_by = auth.uid()
    )
    OR
    is_admin(auth.uid())
  );

-- ============================================================================
-- Profiles Table Policies
-- ============================================================================

-- Public read for basic profile info
CREATE POLICY "profiles_public_read"
  ON profiles
  FOR SELECT
  USING (true);

-- Users can update their own profile
CREATE POLICY "profiles_owner_update"
  ON profiles
  FOR UPDATE
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid() AND role = OLD.role);  -- Prevent role escalation

-- Admins can update any profile including roles
CREATE POLICY "profiles_admin_update"
  ON profiles
  FOR UPDATE
  USING (is_admin(auth.uid()));

-- ============================================================================
-- Grant necessary permissions
-- ============================================================================

-- Grant execute on helper functions to authenticated users
GRANT EXECUTE ON FUNCTION is_admin(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_creator(UUID) TO authenticated;

-- ============================================================================
-- Verification Queries
-- ============================================================================
-- Run these to verify RLS is working correctly:

-- Check RLS is enabled
-- SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';

-- Check policies
-- SELECT tablename, policyname, cmd, qual FROM pg_policies WHERE schemaname = 'public';

-- ============================================================================
-- Notes
-- ============================================================================
-- 1. Backend service role key bypasses RLS - use for admin operations
-- 2. Frontend uses anon/authenticated keys - subject to RLS
-- 3. Test RLS policies thoroughly before production deployment
-- 4. Monitor logs for RLS policy violations
-- 5. Review and update policies as schema evolves
