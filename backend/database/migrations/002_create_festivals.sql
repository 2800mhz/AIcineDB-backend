-- Migration: Festival System Tables
-- Description: Creates tables for film festival management system
-- Date: 2024-12-14

-- ============================================================================
-- FESTIVALS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS festivals (
    id UUID PRIMARY KEY,
    created_by UUID NOT NULL,
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    tagline VARCHAR(255),
    
    -- Dates
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    submission_start_date TIMESTAMP,
    submission_end_date TIMESTAMP,
    
    -- Location
    location VARCHAR(255),
    venue VARCHAR(255),
    
    -- Configuration
    categories TEXT[], -- ['short', 'feature', 'experimental']
    genres TEXT[], -- ['sci-fi', 'drama', 'documentary']
    rules TEXT,
    entry_fee DECIMAL(10,2),
    
    -- Contact
    website VARCHAR(500),
    contact_email VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'cancelled'
    is_creator_festival BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    
    -- Date constraints
    CONSTRAINT festivals_date_check CHECK (end_date > start_date),
    CONSTRAINT festivals_submission_date_check CHECK (
        submission_start_date IS NULL OR 
        submission_end_date IS NULL OR 
        submission_end_date > submission_start_date
    ),
    CONSTRAINT festivals_submission_before_start_check CHECK (
        submission_end_date IS NULL OR 
        start_date IS NULL OR 
        submission_end_date <= start_date
    )
);

CREATE INDEX IF NOT EXISTS idx_festivals_status ON festivals(status);
CREATE INDEX IF NOT EXISTS idx_festivals_created_by ON festivals(created_by);
CREATE INDEX IF NOT EXISTS idx_festivals_dates ON festivals(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_festivals_slug ON festivals(slug);


-- ============================================================================
-- FESTIVAL APPLICATIONS TABLE (Creator → Admin)
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_applications (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    
    -- Application data
    festival_data JSONB NOT NULL, -- Festival data from creator
    motivation TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    festival_id UUID REFERENCES festivals(id) ON DELETE SET NULL,
    
    -- Review
    admin_notes TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_festival_applications_user ON festival_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_festival_applications_status ON festival_applications(status);


-- ============================================================================
-- FESTIVAL SUBMISSIONS TABLE (Film → Festival)
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_submissions (
    id UUID PRIMARY KEY,
    festival_id UUID NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    film_id INTEGER NOT NULL REFERENCES films(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    
    -- Submission info
    category VARCHAR(100),
    notes TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'accepted', 'rejected', 'withdrawn'
    
    -- Review
    feedback TEXT,
    reviewed_at TIMESTAMP,
    reviewed_by UUID,
    
    -- Timestamps
    submitted_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(festival_id, film_id)
);

CREATE INDEX IF NOT EXISTS idx_festival_submissions_festival ON festival_submissions(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_submissions_film ON festival_submissions(film_id);
CREATE INDEX IF NOT EXISTS idx_festival_submissions_user ON festival_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_festival_submissions_status ON festival_submissions(status);


-- ============================================================================
-- FESTIVAL ORGANIZERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_organizers (
    festival_id UUID NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    role VARCHAR(50) DEFAULT 'organizer',
    
    added_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (festival_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_festival_organizers_user ON festival_organizers(user_id);


-- ============================================================================
-- FESTIVAL FOLLOWERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_followers (
    festival_id UUID NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    
    followed_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (festival_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_festival_followers_user ON festival_followers(user_id);


-- ============================================================================
-- FESTIVAL EVENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS festival_events (
    id UUID PRIMARY KEY,
    festival_id UUID NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    
    -- Event info
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_date TIMESTAMP NOT NULL,
    location VARCHAR(255),
    event_type VARCHAR(50) DEFAULT 'screening', -- 'screening', 'ceremony', 'workshop', 'panel'
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_festival_events_festival ON festival_events(festival_id);
CREATE INDEX IF NOT EXISTS idx_festival_events_date ON festival_events(event_date);


-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE festivals IS 'Film festivals created by admins or approved creators';
COMMENT ON TABLE festival_applications IS 'Creator applications to create festivals (pending admin approval)';
COMMENT ON TABLE festival_submissions IS 'Film submissions to festivals';
COMMENT ON TABLE festival_organizers IS 'Festival organizers who can manage the festival';
COMMENT ON TABLE festival_followers IS 'Users following festivals for updates';
COMMENT ON TABLE festival_events IS 'Events scheduled during festivals (screenings, ceremonies, etc.)';
