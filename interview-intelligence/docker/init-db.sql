-- Enable pgvector extension for high-performance vector search
CREATE EXTENSION IF NOT EXISTS vector;

-- Ensure schema permissions
GRANT ALL ON SCHEMA public TO postgres;
