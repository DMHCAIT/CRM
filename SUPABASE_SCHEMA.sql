-- ============================================================================
-- MEDICAL EDUCATION CRM - SUPABASE DATABASE SCHEMA
-- ============================================================================
-- Run this SQL in Supabase Dashboard > SQL Editor
-- Complete database setup for production deployment
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users table (counselors, admins, team members)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    password VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Super Admin', 'Hospital Admin', 'Manager', 'Team Leader', 'Counselor')),
    hospital_id INTEGER,
    reports_to VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hospitals table (partner hospitals/institutions)
CREATE TABLE IF NOT EXISTS hospitals (
    id SERIAL PRIMARY KEY,
    hospital_name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    city VARCHAR(100),
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    partnership_status VARCHAR(50) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Courses table (medical programs)
CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    country VARCHAR(100),
    duration VARCHAR(100),
    price FLOAT,
    hospital_id INTEGER REFERENCES hospitals(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Leads table (prospective students)
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    whatsapp VARCHAR(50),
    country VARCHAR(100),
    source VARCHAR(100),
    course_interested VARCHAR(255),
    status VARCHAR(50) DEFAULT 'Follow Up',
    assigned_to VARCHAR(255),
    ai_score FLOAT DEFAULT 0,
    ai_segment VARCHAR(50),
    conversion_probability FLOAT DEFAULT 0,
    expected_revenue FLOAT DEFAULT 0,
    actual_revenue FLOAT DEFAULT 0,
    follow_up_date TIMESTAMP,
    enrollment_deadline TIMESTAMP,
    last_contacted TIMESTAMP,
    feature_importance JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activities table (lead interaction tracking)
CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,
    description TEXT,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Notes table (lead notes and comments)
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Communication History table (WhatsApp, Email, Calls)
CREATE TABLE IF NOT EXISTS communication_history (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(50),
    communication_type VARCHAR(20) NOT NULL CHECK (communication_type IN ('whatsapp', 'email', 'call', 'sms')),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'sent',
    metadata JSONB,
    sender VARCHAR(255),
    recipient VARCHAR(255),
    used_for_training BOOLEAN DEFAULT FALSE,
    sentiment_score FLOAT,
    ai_insights TEXT,
    
    CONSTRAINT fk_lead
        FOREIGN KEY(lead_id)
        REFERENCES leads(lead_id)
        ON DELETE CASCADE
);

-- Counselors table (dedicated counselor profiles)
CREATE TABLE IF NOT EXISTS counselors (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    specialization TEXT,
    performance_score FLOAT DEFAULT 0,
    active_leads INTEGER DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================

-- Leads indexes (most queried table)
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);
CREATE INDEX IF NOT EXISTS idx_leads_segment ON leads(ai_segment);
CREATE INDEX IF NOT EXISTS idx_leads_assigned_to ON leads(assigned_to);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_updated_at ON leads(updated_at);
CREATE INDEX IF NOT EXISTS idx_leads_follow_up_date ON leads(follow_up_date);
CREATE INDEX IF NOT EXISTS idx_leads_ai_score ON leads(ai_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_status_segment ON leads(status, ai_segment);
CREATE INDEX IF NOT EXISTS idx_leads_lead_id ON leads(lead_id);

-- Activities indexes
CREATE INDEX IF NOT EXISTS idx_activities_lead_id ON activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON activities(created_at DESC);

-- Notes indexes
CREATE INDEX IF NOT EXISTS idx_notes_lead_id ON notes(lead_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at DESC);

-- Communication history indexes
CREATE INDEX IF NOT EXISTS idx_comm_lead_id ON communication_history(lead_id);
CREATE INDEX IF NOT EXISTS idx_comm_type ON communication_history(communication_type);
CREATE INDEX IF NOT EXISTS idx_comm_timestamp ON communication_history(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_comm_training ON communication_history(used_for_training);

-- Courses indexes
CREATE INDEX IF NOT EXISTS idx_courses_category ON courses(category);
CREATE INDEX IF NOT EXISTS idx_courses_active ON courses(is_active);
CREATE INDEX IF NOT EXISTS idx_courses_country ON courses(country);

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Counselors indexes
CREATE INDEX IF NOT EXISTS idx_counselors_email ON counselors(email);
CREATE INDEX IF NOT EXISTS idx_counselors_active ON counselors(is_active);

-- Hospitals indexes
CREATE INDEX IF NOT EXISTS idx_hospitals_country ON hospitals(country);

-- ============================================================================
-- AUTO-UPDATE TRIGGERS
-- ============================================================================

-- Trigger function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) - Optional but Recommended
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE communication_history ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to read all users
CREATE POLICY "Allow authenticated read access" ON users
    FOR SELECT
    USING (auth.role() = 'authenticated');

-- Policy: Allow authenticated users to read/write their own leads
CREATE POLICY "Allow authenticated access to leads" ON leads
    FOR ALL
    USING (auth.role() = 'authenticated');

-- Policy: Allow authenticated access to communication history
CREATE POLICY "Allow authenticated access to communication" ON communication_history
    FOR ALL
    USING (auth.role() = 'authenticated');

-- ============================================================================
-- SEED DATA (Sample Courses & Hospitals)
-- ============================================================================

-- Insert sample hospitals
INSERT INTO hospitals (hospital_name, country, city, partnership_status) VALUES
('All India Institute of Medical Sciences', 'India', 'New Delhi', 'Active'),
('Christian Medical College', 'India', 'Vellore', 'Active'),
('Manipal Academy of Higher Education', 'India', 'Manipal', 'Active'),
('King George Medical University', 'India', 'Lucknow', 'Active'),
('JSS Medical College', 'India', 'Mysore', 'Active')
ON CONFLICT DO NOTHING;

-- Insert sample courses
INSERT INTO courses (course_name, category, country, duration, price, is_active) VALUES
('MBBS', 'Medical', 'India', '5.5 years', 5000000, true),
('MD (General Medicine)', 'Post-Graduate', 'India', '3 years', 3000000, true),
('MS (General Surgery)', 'Post-Graduate', 'India', '3 years', 3500000, true),
('BDS', 'Dental', 'India', '4 years', 2500000, true),
('BAMS (Ayurveda)', 'Alternative Medicine', 'India', '5.5 years', 1500000, true),
('BHMS (Homeopathy)', 'Alternative Medicine', 'India', '5.5 years', 1200000, true),
('B.Sc Nursing', 'Nursing', 'India', '4 years', 800000, true),
('Pharmacy (B.Pharm)', 'Pharmacy', 'India', '4 years', 1000000, true),
('BPT (Physiotherapy)', 'Allied Health', 'India', '4.5 years', 900000, true),
('MBBS', 'Medical', 'Russia', '6 years', 4000000, true),
('MBBS', 'Medical', 'China', '6 years', 3500000, true),
('MBBS', 'Medical', 'Philippines', '5 years', 3000000, true)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these after migration to verify setup:
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- SELECT COUNT(*) FROM courses;
-- SELECT COUNT(*) FROM hospitals;

-- ============================================================================
-- COMPLETE! 🎉
-- ============================================================================
-- Your database is now ready for the CRM application.
-- Next steps:
-- 1. Update SUPABASE_URL in Render backend environment variables
-- 2. Update SUPABASE_KEY in Render backend environment variables
-- 3. Deploy backend and frontend
-- 4. Create your first admin user via API
-- ============================================================================
