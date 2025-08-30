-- Add pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to existing table
ALTER TABLE service_search_view 
ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- Create vector similarity index for fast searches
CREATE INDEX IF NOT EXISTS idx_embedding_cosine ON service_search_view 
USING hnsw (embedding vector_cosine_ops);