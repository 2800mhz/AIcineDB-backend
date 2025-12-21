-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Films table
CREATE TABLE IF NOT EXISTS films (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500),
    url TEXT UNIQUE,
    duration FLOAT,
    uploader VARCHAR(255),
    upload_date DATE,
    view_count INTEGER,
    like_count INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Embeddings for similarity search
    visual_embedding vector(512),
    text_embedding vector(384),
    audio_embedding vector(128),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    analyzed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Analysis jobs table
CREATE TABLE IF NOT EXISTS analysis_jobs (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    user_id TEXT,  -- UUID of uploader from Supabase profiles table
    title_id TEXT,  -- UUID of title in Supabase (from frontend upload or backend creation)
    
    status VARCHAR(50) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    current_stage VARCHAR(255),
    
    priority INTEGER DEFAULT 5,
    
    error_message TEXT,
    celery_task_id VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Shots table
CREATE TABLE IF NOT EXISTS shots (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    shot_number INTEGER NOT NULL,
    
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    
    shot_type VARCHAR(50),
    lighting VARCHAR(50),
    brightness FLOAT,
    
    colors TEXT[],
    keyframe_path VARCHAR(500),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Characters table
CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    character_id VARCHAR(100) NOT NULL,
    
    name VARCHAR(255),
    role VARCHAR(100),
    
    screen_time FLOAT DEFAULT 0,
    total_appearances INTEGER DEFAULT 0,
    
    primary_emotion VARCHAR(50),
    confidence FLOAT,
    
    face_embedding vector(128),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Scenes table
CREATE TABLE IF NOT EXISTS scenes (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    scene_number INTEGER NOT NULL,
    
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    duration FLOAT NOT NULL,
    
    lighting VARCHAR(50),
    emotion VARCHAR(50),
    pacing VARCHAR(50),
    description TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Narratives table
CREATE TABLE IF NOT EXISTS narratives (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    
    logline TEXT,
    synopsis TEXT,
    
    themes JSONB DEFAULT '[]',
    genre TEXT[],
    tone TEXT[],
    
    conflict_type VARCHAR(100),
    emotional_arc FLOAT[],
    
    story_beats JSONB DEFAULT '[]',
    act_structure JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Transcripts table
CREATE TABLE IF NOT EXISTS transcripts (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    
    text TEXT,
    language VARCHAR(10),
    word_count INTEGER,
    
    segments JSONB DEFAULT '[]',
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audio features table
CREATE TABLE IF NOT EXISTS audio_features (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    
    tempo FLOAT,
    mood VARCHAR(50),
    intensity FLOAT,
    pacing VARCHAR(50),
    
    avg_energy FLOAT,
    spectral_brightness FLOAT,
    speech_ratio FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Film frames table (for extracted keyframes/photos)
CREATE TABLE IF NOT EXISTS film_frames (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    
    frame_url TEXT NOT NULL,
    frame_number INTEGER NOT NULL,
    timestamp FLOAT NOT NULL DEFAULT 0.0,
    ordering INTEGER DEFAULT 0,
    
    width INTEGER,
    height INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Film cast table (for actors and crew)
CREATE TABLE IF NOT EXISTS film_cast (
    id SERIAL PRIMARY KEY,
    film_id INTEGER REFERENCES films(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,
    role VARCHAR(255),
    type VARCHAR(50) DEFAULT 'actor',
    department VARCHAR(100),
    
    screen_time FLOAT,
    appearance_count INTEGER,
    ordering INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_films_url ON films(url);
CREATE INDEX idx_jobs_status ON analysis_jobs(status);
CREATE INDEX idx_jobs_created ON analysis_jobs(created_at DESC);
CREATE INDEX idx_jobs_title_id ON analysis_jobs(title_id);
CREATE INDEX idx_shots_film ON shots(film_id);
CREATE INDEX idx_characters_film ON characters(film_id);
CREATE INDEX idx_film_frames_film_id ON film_frames(film_id);
CREATE INDEX idx_film_frames_ordering ON film_frames(film_id, ordering);
CREATE INDEX idx_film_cast_film_id ON film_cast(film_id);
CREATE INDEX idx_film_cast_type ON film_cast(type);
CREATE INDEX idx_film_cast_ordering ON film_cast(film_id, ordering);