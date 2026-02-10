-- Initialize NewsJuice Database
-- This script creates all necessary tables for the chatter service

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, preference_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Audio history table
CREATE TABLE IF NOT EXISTS audio_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    question_text TEXT,
    podcast_text TEXT,
    audio_url TEXT,
    source_chunks JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Articles table (for news content)
CREATE TABLE IF NOT EXISTS articles (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) UNIQUE NOT NULL,
    author TEXT,
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP,
    published_at TIMESTAMP,
    vflag INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks vector table (for RAG retrieval)
CREATE TABLE IF NOT EXISTS chunks_vector (
    id SERIAL PRIMARY KEY,
    article_id VARCHAR(255) NOT NULL,
    author TEXT,
    title TEXT,
    summary TEXT,
    content TEXT,
    source_link TEXT,
    source_type VARCHAR(50),
    fetched_at TIMESTAMP,
    published_at TIMESTAMP,
    chunk TEXT,
    chunk_index INTEGER,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(article_id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_audio_history_user_id ON audio_history(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_vflag ON articles(vflag);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks_vector USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Display success message
DO $$
BEGIN
    RAISE NOTICE 'Database initialized successfully!';
END $$;
