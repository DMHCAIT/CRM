-- ============================================================================
-- QUICK FIX: Clean up existing Supabase tables and start fresh
-- ============================================================================
-- Run this FIRST if you get "column does not exist" errors
-- This will delete all existing tables and data
-- ============================================================================

-- Drop all tables in reverse order (to handle foreign key constraints)
DROP TABLE IF EXISTS communication_history CASCADE;
DROP TABLE IF EXISTS activities CASCADE;
DROP TABLE IF EXISTS notes CASCADE;
DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS counselors CASCADE;
DROP TABLE IF EXISTS courses CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS hospitals CASCADE;

-- ============================================================================
-- DONE! Now run SUPABASE_SCHEMA.sql to create fresh tables
-- ============================================================================
