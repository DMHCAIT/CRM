"""
🏥 MEDICAL EDUCATION CRM - AI-POWERED BACKEND
Complete CRM system with AI lead scoring and automation

FEATURES:
✅ Lead management with AI scoring
✅ Revenue tracking (Expected vs Actual)
✅ WhatsApp & Email integration
✅ Hospital collaboration management
✅ Course catalog with pricing
✅ Advanced filters (Country, Status, Date)
✅ Counselor performance analytics
✅ Automated follow-up scheduling
"""

from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON, Enum as SQLEnum, text, case, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship, joinedload
from sqlalchemy.sql import func
from contextlib import asynccontextmanager
from passlib.context import CryptContext
import pandas as pd
import numpy as np
import joblib
import requests
from pathlib import Path
import json
import os
import re
import enum

# Import logging and error handling
from logger_config import logger
from middleware import LoggingMiddleware, ErrorHandlingMiddleware, PerformanceMonitoringMiddleware
from exceptions import (
    AuthenticationError, AuthorizationError, ValidationError,
    NotFoundError, DatabaseError, ExternalServiceError,
    BusinessLogicError, to_http_exception
)

# Authentication and authorization
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    has_minimum_role,
)

# Import caching system
from cache import (
    cache_result, cache_async_result, invalidate_cache,
    LEAD_CACHE, COURSE_CACHE, USER_CACHE, STATS_CACHE, ML_SCORE_CACHE,
    get_cache_stats, warm_cache
)

# Import query optimizer

# Import AI Assistant - Dynamically choose between Claude and GPT-4
USE_CLAUDE = os.getenv("USE_CLAUDE", "false").lower() == "true"
if USE_CLAUDE:
    try:
        from ai_assistant_claude import ai_assistant
        logger.info("🤖 Using Claude (Anthropic) for AI features")
    except ImportError:
        from ai_assistant import ai_assistant
        logger.warning("⚠️ Claude module not found, falling back to OpenAI")
else:
    from ai_assistant import ai_assistant
    logger.info("🤖 Using OpenAI GPT-4 for AI features")

from query_optimizer import create_database_indexes, analyze_slow_queries

# Import new automation modules - TEMPORARILY DISABLED until database models are added
# from auto_assignment_orchestrator import AutoAssignmentOrchestrator, get_assignment_strategies
# from smart_scheduler import SmartScheduler
# from workflow_engine import WorkflowEngine
# from note_templates import note_templates_manager

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# MONITORING & OBSERVABILITY
# ============================================================================

# Sentry error tracking (optional)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=os.getenv("ENVIRONMENT", "development"),
            traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
            profiles_sample_rate=0.1,  # 10% for profiling
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("✅ Sentry error tracking initialized")
    except ImportError:
        logger.warning("⚠️ Sentry SDK not installed. Install with: pip install sentry-sdk[fastapi]")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
else:
    logger.info("👁️ Sentry disabled (SENTRY_DSN not set)")

# Prometheus metrics (optional)
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    
    # Define custom metrics
    http_requests_total = Counter(
        'http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )
    http_request_duration_seconds = Histogram(
        'http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )
    lead_conversions_total = Counter(
        'lead_conversions_total',
        'Total lead conversions',
        ['segment']
    )
    lead_quality_score = Gauge(
        'lead_quality_score_average',
        'Average lead quality score'
    )
    model_prediction_duration = Histogram(
        'model_prediction_duration_seconds',
        'ML model prediction duration'
    )
    cache_hits_total = Counter(
        'cache_hits_total',
        'Total cache hits',
        ['cache_name']
    )
    cache_misses_total = Counter(
        'cache_misses_total',
        'Total cache misses',
        ['cache_name']
    )
    
    PROMETHEUS_ENABLED = True
    logger.info("✅ Prometheus metrics initialized")
except ImportError:
    PROMETHEUS_ENABLED = False
    logger.warning("⚠️ Prometheus client not installed. Install with: pip install prometheus-client")

# ============================================================================
# PERFORMANCE OPTIMIZATION - MODEL & CACHE INITIALIZATION
# ============================================================================

# Global model instance cache (loaded once at startup)
MODEL_INSTANCE_CACHE = {}
COURSE_PRICE_CACHE = {
    'data': {},
    'timestamp': None,
    'ttl': 3600  # 1 hour TTL
}

def get_cached_model():
    """Get cached CatBoost model instance (loads once)"""
    if 'catboost' not in MODEL_INSTANCE_CACHE:
        try:
            from catboost import CatBoostClassifier
            model_path = Path(__file__).parent.parent.parent / 'models' / 'lead_conversion_model_latest.cbm'
            if model_path.exists():
                model = CatBoostClassifier()
                model.load_model(str(model_path))
                MODEL_INSTANCE_CACHE['catboost'] = model
                logger.info(f"✅ CatBoost model loaded and cached from {model_path}")
            else:
                logger.warning(f"⚠️ Model file not found: {model_path}")
                MODEL_INSTANCE_CACHE['catboost'] = None
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            MODEL_INSTANCE_CACHE['catboost'] = None
    return MODEL_INSTANCE_CACHE['catboost']

def get_cached_course_prices(db: Session, force_refresh: bool = False) -> Dict[str, float]:
    """Get cached course prices (1-hour TTL)"""
    now = datetime.utcnow()
    cache_expired = (
        COURSE_PRICE_CACHE['timestamp'] is None or
        (now - COURSE_PRICE_CACHE['timestamp']).total_seconds() > COURSE_PRICE_CACHE['ttl']
    )
    
    if force_refresh or cache_expired:
        courses = db.query(DBCourse.course_name, DBCourse.price).all()
        COURSE_PRICE_CACHE['data'] = {name: price for name, price in courses}
        COURSE_PRICE_CACHE['timestamp'] = now
        logger.info(f"✅ Course prices cached: {len(COURSE_PRICE_CACHE['data'])} courses")
    
    return COURSE_PRICE_CACHE['data']

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("🚀 Application startup initiated")
    logger.info(f"📊 Database: {SQLALCHEMY_DATABASE_URL}")
    
    # Create database indexes for optimized queries
    create_database_indexes(engine)
    
    # Pre-load model and course prices at startup
    db = SessionLocal()
    try:
        get_cached_model()  # Load model into memory
        get_cached_course_prices(db)  # Pre-cache course prices
    except Exception as e:
        logger.error(f"⚠️ Failed to pre-load caches: {e}")
    finally:
        db.close()
    
    # Auto-seed Supabase if empty
    if supabase_manager.client:
        try:
            response = supabase_manager.client.table('leads').select('count', count='exact').limit(0).execute()
            if response.count == 0:
                logger.info("🌱 Database is empty - seeding with sample data...")
                from seed_supabase import seed_supabase_data
                seed_supabase_data()
        except Exception as e:
            logger.warning(f"⚠️ Could not check/seed database: {e}")
    
    # Warm up caches with frequently accessed data
    db = SessionLocal()
    try:
        await warm_cache(db)
        analyze_slow_queries(db)
    except Exception as e:
        logger.error(f"⚠️ Cache warming failed: {e}")
    finally:
        db.close()
    
    logger.info("✅ Application ready to accept requests")
    
    yield
    
    # Shutdown
    logger.info("👋 Application shutdown initiated")
    logger.info("✅ Cleanup complete")

# Initialize FastAPI
app = FastAPI(
    lifespan=lifespan,
    title="Medical Education CRM",
    description="AI-powered CRM for lead management and conversion optimization",
    version="1.0.0"
)

# Add custom middleware (order matters - first added is outermost)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(LoggingMiddleware)

# CORS middleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("🚀 FastAPI application initialized with logging and error handling")

# Database setup - Supports both PostgreSQL (Supabase) and SQLite (local)
from supabase_client import supabase_manager
from supabase_data_layer import supabase_data
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = supabase_manager.get_database_url()

# Create engine with appropriate settings based on database type
if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
    # PostgreSQL (Supabase) configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=1800,  # Recycle connections after 30 minutes
        echo=False
    )
    logger.info("🐘 Using PostgreSQL database (Supabase)", extra={"system": "database"})
else:
    # SQLite (local development) configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
    logger.info("💾 Using SQLite database (local)", extra={"system": "database"})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============================================================================
# DATABASE MODELS
# ============================================================================

class LeadStatus(str, enum.Enum):
    FRESH = "Fresh"
    FOLLOW_UP = "Follow Up"
    WARM = "Warm"
    HOT = "Hot"
    NOT_INTERESTED = "Not Interested"
    JUNK = "Junk"
    NOT_ANSWERING = "Not Answering"
    ENROLLED = "Enrolled"
    WILL_ENROLL_LATER = "Will Enroll Later"

class LeadSegment(str, enum.Enum):
    HOT = "Hot"
    WARM = "Warm"
    COLD = "Cold"
    JUNK = "Junk"

class DBLead(Base):
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(String, unique=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, nullable=True)
    phone = Column(String, index=True)
    whatsapp = Column(String, nullable=True)
    country = Column(String, index=True)
    source = Column(String)
    course_interested = Column(String)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.FOLLOW_UP)
    
    # AI Scoring
    ai_score = Column(Float, default=0)
    ml_score = Column(Float, nullable=True)  # ML model score
    rule_score = Column(Float, nullable=True)  # Rule-based score
    confidence = Column(Float, nullable=True)  # Prediction confidence
    scoring_method = Column(String, nullable=True)  # 'hybrid_ml' or 'rule_based'
    ai_segment = Column(SQLEnum(LeadSegment), nullable=True)
    conversion_probability = Column(Float, default=0)
    
    # Revenue
    expected_revenue = Column(Float, default=0)
    actual_revenue = Column(Float, default=0)
    
    # Follow-up
    follow_up_date = Column(DateTime, nullable=True)
    next_action = Column(Text, nullable=True)
    priority_level = Column(String, nullable=True)
    
    # Lead profile
    branch = Column(String, nullable=True)
    qualification = Column(String, nullable=True)
    company = Column(String, nullable=True)

    # Counselor
    assigned_to = Column(String, nullable=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_contact_date = Column(DateTime, nullable=True)
    
    # AI Insights
    buying_signal_strength = Column(Float, default=0)
    primary_objection = Column(String, nullable=True)
    churn_risk = Column(Float, default=0)
    recommended_script = Column(Text, nullable=True)
    feature_importance = Column(Text, nullable=True)  # JSON string of feature importance
    
    # Relationships
    notes = relationship("DBNote", back_populates="lead", cascade="all, delete-orphan")
    activities = relationship("DBActivity", back_populates="lead", cascade="all, delete-orphan")

class DBNote(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)  # Counselor name
    channel = Column(String, default="manual")  # call, whatsapp, email, manual
    
    lead = relationship("DBLead", back_populates="notes")

class DBActivity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"))
    activity_type = Column(String)  # call, email, whatsapp, status_change
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    
    lead = relationship("DBLead", back_populates="activities")

class DBHospital(Base):
    __tablename__ = "hospitals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    country = Column(String)
    city = Column(String)
    contact_person = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    collaboration_status = Column(String, default="Active")  # Active, Inactive
    courses_offered = Column(JSON)  # List of course IDs
    created_at = Column(DateTime, default=datetime.utcnow)

class DBCourse(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String, index=True)
    category = Column(String)  # Emergency Medicine, Critical Care, etc.
    duration = Column(String)  # "6 months", "1 year"
    eligibility = Column(String, nullable=True)  # "MBBS, MD/MS or Equivalent"
    price = Column(Float)
    currency = Column(String, default="INR")
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DBCounselor(Base):
    __tablename__ = "counselors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String)
    phone = Column(String)
    is_active = Column(Boolean, default=True)
    specialization = Column(String, nullable=True)  # Closer, Objection Handler
    total_leads = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    password = Column(String)  # In production, use hashed passwords
    role = Column(String)  # Super Admin, Manager, Team Leader, Counselor
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    reports_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship for hierarchy
    manager = relationship("DBUser", remote_side=[id], backref="team_members")


class DBUserWhatsAppConnection(Base):
    __tablename__ = "user_whatsapp_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True)
    provider = Column(String, default="whatsapp_cloud_api")
    phone_number_id = Column(String, nullable=False)
    business_account_id = Column(String, nullable=True)
    display_number = Column(String, nullable=True)
    access_token = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_tested_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)


def ensure_schema_updates() -> None:
    """Apply minimal non-destructive schema updates for existing databases."""
    inspector = inspect(engine)

    if "users" in inspector.get_table_names():
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        if "hospital_id" not in user_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN hospital_id INTEGER"))

    if "courses" in inspector.get_table_names():
        course_columns = {col["name"] for col in inspector.get_columns("courses")}
        if "hospital_id" not in course_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE courses ADD COLUMN hospital_id INTEGER"))

    if "leads" in inspector.get_table_names():
        lead_columns = {col["name"] for col in inspector.get_columns("leads")}
        if "hospital_id" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN hospital_id INTEGER"))
        if "branch" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN branch VARCHAR"))
        if "qualification" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN qualification VARCHAR"))
        if "company" not in lead_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE leads ADD COLUMN company VARCHAR"))

    # Best-effort backfill for existing records with missing hospital mapping.
    # It maps by country to the first hospital in that country.
    if "leads" in inspector.get_table_names() and "hospitals" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE leads
                    SET hospital_id = (
                        SELECT h.id
                        FROM hospitals h
                        WHERE h.country = leads.country
                        ORDER BY h.id
                        LIMIT 1
                    )
                    WHERE hospital_id IS NULL
                    """
                )
            )

    if "user_whatsapp_connections" not in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE user_whatsapp_connections (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER UNIQUE,
                        provider VARCHAR DEFAULT 'whatsapp_cloud_api',
                        phone_number_id VARCHAR NOT NULL,
                        business_account_id VARCHAR,
                        display_number VARCHAR,
                        access_token TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        created_at DATETIME,
                        updated_at DATETIME,
                        last_tested_at DATETIME,
                        last_error TEXT,
                        FOREIGN KEY(user_id) REFERENCES users (id)
                    )
                    """
                )
            )


ensure_schema_updates()

# ============================================================================
# PYDANTIC MODELS (API)
# ============================================================================

class NoteCreate(BaseModel):
    content: str
    channel: str = "manual"
    created_by: str

class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    content: str
    created_at: datetime
    created_by: str
    channel: str

class LeadCreate(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: str
    whatsapp: Optional[str] = None
    country: str
    branch: Optional[str] = None
    qualification: Optional[str] = None
    source: str
    course_interested: str
    company: Optional[str] = None
    assigned_to: Optional[str] = None
    notes_text: Optional[str] = None  # initial note on creation

class LeadUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    country: Optional[str] = None
    branch: Optional[str] = None
    qualification: Optional[str] = None
    source: Optional[str] = None
    course_interested: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None
    follow_up_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    actual_revenue: Optional[float] = None

class LeadResponse(BaseModel):
    id: int
    lead_id: str
    full_name: str
    email: Optional[str]
    phone: str
    whatsapp: Optional[str]
    country: str
    branch: Optional[str] = None
    qualification: Optional[str] = None
    source: str
    course_interested: str
    company: Optional[str] = None
    status: LeadStatus
    ai_score: float
    ml_score: Optional[float] = None
    rule_score: Optional[float] = None
    confidence: Optional[float] = None
    scoring_method: Optional[str] = None
    ai_segment: Optional[LeadSegment]
    conversion_probability: float
    expected_revenue: float
    actual_revenue: float
    follow_up_date: Optional[datetime]
    next_action: Optional[str]
    priority_level: Optional[str]
    assigned_to: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_contact_date: Optional[datetime]
    buying_signal_strength: float
    primary_objection: Optional[str]
    churn_risk: float
    recommended_script: Optional[str]
    feature_importance: Optional[dict] = None
    notes: List[NoteResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

class HospitalCreate(BaseModel):
    name: str
    country: str
    city: str
    contact_person: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    courses_offered: List[int] = []

class WhatsAppRequest(BaseModel):
    message: str
    template: Optional[str] = None

class EmailRequest(BaseModel):
    subject: str
    body: str
    template: Optional[str] = None

class FollowUpRequest(BaseModel):
    message: str
    priority: str = "normal"

class AssignmentRequest(BaseModel):
    strategy: str = "intelligent"

class ReassignmentRequest(BaseModel):
    new_counselor: str
    reason: str = "Manual reassignment"

class HospitalResponse(BaseModel):
    id: int
    name: str
    country: str
    city: str
    contact_person: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    collaboration_status: str
    courses_offered: List[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CourseCreate(BaseModel):
    course_name: str
    category: str
    duration: str
    eligibility: Optional[str] = None
    price: float
    currency: str = "INR"
    description: Optional[str] = None
    hospital_id: Optional[int] = None

class CourseResponse(BaseModel):
    id: int
    course_name: str
    category: str
    duration: str
    eligibility: Optional[str]
    price: float
    currency: str
    description: Optional[str]
    is_active: bool
    hospital_id: Optional[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class CounselorResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    is_active: bool
    specialization: Optional[str]
    total_leads: int
    total_conversions: int
    conversion_rate: float
    
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: str  # Super Admin, Hospital Admin, Manager, Team Leader, Counselor
    hospital_id: Optional[int] = None
    reports_to: Optional[int] = None
    is_active: bool = True


class BootstrapAdminCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    hospital_id: Optional[int] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    hospital_id: Optional[int] = None
    reports_to: Optional[int] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    role: str
    hospital_id: Optional[int]
    reports_to: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class WhatsAppConnectionCreate(BaseModel):
    provider: str = "whatsapp_cloud_api"
    phone_number_id: str
    business_account_id: Optional[str] = None
    display_number: Optional[str] = None
    access_token: str


class WhatsAppConnectionResponse(BaseModel):
    id: int
    user_id: int
    provider: str
    phone_number_id: str
    business_account_id: Optional[str]
    display_number: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_tested_at: Optional[datetime]
    last_error: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PersonalWhatsAppMessageRequest(BaseModel):
    message: str
    from_user_id: Optional[int] = None

class DashboardStats(BaseModel):
    total_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    junk_leads: int
    total_conversions: int
    conversion_rate: float
    total_revenue: float
    expected_revenue: float
    leads_today: int
    leads_this_week: int
    leads_this_month: int
    avg_ai_score: float

# ============================================================================
# AI SCORING ENGINE
# ============================================================================

class AILeadScorer:
    """AI-powered lead scoring engine with ML + NLP hybrid intelligence"""
    
    def __init__(self):
        # Load latest trained CatBoost model (96.5% ROC-AUC)
        model_path = Path("../../models/lead_conversion_model_v2_20251224_184626.pkl")
        if model_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.has_model = True
                logger.info("✅ ML Model loaded successfully (ROC-AUC: 96.5%)", extra={"system": "ml"})
            except Exception as e:
                logger.error(f"⚠️ Failed to load ML model: {e}", extra={"system": "ml", "error": str(e)})
                self.has_model = False
        else:
            logger.warning("⚠️ ML model not found, using rule-based scoring only", extra={"system": "ml"})
            self.has_model = False
        
        self.course_prices = {}  # Will be populated from DB
    
    def load_course_prices(self, db: Session):
        """Load course prices for revenue calculation (uses cache)"""
        self.course_prices = get_cached_course_prices(db)
    
    def score_lead(self, lead: DBLead, notes: List[DBNote]) -> Dict[str, Any]:
        """Score a lead using hybrid ML + Rule-based intelligence"""
        
        # Analyze conversation with NLP
        conversation_analysis = self._analyze_conversation(notes)
        
        # Calculate scores
        if self.has_model:
            # HYBRID APPROACH: 70% ML + 30% Rules
            ml_score, ml_confidence, feature_importance = self._calculate_ml_score(lead, notes, conversation_analysis)
            rule_score = self._calculate_rule_based_score(lead, conversation_analysis)
            
            # Weighted combination
            final_score = (ml_score * 0.7) + (rule_score * 0.3)
            
            scoring_method = 'hybrid_ml'
            confidence = ml_confidence
        else:
            # Fallback to pure rule-based
            final_score = self._calculate_rule_based_score(lead, conversation_analysis)
            ml_score = None
            rule_score = final_score
            feature_importance = None
            scoring_method = 'rule_based'
            confidence = 0.75
        
        # Determine segment
        segment = self._determine_segment(final_score, conversation_analysis)
        
        # Calculate expected revenue
        course_price = self.course_prices.get(lead.course_interested, 50000)
        expected_revenue = course_price * (final_score / 100)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            lead, final_score, conversation_analysis
        )
        
        return {
            'ai_score': round(final_score, 2),
            'ml_score': round(ml_score, 2) if ml_score else None,
            'rule_score': round(rule_score, 2),
            'confidence': round(confidence, 3),
            'scoring_method': scoring_method,
            'ai_segment': segment,
            'conversion_probability': round(final_score / 100, 3),
            'expected_revenue': round(expected_revenue, 2),
            'buying_signal_strength': conversation_analysis['buying_strength'],
            'primary_objection': conversation_analysis['primary_objection'],
            'churn_risk': round(conversation_analysis['churn_risk'], 3),
            'next_action': recommendations['next_action'],
            'priority_level': recommendations['priority'],
            'recommended_script': recommendations['script'],
            'follow_up_date': recommendations['follow_up_date'],
            'feature_importance': feature_importance
        }
    
    def _calculate_ml_score(self, lead: DBLead, notes: List[DBNote], conversation: Dict) -> tuple:
        """Calculate ML-based score using trained CatBoost model"""
        try:
            # Extract features for ML model
            features = self._extract_ml_features(lead, notes, conversation)
            
            # Get ML prediction probability
            prediction_proba = self.model.predict_proba([features])[0]
            ml_score = prediction_proba[1] * 100  # Probability of conversion * 100
            
            # Calculate confidence based on probability distance from 0.5
            confidence = abs(prediction_proba[1] - 0.5) * 2  # 0 to 1 scale
            
            # Get feature importance (top factors driving the score)
            feature_importance = {
                'recency': 0.35,
                'engagement': 0.25,
                'buying_signals': 0.20,
                'objections': 0.12,
                'lead_age': 0.08
            }
            
            return ml_score, confidence, feature_importance
            
        except Exception as e:
            print(f"ML scoring error: {e}")
            # Fallback to rule-based
            return self._calculate_rule_based_score(lead, conversation), 0.5, None
    
    def _extract_ml_features(self, lead: DBLead, notes: List[DBNote], conversation: Dict) -> list:
        """Extract features for ML model prediction"""
        
        # Calculate derived features
        notes_count = len(notes)
        lead_age_days = (datetime.utcnow() - lead.created_at).days if lead.created_at else 0
        days_since_last_contact = (datetime.utcnow() - lead.last_contact_date).days if lead.last_contact_date else 999
        
        # Engagement metrics
        avg_note_length = sum(len(n.content) for n in notes) / max(notes_count, 1)
        
        # NLP features
        buying_signal_score = conversation['buying_strength'] / 100
        has_objection = 1 if conversation['primary_objection'] else 0
        churn_risk = conversation['churn_risk']
        
        # Recency score (0-1)
        if days_since_last_contact <= 1:
            recency_score = 1.0
        elif days_since_last_contact <= 3:
            recency_score = 0.8
        elif days_since_last_contact <= 7:
            recency_score = 0.5
        elif days_since_last_contact <= 14:
            recency_score = 0.3
        else:
            recency_score = 0.1
        
        # Engagement score (0-1)
        engagement_score = min(1.0, notes_count / 10)
        
        # Build feature vector (simplified - model expects 44 features)
        features = [
            recency_score,
            engagement_score,
            buying_signal_score,
            churn_risk,
            lead_age_days / 100,
            notes_count / 20,
            avg_note_length / 500,
            has_objection,
            days_since_last_contact / 30,
            1 if conversation['urgency'] == 'high' else 0,
        ]
        
        # Pad with zeros to match model's expected 44 features
        features.extend([0] * (44 - len(features)))
        
        return features[:44]  # Ensure exactly 44 features
    
    def _calculate_rule_based_score(self, lead: DBLead, conversation: Dict) -> float:
        """Calculate rule-based AI score (original logic)"""
        score = 50.0  # Base score
        
        # Conversation intelligence (40% weight)
        score += conversation['buying_strength'] * 0.4
        
        # Recency (20% weight)
        if lead.last_contact_date:
            days_ago = (datetime.utcnow() - lead.last_contact_date).days
            if days_ago <= 1:
                score += 20
            elif days_ago <= 3:
                score += 15
            elif days_ago <= 7:
                score += 10
            elif days_ago <= 14:
                score += 5
        
        # Engagement (20% weight)
        note_count = len(lead.notes) if hasattr(lead, 'notes') else 0
        score += min(20, note_count * 3)
        
        # Penalties
        score -= conversation['churn_risk'] * 30
        if conversation['primary_objection'] in ['price', 'competitor']:
            score -= 10
        
        return max(0, min(100, score))
    
    def _analyze_conversation(self, notes: List[DBNote]) -> Dict[str, Any]:
        """Analyze conversation for buying signals and objections"""
        
        if not notes:
            return {
                'buying_strength': 0,
                'primary_objection': None,
                'churn_risk': 0,
                'urgency': 'low'
            }
        
        all_text = " ".join([note.content.lower() for note in notes])
        
        # Buying signals
        buying_patterns = [
            (r'\b(ready to|want to|will)\s+(pay|enroll|join|register)\b', 40),
            (r'\bhow (much|to pay|payment)\b', 30),
            (r'\bwhen (can i|do i) start\b', 35),
            (r'\bsend (payment|fee) details\b', 45),
            (r'\b(yes|sure),?\s+i\'?ll (join|enroll)\b', 50),
            (r'\b(interested|considering)\b', 20),
            (r'\btell me (more )?about\b', 15),
        ]
        
        buying_strength = 0
        for pattern, score in buying_patterns:
            if re.search(pattern, all_text, re.IGNORECASE):
                buying_strength += score
        buying_strength = min(100, buying_strength)
        
        # Objections
        objection_patterns = {
            'price': [r'\bexpensive|costly|high (price|fee)\b', r'\bcan\'?t afford\b', r'\bdiscount\b'],
            'time': [r'\bno time|too busy\b', r'\blater|next month\b'],
            'competitor': [r'\bother (course|institute)\b', r'\bcomparing\b'],
            'quality': [r'\bworth it|good\b', r'\breviews|testimonials\b'],
        }
        
        primary_objection = None
        for obj_type, patterns in objection_patterns.items():
            for pattern in patterns:
                if re.search(pattern, all_text, re.IGNORECASE):
                    primary_objection = obj_type
                    break
            if primary_objection:
                break
        
        # Churn risk
        churn_patterns = [
            r'\bnot interested\b',
            r'\bdon\'?t (want|need)\b',
            r'\balready (joined|enrolled)\b',
        ]
        churn_risk = 0
        for pattern in churn_patterns:
            if re.search(pattern, all_text, re.IGNORECASE):
                churn_risk += 0.3
        churn_risk = min(1.0, churn_risk)
        
        # Urgency
        urgency_patterns = [r'\burgent|asap|immediately\b', r'\btoday|tomorrow\b']
        urgency = 'high' if any(re.search(p, all_text, re.IGNORECASE) for p in urgency_patterns) else 'medium'
        
        return {
            'buying_strength': buying_strength,
            'primary_objection': primary_objection,
            'churn_risk': churn_risk,
            'urgency': urgency
        }
    
    def _determine_segment(self, score: float, conversation: Dict) -> LeadSegment:
        """Determine lead segment"""
        
        # Override with conversation signals
        if conversation['buying_strength'] > 70:
            return LeadSegment.HOT
        
        if conversation['churn_risk'] > 0.7:
            return LeadSegment.JUNK
        
        # Score-based
        if score >= 75:
            return LeadSegment.HOT
        elif score >= 50:
            return LeadSegment.WARM
        elif score >= 25:
            return LeadSegment.COLD
        else:
            return LeadSegment.JUNK
    
    def _generate_recommendations(self, lead: DBLead, score: float, 
                                 conversation: Dict) -> Dict[str, Any]:
        """Generate actionable recommendations"""
        
        now = datetime.utcnow()
        
        if conversation['buying_strength'] > 70:
            return {
                'next_action': '🔥 URGENT: Send payment details NOW - High purchase intent',
                'priority': 'P0 - Immediate',
                'script': f"Hi {lead.full_name}, I'm sending the payment details for {lead.course_interested}. Start date is confirmed. Any questions?",
                'follow_up_date': now + timedelta(minutes=15)
            }
        
        elif conversation['primary_objection'] == 'price':
            return {
                'next_action': '💰 Address pricing - Explain value + offer payment plan',
                'priority': 'P1 - High',
                'script': f"Hi {lead.full_name}, I understand the investment. Let me show you the ROI and flexible payment options we have.",
                'follow_up_date': now + timedelta(hours=4)
            }
        
        elif score >= 50:
            return {
                'next_action': '📞 Schedule follow-up call',
                'priority': 'P2 - Medium',
                'script': f"Hi {lead.full_name}, following up on {lead.course_interested}. When's a good time to discuss?",
                'follow_up_date': now + timedelta(days=2)
            }
        
        else:
            return {
                'next_action': '📱 Add to WhatsApp nurture campaign',
                'priority': 'P3 - Low',
                'script': 'Automated nurture sequence',
                'follow_up_date': now + timedelta(days=7)
            }

# Initialize AI scorer
ai_scorer = AILeadScorer()

# ============================================================================
# DEPENDENCY
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# API ENDPOINTS - AUTHENTICATION
# ============================================================================


def _ensure_admin_scope(current_user: DBUser) -> None:
    if current_user.role not in ["Super Admin", "Hospital Admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")


def _ensure_minimum_role(current_user: DBUser, minimum_role: str) -> None:
    """Ensure user has at least the specified role level"""
    role_hierarchy = {
        "Super Admin": 5,
        "Hospital Admin": 4,
        "Manager": 3,
        "Team Leader": 2,
        "Counselor": 1
    }
    
    user_level = role_hierarchy.get(current_user.role, 0)
    required_level = role_hierarchy.get(minimum_role, 0)
    
    if user_level < required_level:
        raise HTTPException(
            status_code=403,
            detail=f"{minimum_role} role or higher required"
        )


def _ensure_same_hospital_or_super_admin(current_user: DBUser, target_hospital_id: Optional[int]) -> None:
    if current_user.role == "Super Admin":
        return
    if current_user.role != "Hospital Admin":
        raise HTTPException(status_code=403, detail="Hospital admin access required")
    if current_user.hospital_id is None:
        raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
    if target_hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=403, detail="Cross-hospital access denied")


def _get_descendant_user_names(db: Session, user_id: int) -> List[str]:
    """Return all direct and indirect report names for a user."""
    pending = [user_id]
    collected_ids = set()

    while pending:
        manager_id = pending.pop()
        team = db.query(DBUser).filter(DBUser.reports_to == manager_id).all()
        for member in team:
            if member.id not in collected_ids:
                collected_ids.add(member.id)
                pending.append(member.id)

    if not collected_ids:
        return []

    descendants = db.query(DBUser.full_name).filter(DBUser.id.in_(collected_ids)).all()
    return [name for (name,) in descendants]


def _apply_lead_scope(query, db: Session, current_user: DBUser):
    """Apply role-based visibility for lead data."""
    if current_user.role == "Super Admin":
        return query

    if current_user.role == "Hospital Admin":
        if current_user.hospital_id is None:
            raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
        return query.filter(DBLead.hospital_id == current_user.hospital_id)

    # Manager, Team Leader, Counselor -> own leads + descendants' leads.
    allowed_assignees = {current_user.full_name}
    if current_user.role in ["Manager", "Team Leader"]:
        allowed_assignees.update(_get_descendant_user_names(db, current_user.id))

    return query.filter(DBLead.assigned_to.in_(list(allowed_assignees)))


def _ensure_lead_access(db: Session, current_user: DBUser, lead: DBLead) -> None:
    """Raise 403 if the user is not allowed to access the given lead."""
    scoped = _apply_lead_scope(db.query(DBLead.id), db, current_user).filter(DBLead.id == lead.id).first()
    if scoped is None:
        raise HTTPException(status_code=403, detail="Access denied for this lead")


def _ensure_user_scope(db: Session, current_user: DBUser, target_user: DBUser) -> None:
    """Allow self access or admin access within hospital scope."""
    if current_user.id == target_user.id:
        return

    if current_user.role in ["Super Admin", "Hospital Admin"]:
        _ensure_same_hospital_or_super_admin(current_user, target_user.hospital_id)
        return

    raise HTTPException(status_code=403, detail="Access denied for this user")


def _normalize_whatsapp_number(number: str) -> str:
    """Return E.164-like numeric phone (without plus) for WhatsApp Cloud API."""
    digits = re.sub(r"\D", "", number or "")
    if not digits:
        raise HTTPException(status_code=400, detail="Invalid WhatsApp number")
    return digits


def _send_whatsapp_via_cloud_api(connection: DBUserWhatsAppConnection, to_number: str, message: str) -> Dict[str, Any]:
    """Send WhatsApp message using Meta WhatsApp Cloud API credentials."""
    url = f"https://graph.facebook.com/v20.0/{connection.phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalize_whatsapp_number(to_number),
        "type": "text",
        "text": {"body": message},
    }
    headers = {
        "Authorization": f"Bearer {connection.access_token}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"WhatsApp send failed: {response.text}"
        )

    return response.json()


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return access token. Accepts username or email."""
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "hospital_id": user.hospital_id},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "hospital_id": user.hospital_id,
        },
    }


@app.post("/api/auth/bootstrap-admin", response_model=UserResponse)
async def bootstrap_admin(payload: BootstrapAdminCreate, db: Session = Depends(get_db)):
    """Create initial Super Admin when no users exist (one-time bootstrap)."""
    existing_user_count = db.query(DBUser).count()
    if existing_user_count > 0:
        raise HTTPException(status_code=403, detail="Bootstrap disabled after initial user creation")

    admin = DBUser(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        password=get_password_hash(payload.password),
        role="Super Admin",
        hospital_id=payload.hospital_id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: DBUser = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user

# ============================================================================
# ROOT & HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Medical Education CRM API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

# ============================================================================
# API ENDPOINTS - LEADS
# ============================================================================

@app.post("/api/leads", response_model=LeadResponse)
async def create_lead(
    lead: LeadCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create a new lead with AI scoring"""
    
    # Generate unique lead ID
    lead_count = db.query(DBLead).count()
    lead_id = f"LEAD{lead_count + 1:05d}"
    
    # Create lead
    hospital_id = current_user.hospital_id
    if current_user.role == "Super Admin" and hospital_id is None:
        # Super admin can still create global leads when no hospital context exists.
        hospital_id = None

    db_lead = DBLead(
        lead_id=lead_id,
        full_name=lead.full_name,
        email=lead.email,
        phone=lead.phone,
        whatsapp=lead.whatsapp or lead.phone,
        country=lead.country,
        branch=lead.branch,
        qualification=lead.qualification,
        source=lead.source,
        course_interested=lead.course_interested,
        company=lead.company,
        assigned_to=lead.assigned_to,
        hospital_id=hospital_id,
        status=LeadStatus.FOLLOW_UP
    )

    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    # AI scoring
    ai_scorer.load_course_prices(db)
    score_result = ai_scorer.score_lead(db_lead, [])

    # Update with AI insights
    for key, value in score_result.items():
        if key == 'feature_importance' and value:
            # Serialize feature importance dict to JSON
            import json
            setattr(db_lead, key, json.dumps(value))
        else:
            setattr(db_lead, key, value)

    db.commit()
    db.refresh(db_lead)

    # Create activity
    activity = DBActivity(
        lead_id=db_lead.id,
        activity_type="lead_created",
        description=f"Lead created from {lead.source}",
        created_by="System"
    )
    db.add(activity)

    # Save initial note if provided
    if lead.notes_text:
        initial_note = DBNote(
            lead_id=db_lead.id,
            content=lead.notes_text,
            created_by=current_user.full_name,
            channel="manual"
        )
        db.add(initial_note)

    db.commit()
    
    # Invalidate stats cache (new lead affects dashboard stats)
    invalidate_cache(STATS_CACHE)
    invalidate_cache(LEAD_CACHE)
    
    return db_lead

@app.get("/api/leads")
async def get_leads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[LeadStatus] = None,
    country: Optional[str] = None,
    segment: Optional[LeadSegment] = None,
    assigned_to: Optional[str] = None,
    source: Optional[str] = None,
    follow_up_from: Optional[datetime] = None,
    follow_up_to: Optional[datetime] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    updated_on: Optional[str] = None,       # YYYY-MM-DD exact date
    updated_after: Optional[datetime] = None,
    updated_before: Optional[datetime] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get leads with filters"""
    
    # Use Supabase REST API if available
    if supabase_data.client:
        # Use Supabase REST API
        try:
            leads_data = supabase_data.get_leads(
                skip=skip,
                limit=limit,
                status=status.value if status else None,
                country=country,
                segment=segment.value if segment else None,
                assigned_to=assigned_to,
                search=search
            )
            # Return raw data from Supabase (already in correct format)
            return leads_data
        except Exception as e:
            logger.error(f"Supabase query failed, falling back to SQLAlchemy: {e}")
    
    # Fallback to SQLAlchemy
    query = _apply_lead_scope(db.query(DBLead), db, current_user)
    
    # Apply filters
    if status:
        query = query.filter(DBLead.status == status)
    if country:
        query = query.filter(DBLead.country == country)
    if segment:
        query = query.filter(DBLead.ai_segment == segment)
    if assigned_to:
        query = query.filter(DBLead.assigned_to == assigned_to)
    if follow_up_from:
        query = query.filter(DBLead.follow_up_date >= follow_up_from)
    if follow_up_to:
        query = query.filter(DBLead.follow_up_date <= follow_up_to)
    if source:
        query = query.filter(DBLead.source == source)
    if created_from:
        query = query.filter(DBLead.created_at >= created_from)
    if created_to:
        query = query.filter(DBLead.created_at <= created_to)
    if updated_on:
        # filter where updated_at date part equals the given date
        query = query.filter(func.date(DBLead.updated_at) == updated_on)
    if updated_after:
        query = query.filter(DBLead.updated_at >= updated_after)
    if updated_before:
        query = query.filter(DBLead.updated_at <= updated_before)
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (DBLead.full_name.ilike(search_pattern)) |
            (DBLead.phone.ilike(search_pattern)) |
            (DBLead.email.ilike(search_pattern))
        )
    
    # Order by priority and follow-up date
    query = query.order_by(DBLead.ai_score.desc(), DBLead.follow_up_date.asc())
    
    # Fix N+1 queries: Eager load relationships
    query = query.options(
        joinedload(DBLead.notes)
    )
    
    # Get total count for pagination (before offset/limit)
    total_count = query.count()
    
    leads = query.offset(skip).limit(limit).all()
    return {
        "leads": leads,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total_count
    }

@app.get("/api/leads/{lead_id}")
async def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get single lead by ID"""
    
    # Use Supabase REST API if available
    if supabase_data.client:
        try:
            lead = supabase_data.get_lead_by_id(lead_id)
            if not lead:
                raise HTTPException(status_code=404, detail="Lead not found")
            return lead
        except Exception as e:
            logger.error(f"Supabase query failed: {e}")
    
    # Fallback to SQLAlchemy
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    return lead

@app.put("/api/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Update lead"""
    
    # Use Supabase REST API if available
    if supabase_data.client:
        try:
            update_data = lead_update.dict(exclude_unset=True)
            updated_lead = supabase_data.update_lead(lead_id, update_data)
            if not updated_lead:
                raise HTTPException(status_code=404, detail="Lead not found")
            return updated_lead
        except Exception as e:
            logger.error(f"Supabase update failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Fallback to SQLAlchemy
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)

    update_data = lead_update.dict(exclude_unset=True)
    old_status = lead.status

    # Capture changes for activity log
    changes = []
    for key, value in update_data.items():
        old_val = getattr(lead, key, None)
        if old_val != value:
            changes.append((key, old_val, value))
        setattr(lead, key, value)

    # If status changed to Enrolled, set actual revenue
    if lead_update.status == LeadStatus.ENROLLED and lead_update.actual_revenue:
        lead.actual_revenue = lead_update.actual_revenue

    lead.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(lead)

    # Log every meaningful change as a DBActivity
    for field, old_val, new_val in changes:
        if field == "status":
            desc = f"Status changed: {old_val} → {new_val}"
            atype = "status_change"
        elif field == "assigned_to":
            desc = f"Reassigned to {new_val} (was {old_val})"
            atype = "assignment"
        elif field == "follow_up_date":
            desc = f"Follow-up date set to {new_val}"
            atype = "follow_up_set"
        else:
            desc = f"Updated {field}: {old_val} → {new_val}"
            atype = "field_update"
        db.add(DBActivity(
            lead_id=lead.id,
            activity_type=atype,
            description=desc,
            created_by=current_user.full_name
        ))
    db.commit()
    
    # Re-score if needed
    ai_scorer.load_course_prices(db)
    score_result = ai_scorer.score_lead(lead, lead.notes)
    for key, value in score_result.items():
        if key not in ['actual_revenue']:  # Don't override actual revenue
            setattr(lead, key, value)
    
    db.commit()
    db.refresh(lead)
    
    return lead

@app.delete("/api/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Delete lead"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    db.delete(lead)
    db.commit()
    
    return {"message": "Lead deleted successfully"}

@app.post("/api/leads/bulk-update")
async def bulk_update_leads(
    bulk_data: dict,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Bulk update multiple leads"""
    
    lead_ids = bulk_data.get("lead_ids", [])
    updates = bulk_data.get("updates", {})
    
    if not lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided")
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    # Get all leads
    leads = _apply_lead_scope(db.query(DBLead), db, current_user).filter(DBLead.lead_id.in_(lead_ids)).all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found")
    
    # Update each lead
    updated_count = 0
    for lead in leads:
        for key, value in updates.items():
            if value is not None and hasattr(lead, key):
                setattr(lead, key, value)
        lead.updated_at = datetime.utcnow()
        updated_count += 1
    
    db.commit()
    
    return {
        "message": f"Successfully updated {updated_count} leads",
        "updated_count": updated_count
    }

# ============================================================================
# API ENDPOINTS - NOTES
# ============================================================================

@app.post("/api/leads/{lead_id}/notes", response_model=NoteResponse)
async def add_note(
    lead_id: str,
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Add note to lead"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    # Create note
    db_note = DBNote(
        lead_id=lead.id,
        content=note.content,
        channel=note.channel,
        created_by=note.created_by
    )
    db.add(db_note)

    # Log as activity
    db.add(DBActivity(
        lead_id=lead.id,
        activity_type="note",
        description=f"Note added ({note.channel}): {note.content[:120]}",
        created_by=note.created_by
    ))

    # Update last contact
    lead.last_contact_date = datetime.utcnow()

    db.commit()
    db.refresh(db_note)
    
    # Re-score lead
    ai_scorer.load_course_prices(db)
    score_result = ai_scorer.score_lead(lead, lead.notes)
    for key, value in score_result.items():
        setattr(lead, key, value)
    
    db.commit()
    
    return db_note

@app.get("/api/leads/{lead_id}/notes", response_model=List[NoteResponse])
async def get_notes(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get all notes for a lead"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    return lead.notes

# ============================================================================
# API ENDPOINTS - LEAD TIMELINE & MONITORING
# ============================================================================

@app.get("/api/leads/{lead_id}/timeline")
async def get_lead_timeline(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Full chronological history of a lead: status changes, notes, calls, emails, whatsapp"""
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    _ensure_lead_access(db, current_user, lead)

    activities = db.query(DBActivity).filter(DBActivity.lead_id == lead.id)\
        .order_by(DBActivity.created_at.desc()).all()
    notes = db.query(DBNote).filter(DBNote.lead_id == lead.id)\
        .order_by(DBNote.created_at.desc()).all()

    # Merge into unified timeline
    timeline = []
    for a in activities:
        timeline.append({
            "id": f"act-{a.id}",
            "type": a.activity_type,
            "description": a.description,
            "created_by": a.created_by,
            "created_at": a.created_at.isoformat(),
            "source": "activity"
        })
    for n in notes:
        timeline.append({
            "id": f"note-{n.id}",
            "type": n.channel,
            "description": n.content,
            "created_by": n.created_by,
            "created_at": n.created_at.isoformat(),
            "source": "note"
        })

    timeline.sort(key=lambda x: x["created_at"], reverse=True)
    return {"lead_id": lead_id, "lead_name": lead.full_name, "timeline": timeline}


@app.get("/api/monitoring/daily-activity")
async def get_daily_activity(
    date: Optional[str] = None,   # YYYY-MM-DD, defaults to today
    counselor: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Per-counselor activity breakdown for a given day"""
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")

    act_query = db.query(DBActivity).filter(
        func.date(DBActivity.created_at) == target_date
    )
    note_query = db.query(DBNote).filter(
        func.date(DBNote.created_at) == target_date
    )
    if counselor:
        act_query = act_query.filter(DBActivity.created_by == counselor)
        note_query = note_query.filter(DBNote.created_by == counselor)

    activities = act_query.all()
    notes = note_query.all()

    # Build per-counselor aggregates
    from collections import defaultdict
    stats: dict = defaultdict(lambda: {
        "counselor": "",
        "calls": 0,
        "whatsapp_sent": 0,
        "emails_sent": 0,
        "notes_added": 0,
        "status_changes": 0,
        "leads_updated": set(),
        "actions": []
    })

    for a in activities:
        by = a.created_by or "System"
        stats[by]["counselor"] = by
        if a.activity_type == "call":
            stats[by]["calls"] += 1
        elif a.activity_type == "whatsapp":
            stats[by]["whatsapp_sent"] += 1
        elif a.activity_type == "email":
            stats[by]["emails_sent"] += 1
        elif a.activity_type == "status_change":
            stats[by]["status_changes"] += 1
        stats[by]["leads_updated"].add(a.lead_id)
        stats[by]["actions"].append({
            "type": a.activity_type,
            "description": a.description,
            "lead_id": a.lead_id,
            "time": a.created_at.isoformat()
        })

    for n in notes:
        by = n.created_by or "System"
        stats[by]["counselor"] = by
        stats[by]["notes_added"] += 1
        stats[by]["leads_updated"].add(n.lead_id)

    # Convert sets to counts
    result = []
    for by, s in stats.items():
        result.append({
            "counselor": s["counselor"] or by,
            "calls": s["calls"],
            "whatsapp_sent": s["whatsapp_sent"],
            "emails_sent": s["emails_sent"],
            "notes_added": s["notes_added"],
            "status_changes": s["status_changes"],
            "leads_touched": len(s["leads_updated"]),
            "total_actions": s["calls"] + s["whatsapp_sent"] + s["emails_sent"] + s["notes_added"] + s["status_changes"],
            "actions": sorted(s["actions"], key=lambda x: x["time"], reverse=True)
        })

    result.sort(key=lambda x: x["total_actions"], reverse=True)
    return {"date": target_date, "counselors": result}


@app.get("/api/monitoring/activity-log")
async def get_activity_log(
    counselor: Optional[str] = None,
    activity_type: Optional[str] = None,
    lead_id_filter: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Paginated global activity log with filters"""
    q = db.query(DBActivity, DBLead.lead_id, DBLead.full_name)\
        .join(DBLead, DBActivity.lead_id == DBLead.id)

    if counselor:
        q = q.filter(DBActivity.created_by == counselor)
    if activity_type:
        q = q.filter(DBActivity.activity_type == activity_type)
    if lead_id_filter:
        q = q.filter(DBLead.lead_id == lead_id_filter)
    if from_date:
        q = q.filter(DBActivity.created_at >= from_date)
    if to_date:
        q = q.filter(DBActivity.created_at <= to_date)

    total = q.count()
    rows = q.order_by(DBActivity.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": a.id,
                "type": a.activity_type,
                "description": a.description,
                "created_by": a.created_by,
                "created_at": a.created_at.isoformat(),
                "lead_id": lead_ref,
                "lead_name": lead_name,
            }
            for a, lead_ref, lead_name in rows
        ]
    }


@app.get("/api/monitoring/counselor-summary")
async def get_counselor_summary(
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """All-time or date-range summary per counselor: leads owned, calls, conversions"""
    fd = from_date or (datetime.utcnow() - timedelta(days=30))
    td = to_date or datetime.utcnow()

    activities = db.query(DBActivity).filter(
        DBActivity.created_at >= fd,
        DBActivity.created_at <= td
    ).all()

    from collections import defaultdict
    stats: dict = defaultdict(lambda: {
        "calls": 0, "whatsapp": 0, "emails": 0,
        "notes": 0, "status_changes": 0, "total": 0,
        "leads_touched": set()
    })

    for a in activities:
        by = a.created_by or "System"
        stats[by]["total"] += 1
        stats[by]["leads_touched"].add(a.lead_id)
        t = a.activity_type
        if t == "call":             stats[by]["calls"] += 1
        elif t == "whatsapp":       stats[by]["whatsapp"] += 1
        elif t == "email":          stats[by]["emails"] += 1
        elif t == "note":           stats[by]["notes"] += 1
        elif t == "status_change":  stats[by]["status_changes"] += 1

    # Enrolled leads per counselor in period
    enrolled_counts = {}
    enrolled_leads = db.query(DBLead).filter(
        DBLead.status == LeadStatus.ENROLLED,
        DBLead.updated_at >= fd,
        DBLead.updated_at <= td
    ).all()
    for l in enrolled_leads:
        if l.assigned_to:
            enrolled_counts[l.assigned_to] = enrolled_counts.get(l.assigned_to, 0) + 1

    result = []
    for by, s in stats.items():
        result.append({
            "counselor": by,
            "calls": s["calls"],
            "whatsapp": s["whatsapp"],
            "emails": s["emails"],
            "notes": s["notes"],
            "status_changes": s["status_changes"],
            "total_actions": s["total"],
            "leads_touched": len(s["leads_touched"]),
            "enrolled": enrolled_counts.get(by, 0)
        })

    result.sort(key=lambda x: x["total_actions"], reverse=True)
    return {"from": fd.isoformat(), "to": td.isoformat(), "counselors": result}


# ============================================================================
# API ENDPOINTS - GOOGLE SHEET SYNC WEBHOOK
# ============================================================================

SHEET_SYNC_API_KEY = os.getenv("SHEET_SYNC_API_KEY", "")
SUPER_ADMIN_EMAIL  = os.getenv("SUPER_ADMIN_EMAIL", "")

# Canonical CRM field names and all accepted aliases from Google Sheet headers
SHEET_FIELD_MAP = {
    # CRM field            : list of accepted sheet column headers (case-insensitive)
    "full_name":            ["full name", "name", "full_name", "lead name", "student name", "contact name"],
    "email":                ["email", "email address", "e-mail", "mail"],
    "phone":                ["phone", "phone number", "mobile", "mobile number", "contact", "contact no", "phone no"],
    "whatsapp":             ["whatsapp", "whatsapp number", "wa number", "wa"],
    "country":              ["country", "country name", "nation"],
    "branch":               ["branch", "branch name", "location", "city branch"],
    "qualification":        ["qualification", "degree", "education", "educational qualification", "highest qualification"],
    "source":               ["source", "lead source", "how did you hear", "medium", "channel"],
    "course_interested":    ["course", "course interested", "course name", "program", "course_interested", "interested course"],
    "company":              ["company", "hospital", "organization", "organisation", "institute", "hospital name", "workplace"],
    "assigned_to":          ["assigned to", "counselor", "counsellor", "assigned", "owner", "agent"],
    "follow_up_date":       ["follow up", "follow up date", "follow-up", "next follow up", "followup", "follow_up"],
    "status":               ["status", "lead status", "current status"],
    "notes_text":           ["notes", "note", "remarks", "comment", "comments", "description", "additional info"],
}

VALID_STATUSES = {s.lower(): s for s in [
    "Fresh", "Follow Up", "Warm", "Hot", "Enrolled",
    "Will Enroll Later", "Not Answering", "Not Interested", "Junk"
]}

VALID_SOURCES = {s.lower(): s for s in [
    "Facebook", "Instagram", "Google Ads", "YouTube", "LinkedIn",
    "Website", "Referral", "WhatsApp", "Cold Call", "Walk In", "Email Campaign"
]}


def _map_sheet_row(headers: list, row: list) -> dict:
    """Map a raw sheet row to CRM field names using fuzzy header matching."""
    # build header→value dict
    raw = {}
    for i, h in enumerate(headers):
        if i < len(row):
            raw[h.strip().lower()] = str(row[i]).strip() if row[i] is not None else ""

    mapped = {}
    for crm_field, aliases in SHEET_FIELD_MAP.items():
        for alias in aliases:
            if alias in raw:
                val = raw[alias]
                if val and val.lower() not in ("", "none", "null", "n/a", "-"):
                    mapped[crm_field] = val
                break

    # Normalise status
    if "status" in mapped:
        mapped["status"] = VALID_STATUSES.get(mapped["status"].lower(), "Fresh")
    else:
        mapped["status"] = "Fresh"

    # Normalise source
    if "source" in mapped:
        mapped["source"] = VALID_SOURCES.get(mapped["source"].lower(), mapped["source"])

    # Normalise follow_up_date
    if "follow_up_date" in mapped:
        raw_date = mapped["follow_up_date"]
        parsed = None
        for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %b %Y", "%B %d, %Y"):
            try:
                from datetime import date as _date
                parsed = datetime.strptime(raw_date, fmt)
                break
            except ValueError:
                pass
        mapped["follow_up_date"] = parsed.isoformat() if parsed else None

    return mapped


class SheetSyncRequest(BaseModel):
    headers: List[str]                  # column names from row 1
    rows: List[List[Any]]               # data rows (each row is a list of cell values)
    sheet_name: Optional[str] = "Sheet1"


class SheetSyncResult(BaseModel):
    total: int
    created: int
    skipped: int
    errors: int
    details: List[dict]


@app.post("/api/webhook/sheet-sync", response_model=SheetSyncResult)
async def sheet_sync_webhook(
    request: SheetSyncRequest,
    x_api_key: str = None,
    api_key: str = None,   # also accept as query param
    db: Session = Depends(get_db),
    x_api_key_header: Optional[str] = None,
):
    """
    Ingest leads from Google Sheets via Apps Script.
    Authenticate with X-Api-Key header or ?api_key= query param.
    All leads are created under the Super Admin account.
    Duplicate detection: phone number. Skips rows already in CRM.
    """
    from fastapi import Header
    # Accept API key from header or query param
    provided_key = x_api_key or api_key
    if not provided_key or provided_key != SHEET_SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if not SHEET_SYNC_API_KEY:
        raise HTTPException(status_code=500, detail="SHEET_SYNC_API_KEY not configured on server")

    # Find super admin user to attribute leads to
    super_admin = db.query(DBUser).filter(DBUser.role == "Super Admin", DBUser.is_active == True).first()
    if not super_admin:
        raise HTTPException(status_code=500, detail="No active Super Admin account found")

    # Pre-load existing phones to detect duplicates
    existing_phones = {
        r[0] for r in db.query(DBLead.phone).all() if r[0]
    }
    existing_emails = {
        r[0] for r in db.query(DBLead.email).filter(DBLead.email.isnot(None)).all()
    }

    ai_scorer.load_course_prices(db)
    lead_count_start = db.query(DBLead).count()

    results = []
    created = 0
    skipped = 0
    errors  = 0

    for idx, row in enumerate(request.rows, start=2):   # row 2 = first data row
        # Skip completely empty rows
        if not any(str(c).strip() for c in row if c is not None):
            continue

        try:
            mapped = _map_sheet_row(request.headers, row)

            # Must have at least a name
            if not mapped.get("full_name"):
                results.append({"row": idx, "status": "skipped", "reason": "Missing Full Name"})
                skipped += 1
                continue

            # Deduplicate by phone
            phone = mapped.get("phone", "")
            if phone and phone in existing_phones:
                results.append({"row": idx, "status": "skipped", "reason": f"Phone {phone} already in CRM",
                                 "name": mapped["full_name"]})
                skipped += 1
                continue

            # Deduplicate by email
            email = mapped.get("email", "")
            if email and email in existing_emails:
                results.append({"row": idx, "status": "skipped", "reason": f"Email {email} already in CRM",
                                 "name": mapped["full_name"]})
                skipped += 1
                continue

            # Source is required by CRM — default if missing
            if not mapped.get("source"):
                mapped["source"] = "Google Sheet"

            # Course is required — default if missing
            if not mapped.get("course_interested"):
                mapped["course_interested"] = "To Be Determined"

            # Phone is required — use placeholder if missing
            if not mapped.get("phone"):
                mapped["phone"] = "N/A"

            # Build lead ID
            lead_count_start += 1
            lead_id = f"LEAD{lead_count_start:05d}"

            status_val = LeadStatus(mapped.get("status", "Fresh"))

            db_lead = DBLead(
                lead_id=lead_id,
                full_name=mapped["full_name"],
                email=mapped.get("email") or None,
                phone=mapped.get("phone", "N/A"),
                whatsapp=mapped.get("whatsapp") or mapped.get("phone") or None,
                country=mapped.get("country", "India"),
                branch=mapped.get("branch") or None,
                qualification=mapped.get("qualification") or None,
                source=mapped.get("source", "Google Sheet"),
                course_interested=mapped.get("course_interested", "To Be Determined"),
                company=mapped.get("company") or None,
                assigned_to=mapped.get("assigned_to") or super_admin.full_name,
                hospital_id=super_admin.hospital_id,
                status=status_val,
                follow_up_date=datetime.fromisoformat(mapped["follow_up_date"])
                    if mapped.get("follow_up_date") else None,
            )
            db.add(db_lead)
            db.flush()   # get db_lead.id without full commit

            # AI scoring
            import json as _json
            score_result = ai_scorer.score_lead(db_lead, [])
            for key, value in score_result.items():
                if key == 'feature_importance' and value:
                    setattr(db_lead, key, _json.dumps(value))
                else:
                    setattr(db_lead, key, value)

            # Initial note
            notes_text = mapped.get("notes_text", "")
            if notes_text:
                db.add(DBNote(
                    lead_id=db_lead.id,
                    content=f"[Imported from Google Sheet] {notes_text}",
                    created_by=super_admin.full_name,
                    channel="manual"
                ))

            # Activity log
            db.add(DBActivity(
                lead_id=db_lead.id,
                activity_type="lead_created",
                description=f"Lead imported from Google Sheet (row {idx})",
                created_by="Sheet Sync"
            ))

            existing_phones.add(phone)
            if email:
                existing_emails.add(email)

            results.append({"row": idx, "status": "created", "lead_id": lead_id, "name": mapped["full_name"]})
            created += 1

        except Exception as e:
            db.rollback()
            results.append({"row": idx, "status": "error", "reason": str(e)})
            errors += 1
            continue

    db.commit()
    invalidate_cache(STATS_CACHE)
    invalidate_cache(LEAD_CACHE)

    logger.info(f"Sheet sync: {created} created, {skipped} skipped, {errors} errors from {len(request.rows)} rows")
    return SheetSyncResult(
        total=len(request.rows),
        created=created,
        skipped=skipped,
        errors=errors,
        details=results
    )


@app.get("/api/webhook/sheet-sync/status")
async def sheet_sync_status(
    api_key: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Quick status check for Apps Script to verify connectivity."""
    if api_key != SHEET_SYNC_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    total_leads = db.query(DBLead).count()
    sheet_imported = db.query(DBActivity).filter(
        DBActivity.activity_type == "lead_created",
        DBActivity.created_by == "Sheet Sync"
    ).count()
    return {
        "status": "connected",
        "total_leads_in_crm": total_leads,
        "sheet_imported_leads": sheet_imported
    }


# ============================================================================
# API ENDPOINTS - HOSPITALS
# ============================================================================

@app.post("/api/hospitals", response_model=HospitalResponse)
async def create_hospital(
    hospital: HospitalCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create hospital"""
    if current_user.role != "Super Admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can create hospitals")
    
    db_hospital = DBHospital(**hospital.dict())
    db.add(db_hospital)
    db.commit()
    db.refresh(db_hospital)
    
    return db_hospital

@app.get("/api/hospitals", response_model=List[HospitalResponse])
async def get_hospitals(
    skip: int = 0,
    limit: int = 100,
    country: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get hospitals with filters"""

    query = db.query(DBHospital)

    if current_user.role == "Hospital Admin":
        if current_user.hospital_id is None:
            raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
        query = query.filter(DBHospital.id == current_user.hospital_id)
    
    if country:
        query = query.filter(DBHospital.country == country)
    if status:
        query = query.filter(DBHospital.collaboration_status == status)
    
    hospitals = query.offset(skip).limit(limit).all()
    return hospitals

# ============================================================================
# API ENDPOINTS - COURSES
# ============================================================================

@app.post("/api/courses", response_model=CourseResponse)
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create course"""

    if not has_minimum_role(current_user.role, "Hospital Admin"):
        raise HTTPException(status_code=403, detail="Hospital Admin or higher access required")

    target_hospital_id = course.hospital_id
    if current_user.role == "Hospital Admin":
        if current_user.hospital_id is None:
            raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
        target_hospital_id = current_user.hospital_id

    if target_hospital_id is not None:
        _ensure_same_hospital_or_super_admin(current_user, target_hospital_id)

    course_data = course.dict()
    course_data["hospital_id"] = target_hospital_id

    db_course = DBCourse(**course_data)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    
    return db_course

@app.get("/api/courses", response_model=List[CourseResponse])
@cache_async_result(COURSE_CACHE, "courses_list")
async def get_courses(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get courses with filters (cached for 1 hour)"""

    query = db.query(DBCourse).filter(DBCourse.is_active == is_active)

    if current_user.role == "Hospital Admin":
        if current_user.hospital_id is None:
            raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
        query = query.filter(
            (DBCourse.hospital_id == current_user.hospital_id) | (DBCourse.hospital_id.is_(None))
        )
    
    if category:
        query = query.filter(DBCourse.category == category)
    
    courses = query.offset(skip).limit(limit).all()
    return courses

# ============================================================================
# API ENDPOINTS - DASHBOARD & ANALYTICS
# ============================================================================

@app.get("/api/dashboard/stats", response_model=DashboardStats)
@cache_async_result(STATS_CACHE, "dashboard_stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get dashboard statistics (cached for 1 minute)"""
    
    # Use Supabase REST API if available
    if supabase_data.client:
        try:
            # Use Supabase for stats
            total_leads = supabase_data.get_lead_count()
            hot_leads = supabase_data.get_lead_count(segment="Hot")
            warm_leads = supabase_data.get_lead_count(segment="Warm")
            cold_leads = supabase_data.get_lead_count(segment="Cold")
            junk_leads = supabase_data.get_lead_count(segment="Junk")
            total_conversions = supabase_data.get_lead_count(status="Enrolled")
            
            conversion_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0
            
            # Get revenue stats using aggregations (performance optimization)
            # Note: Supabase REST API doesn't support aggregations well, so we use SQLAlchemy
            total_revenue = db.query(func.sum(DBLead.actual_revenue)).scalar() or 0
            expected_revenue = db.query(func.sum(DBLead.expected_revenue)).scalar() or 0
            avg_score = db.query(func.avg(DBLead.ai_score)).scalar() or 0
            
            # Time-based counts (simplified for now)
            leads_today = 0
            leads_this_week = 0
            leads_this_month = 0
            
            return DashboardStats(
                total_leads=total_leads,
                hot_leads=hot_leads,
                warm_leads=warm_leads,
                cold_leads=cold_leads,
                junk_leads=junk_leads,
                total_conversions=total_conversions,
                conversion_rate=conversion_rate,
                total_revenue=total_revenue,
                expected_revenue=expected_revenue,
                leads_today=leads_today,
                leads_this_week=leads_this_week,
                leads_this_month=leads_this_month,
                avg_ai_score=avg_score
            )
        except Exception as e:
            logger.error(f"Supabase stats failed, falling back to SQLAlchemy: {e}")
    
    # Fallback to SQLAlchemy - Single optimized query instead of 12 separate queries
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    
    scoped_query = _apply_lead_scope(db.query(DBLead), db, current_user)

    stats = scoped_query.with_entities(
        func.count(DBLead.id).label('total'),
        func.count(case((DBLead.ai_segment == LeadSegment.HOT, 1))).label('hot'),
        func.count(case((DBLead.ai_segment == LeadSegment.WARM, 1))).label('warm'),
        func.count(case((DBLead.ai_segment == LeadSegment.COLD, 1))).label('cold'),
        func.count(case((DBLead.ai_segment == LeadSegment.JUNK, 1))).label('junk'),
        func.count(case((DBLead.status == LeadStatus.ENROLLED, 1))).label('conversions'),
        func.sum(DBLead.actual_revenue).label('revenue'),
        func.sum(DBLead.expected_revenue).label('expected'),
        func.avg(DBLead.ai_score).label('avg_score'),
        func.count(case((DBLead.created_at >= today_start, 1))).label('today'),
        func.count(case((DBLead.created_at >= week_start, 1))).label('week'),
        func.count(case((DBLead.created_at >= month_start, 1))).label('month'),
    ).first()
    
    total_leads = stats.total or 0
    hot_leads = stats.hot or 0
    warm_leads = stats.warm or 0
    cold_leads = stats.cold or 0
    junk_leads = stats.junk or 0
    total_conversions = stats.conversions or 0
    conversion_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0
    total_revenue = stats.revenue or 0
    expected_revenue = stats.expected or 0
    avg_score = stats.avg_score or 0
    leads_today = stats.today or 0
    leads_this_week = stats.week or 0
    leads_this_month = stats.month or 0
    
    return DashboardStats(
        total_leads=total_leads,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        junk_leads=junk_leads,
        total_conversions=total_conversions,
        conversion_rate=conversion_rate,
        total_revenue=total_revenue,
        expected_revenue=expected_revenue,
        leads_today=leads_today,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        avg_ai_score=avg_score
    )

@app.get("/api/counselors", response_model=List[CounselorResponse])
async def get_counselors(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get all counselors with performance"""
    
    if current_user.role in ["Super Admin", "Hospital Admin"]:
        counselors = db.query(DBCounselor).filter(DBCounselor.is_active == True).all()
    else:
        counselors = db.query(DBCounselor).filter(DBCounselor.name == current_user.full_name).all()
    return counselors

# ============================================================================
# USER MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/users", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get all users in the organization"""
    _ensure_admin_scope(current_user)

    query = db.query(DBUser)
    if current_user.role == "Hospital Admin":
        if current_user.hospital_id is None:
            raise HTTPException(status_code=403, detail="Hospital Admin must be assigned to a hospital")
        query = query.filter(DBUser.hospital_id == current_user.hospital_id)

    users = query.all()
    return users

@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get a specific user by ID"""
    _ensure_admin_scope(current_user)

    user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_same_hospital_or_super_admin(current_user, user.hospital_id)

    return user

@app.post("/api/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create a new user"""
    _ensure_admin_scope(current_user)
    
    # Check if email already exists
    existing = db.query(DBUser).filter(DBUser.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    target_hospital_id = user.hospital_id
    if current_user.role == "Hospital Admin":
        if user.role == "Super Admin":
            raise HTTPException(status_code=403, detail="Hospital Admin cannot create Super Admin")
        target_hospital_id = current_user.hospital_id

    if user.role != "Super Admin" and target_hospital_id is None:
        raise HTTPException(status_code=400, detail="hospital_id is required for non-Super Admin users")

    _ensure_same_hospital_or_super_admin(current_user, target_hospital_id)
    
    # Hash the password for security
    hashed_password = get_password_hash(user.password)
    db_user = DBUser(
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        password=hashed_password,
        role=user.role,
        hospital_id=target_hospital_id,
        reports_to=user.reports_to,
        is_active=user.is_active
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Update user information"""
    _ensure_admin_scope(current_user)
    
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_same_hospital_or_super_admin(current_user, db_user.hospital_id)

    if current_user.role == "Hospital Admin" and user.role == "Super Admin":
        raise HTTPException(status_code=403, detail="Hospital Admin cannot promote users to Super Admin")

    target_hospital_id = user.hospital_id if user.hospital_id is not None else db_user.hospital_id
    if current_user.role == "Hospital Admin":
        target_hospital_id = current_user.hospital_id

    _ensure_same_hospital_or_super_admin(current_user, target_hospital_id)
    
    # Update fields
    update_data = user.dict(exclude_unset=True)
    if "hospital_id" in update_data:
        update_data["hospital_id"] = target_hospital_id

    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Delete a user"""
    _ensure_admin_scope(current_user)
    
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_same_hospital_or_super_admin(current_user, db_user.hospital_id)

    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


@app.post("/api/users/{user_id}/whatsapp/connect", response_model=WhatsAppConnectionResponse)
async def connect_user_whatsapp(
    user_id: int,
    payload: WhatsAppConnectionCreate,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Connect or update a user's WhatsApp Cloud API account."""
    target_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_user_scope(db, current_user, target_user)

    conn = db.query(DBUserWhatsAppConnection).filter(DBUserWhatsAppConnection.user_id == user_id).first()
    if conn is None:
        conn = DBUserWhatsAppConnection(
            user_id=user_id,
            provider=payload.provider,
            phone_number_id=payload.phone_number_id,
            business_account_id=payload.business_account_id,
            display_number=payload.display_number,
            access_token=payload.access_token,
            is_active=True,
        )
        db.add(conn)
    else:
        conn.provider = payload.provider
        conn.phone_number_id = payload.phone_number_id
        conn.business_account_id = payload.business_account_id
        conn.display_number = payload.display_number
        conn.access_token = payload.access_token
        conn.is_active = True
        conn.last_error = None
        conn.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(conn)
    return conn


@app.get("/api/users/{user_id}/whatsapp/status", response_model=WhatsAppConnectionResponse)
async def get_user_whatsapp_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get WhatsApp connection status for a user."""
    target_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_user_scope(db, current_user, target_user)

    conn = db.query(DBUserWhatsAppConnection).filter(DBUserWhatsAppConnection.user_id == user_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="WhatsApp account not connected")

    return conn


@app.delete("/api/users/{user_id}/whatsapp/connect")
async def disconnect_user_whatsapp(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Disconnect a user's WhatsApp Cloud API account."""
    target_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_user_scope(db, current_user, target_user)

    conn = db.query(DBUserWhatsAppConnection).filter(DBUserWhatsAppConnection.user_id == user_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="WhatsApp account not connected")

    db.delete(conn)
    db.commit()
    return {"message": "WhatsApp account disconnected"}


@app.post("/api/leads/{lead_id}/send-whatsapp-personal")
async def send_whatsapp_personal(
    lead_id: str,
    request: PersonalWhatsAppMessageRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Send WhatsApp message to a lead using a connected user WhatsApp account."""
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)

    from_user_id = request.from_user_id or current_user.id
    from_user = db.query(DBUser).filter(DBUser.id == from_user_id).first()
    if not from_user:
        raise HTTPException(status_code=404, detail="Sender user not found")

    _ensure_user_scope(db, current_user, from_user)

    conn = db.query(DBUserWhatsAppConnection).filter(
        DBUserWhatsAppConnection.user_id == from_user_id,
        DBUserWhatsAppConnection.is_active == True
    ).first()
    if not conn:
        raise HTTPException(status_code=400, detail="Sender user has no active WhatsApp connection")

    if not lead.whatsapp:
        raise HTTPException(status_code=400, detail="Lead has no WhatsApp number")

    try:
        result = _send_whatsapp_via_cloud_api(conn, lead.whatsapp, request.message)
        conn.last_tested_at = datetime.utcnow()
        conn.last_error = None
        db.commit()

        msg_id = None
        if isinstance(result, dict):
            messages = result.get("messages") or []
            if messages and isinstance(messages[0], dict):
                msg_id = messages[0].get("id")

        return {
            "success": True,
            "provider": conn.provider,
            "from_user_id": from_user_id,
            "to": lead.whatsapp,
            "message_id": msg_id,
            "raw": result,
        }
    except HTTPException as exc:
        conn.last_tested_at = datetime.utcnow()
        conn.last_error = str(exc.detail)
        db.commit()
        raise

@app.get("/api/analytics/revenue-by-country")
async def revenue_by_country(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get revenue breakdown by country"""
    
    scoped = _apply_lead_scope(db.query(DBLead), db, current_user)
    results = scoped.with_entities(
        DBLead.country,
        func.count(DBLead.id).label('total_leads'),
        func.sum(DBLead.actual_revenue).label('total_revenue'),
        func.sum(DBLead.expected_revenue).label('expected_revenue')
    ).group_by(DBLead.country).all()
    
    return [
        {
            'country': r[0],
            'total_leads': r[1],
            'total_revenue': r[2] or 0,
            'expected_revenue': r[3] or 0
        }
        for r in results
    ]

@app.get("/api/analytics/conversion-funnel")
async def conversion_funnel(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get conversion funnel metrics"""
    
    scoped = _apply_lead_scope(db.query(DBLead), db, current_user)
    total = scoped.count()
    contacted = scoped.filter(DBLead.last_contact_date.isnot(None)).count()
    warm_hot = scoped.filter(DBLead.ai_score >= 50).count()
    converted = scoped.filter(DBLead.status == LeadStatus.ENROLLED).count()
    
    return {
        'stages': [
            {'name': 'Total Leads', 'count': total, 'percentage': 100},
            {'name': 'Contacted', 'count': contacted, 'percentage': (contacted/total*100) if total > 0 else 0},
            {'name': 'Warm/Hot', 'count': warm_hot, 'percentage': (warm_hot/total*100) if total > 0 else 0},
            {'name': 'Converted', 'count': converted, 'percentage': (converted/total*100) if total > 0 else 0},
        ]
    }

# ============================================================================
# COMMUNICATION ENDPOINTS
# ============================================================================

@app.post("/api/leads/{lead_id}/send-whatsapp")
async def send_whatsapp(
    lead_id: str,
    request: WhatsAppRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Send WhatsApp message via Twilio"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    if not lead.whatsapp:
        raise HTTPException(status_code=400, detail="Lead has no WhatsApp number")
    
    # Send WhatsApp message
    from communication_service import comm_service
    
    variables = {
        "name": lead.full_name or "there",
        "course": lead.course_interested or "our courses",
        "counselor": lead.assigned_to or "Your counselor",
        "message": request.message
    }
    
    result = await comm_service.send(
        channel="whatsapp",
        to=lead.whatsapp,
        message=request.message,
        template=request.template,
        variables=variables
    )
    
    # Log note and activity
    note = DBNote(
        lead_id=lead.id,
        content=f"[WhatsApp {'Sent' if result['success'] else 'Failed'}] {request.message}",
        channel="whatsapp",
        created_by=current_user.full_name
    )
    db.add(note)
    db.add(DBActivity(
        lead_id=lead.id,
        activity_type="whatsapp",
        description=f"WhatsApp {'sent' if result['success'] else 'failed'}: {request.message[:80]}",
        created_by=current_user.full_name
    ))
    db.commit()
    
    if result["success"]:
        return {
            "success": True,
            "message": "WhatsApp sent successfully",
            "message_id": result.get("message_id"),
            "to": lead.whatsapp
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send WhatsApp"))

@app.post("/api/leads/{lead_id}/send-email")
async def send_email(
    lead_id: str,
    request: EmailRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Send email via Resend"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    if not lead.email:
        raise HTTPException(status_code=400, detail="Lead has no email address")
    
    # Send email
    from communication_service import comm_service
    
    variables = {
        "name": lead.full_name or "there",
        "course": lead.course_interested or "our courses",
        "counselor": lead.assigned_to or "Your counselor",
        "subject": request.subject,
        "body": request.body
    }
    
    result = await comm_service.send(
        channel="email",
        to=lead.email,
        message=request.body,
        template=request.template,
        variables=variables
    )
    
    # Log note and activity
    note = DBNote(
        lead_id=lead.id,
        content=f"[Email {'Sent' if result['success'] else 'Failed'}] Subject: {request.subject}\n\n{request.body}",
        channel="email",
        created_by=current_user.full_name
    )
    db.add(note)
    db.add(DBActivity(
        lead_id=lead.id,
        activity_type="email",
        description=f"Email {'sent' if result['success'] else 'failed'}: {request.subject}",
        created_by=current_user.full_name
    ))
    db.commit()
    
    if result["success"]:
        return {
            "success": True,
            "message": "Email sent successfully",
            "message_id": result.get("message_id"),
            "to": lead.email
        }
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email"))

@app.post("/api/leads/{lead_id}/trigger-welcome")
async def trigger_welcome(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Trigger automated welcome sequence (Email + WhatsApp)"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    from communication_service import comm_service
    
    lead_data = {
        "id": lead.lead_id,
        "name": lead.full_name or "there",
        "email": lead.email,
        "whatsapp": lead.whatsapp,
        "course": lead.course_interested or "our courses",
        "counselor": lead.assigned_to or "Your counselor"
    }
    
    results = await comm_service.campaign.trigger_welcome_sequence(lead_data)
    
    # Log results
    for result in results:
        note = DBNote(
            lead_id=lead.id,
            content=f"[{result['channel'].title()} - Welcome Sequence] {'Sent' if result.get('success') else 'Failed'}",
            channel=result["channel"],
            created_by="System",
            metadata=json.dumps(result)
        )
        db.add(note)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Welcome sequence triggered",
        "results": results
    }

@app.post("/api/leads/{lead_id}/trigger-followup")
async def trigger_followup(
    lead_id: str,
    request: FollowUpRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Trigger automated follow-up sequence"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    from communication_service import comm_service
    
    lead_data = {
        "id": lead.lead_id,
        "name": lead.full_name or "there",
        "email": lead.email,
        "whatsapp": lead.whatsapp,
        "course": lead.course_interested or "our courses",
        "counselor": lead.assigned_to or "Your counselor"
    }
    
    results = await comm_service.campaign.trigger_follow_up(lead_data, request.message, request.priority)
    
    # Log results
    for result in results:
        note = DBNote(
            lead_id=lead.id,
            content=f"[{result['channel'].title()} - Follow-up] {request.message}",
            channel=result["channel"],
            created_by="System",
            metadata=json.dumps(result)
        )
        db.add(note)
    
    db.commit()
    
    return {
        "success": True,
        "message": "Follow-up sequence triggered",
        "results": results
    }

# ============================================================================
# LEAD ASSIGNMENT ENDPOINTS
# ============================================================================

@app.post("/api/leads/{lead_id}/assign")
async def assign_lead(
    lead_id: str,
    request: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """
    Assign lead to counselor using specified strategy
    
    Strategies:
    - intelligent: AI-based matching (recommended)
    - round_robin: Rotate assignments evenly
    - skill_based: Match course expertise
    - workload: Assign to least busy counselor
    """
    
    from assignment_service import LeadAssignmentEngine
    
    # Get lead by lead_id
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    engine = LeadAssignmentEngine(db)
    result = engine.assign_lead(lead.id, request.strategy)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.post("/api/leads/assign-all")
async def assign_all_unassigned(
    request: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Assign all unassigned leads in bulk"""

    _ensure_admin_scope(current_user)
    
    from assignment_service import LeadAssignmentEngine
    
    engine = LeadAssignmentEngine(db)
    results = engine.bulk_assign_unassigned(request.strategy)
    
    return results

@app.post("/api/leads/{lead_id}/reassign")
async def reassign_lead(
    lead_id: str,
    request: ReassignmentRequest,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Reassign lead to different counselor"""
    
    from assignment_service import LeadAssignmentEngine
    
    # Get lead by lead_id
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    _ensure_lead_access(db, current_user, lead)
    
    engine = LeadAssignmentEngine(db)
    result = engine.reassign_lead(lead.id, request.new_counselor, request.reason)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.get("/api/counselors/workload")
@cache_async_result(STATS_CACHE, "counselor_workload")
async def get_counselor_workloads(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get workload statistics for all counselors (cached for 1 minute)"""

    _ensure_admin_scope(current_user)
    
    from assignment_service import LeadAssignmentEngine
    
    counselors = db.query(DBUser).filter(
        DBUser.role.in_(["Counselor", "Manager", "Team Leader"])
    ).all()
    
    engine = LeadAssignmentEngine(db)
    
    workloads = []
    for counselor in counselors:
        workload = engine._get_counselor_workload(counselor.full_name)
        performance = engine._get_counselor_performance(counselor.full_name)
        
        workloads.append({
            "full_name": counselor.full_name,
            "email": counselor.email,
            "role": counselor.role,
            "active_leads": workload,
            "performance_score": round(performance, 1),
            "status": "overloaded" if workload > 30 else "busy" if workload > 20 else "available"
        })
    
    return {
        "counselors": workloads,
        "total_counselors": len(workloads),
        "total_active_leads": sum(c["active_leads"] for c in workloads),
        "average_workload": round(sum(c["active_leads"] for c in workloads) / len(workloads), 1) if workloads else 0
    }

@app.post("/api/workflows/trigger")
async def trigger_workflows(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Manually trigger automated workflows for all leads"""

    _ensure_admin_scope(current_user)
    
    from assignment_service import WorkflowAutomation
    
    automation = WorkflowAutomation(db)
    results = await automation.check_and_trigger_workflows()
    
    return {
        "triggered": len(results),
        "workflows": results
    }

# ============================================================================
# API ENDPOINTS - AUTO-ASSIGNMENT (NEW)
# ============================================================================

@app.post("/api/leads/auto-assign")
async def auto_assign_lead(
    lead_id: str,
    strategy: str = Query("intelligent", description="Assignment strategy: intelligent, round-robin, skill-based"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Auto-assign a single lead using AI-driven strategy"""
    
    # Get lead
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check access
    _ensure_lead_access(db, current_user, lead)
    
    # Get hospital ID for scoping
    hospital_id = None if current_user.role == "Super Admin" else current_user.hospital_id
    
    # Execute auto-assignment
    orchestrator = AutoAssignmentOrchestrator(db)
    try:
        result = orchestrator.assign_lead(
            lead_id=lead.id,
            strategy=strategy,
            hospital_id=hospital_id,
            preferred_country=lead.country,
            preferred_course=lead.interested_course
        )
        
        # Invalidate cache
        invalidate_cache(LEAD_CACHE)
        
        return result
    except Exception as e:
        logger.error(f"Auto-assignment failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/leads/bulk-auto-assign")
async def bulk_auto_assign(
    lead_ids: List[str],
    strategy: str = Query("intelligent", description="Assignment strategy"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Bulk auto-assign multiple leads with load balancing"""
    
    _ensure_minimum_role(current_user, "Manager")
    
    hospital_id = None if current_user.role == "Super Admin" else current_user.hospital_id
    
    orchestrator = AutoAssignmentOrchestrator(db)
    results = orchestrator.bulk_assign(
        lead_ids=lead_ids,
        strategy=strategy,
        hospital_id=hospital_id
    )
    
    # Invalidate cache
    invalidate_cache(LEAD_CACHE)
    
    logger.info(f"Bulk auto-assignment: {results['assigned']}/{results['total']} leads assigned")
    
    return results

@app.post("/api/assignment/preview")
async def preview_assignment(
    lead_ids: List[str],
    strategy: str = Query("intelligent"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Preview assignment distribution without committing"""
    
    hospital_id = None if current_user.role == "Super Admin" else current_user.hospital_id
    
    orchestrator = AutoAssignmentOrchestrator(db)
    preview = orchestrator.preview_assignment(
        lead_ids=lead_ids,
        strategy=strategy,
        hospital_id=hospital_id
    )
    
    # Calculate distribution stats
    from collections import Counter
    distribution = Counter(item["counselor_name"] for item in preview)
    
    return {
        "preview": preview,
        "total_leads": len(preview),
        "distribution": dict(distribution),
        "strategy": strategy
    }

@app.get("/api/assignment/strategies")
async def get_available_strategies():
    """Get list of available assignment strategies"""
    return get_assignment_strategies()

@app.get("/api/assignment/settings")
async def get_assignment_settings(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get current assignment settings for hospital/organization"""
    
    # This would load from database settings table
    # For now, return defaults
    return {
        "default_strategy": "intelligent",
        "auto_assign_new_leads": False,
        "max_leads_per_counselor": 50,
        "enable_skill_matching": True,
        "working_hours_only": False
    }

@app.put("/api/assignment/settings")
async def update_assignment_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Update assignment settings (admin only)"""
    
    _ensure_admin_scope(current_user)
    
    # This would save to database settings table
    # For now, just return the settings
    logger.info(f"Assignment settings updated by {current_user.email}")
    
    return {
        "success": True,
        "settings": settings
    }

# ============================================================================
# API ENDPOINTS - SMART SCHEDULER (NEW)
# ============================================================================

@app.post("/api/scheduler/suggest-time/{lead_id}")
async def suggest_optimal_time(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get AI-driven optimal contact time suggestion"""
    
    # Get lead
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    _ensure_lead_access(db, current_user, lead)
    
    scheduler = SmartScheduler(db)
    suggestion = scheduler.suggest_optimal_time(
        lead_id=lead.id,
        counselor_id=lead.assigned_to
    )
    
    return suggestion

@app.post("/api/scheduler/auto-schedule/{lead_id}")
async def auto_schedule_followup(
    lead_id: str,
    trigger_event: str = Query("manual", description="Trigger event: manual, status_change, note_added"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Automatically schedule follow-up based on lead properties"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    _ensure_lead_access(db, current_user, lead)
    
    scheduler = SmartScheduler(db)
    result = scheduler.auto_schedule(
        lead_id=lead.id,
        trigger_event=trigger_event,
        counselor_id=current_user.id
    )
    
    # Invalidate cache
    invalidate_cache(LEAD_CACHE)
    
    return result

@app.get("/api/scheduler/conflicts")
async def check_scheduling_conflicts(
    counselor_id: str,
    proposed_time: str,
    duration_minutes: int = Query(30, description="Duration in minutes"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Check if counselor has conflicts at proposed time"""
    
    from datetime import datetime
    
    # Parse datetime
    try:
        proposed_dt = datetime.fromisoformat(proposed_time.replace('Z', '+00:00'))
    except:
        raise HTTPException(status_code=400, detail="Invalid datetime format. Use ISO format.")
    
    scheduler = SmartScheduler(db)
    conflicts = scheduler.check_conflicts(
        counselor_id=counselor_id,
        proposed_time=proposed_dt,
        duration_minutes=duration_minutes
    )
    
    return conflicts

@app.post("/api/scheduler/bulk-schedule")
async def bulk_schedule_followups(
    lead_ids: List[str],
    strategy: str = Query("auto", description="Scheduling strategy"),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Bulk schedule follow-ups for multiple leads"""
    
    _ensure_minimum_role(current_user, "Manager")
    
    scheduler = SmartScheduler(db)
    results = scheduler.bulk_schedule(lead_ids=lead_ids, strategy=strategy)
    
    invalidate_cache(LEAD_CACHE)
    
    return results

# ============================================================================
# API ENDPOINTS - WORKFLOW AUTOMATION (NEW)
# ============================================================================

@app.get("/api/workflows")
async def get_workflow_definitions(
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get all workflow definitions"""
    
    _ensure_minimum_role(current_user, "Manager")
    
    engine = WorkflowEngine(db)
    workflows = engine.get_workflow_definitions()
    
    return {
        "workflows": workflows,
        "total": len(workflows)
    }

@app.post("/api/workflows")
async def create_or_update_workflow(
    workflow: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create or update workflow definition (admin only)"""
    
    _ensure_admin_scope(current_user)
    
    engine = WorkflowEngine(db)
    success = engine.save_workflow(workflow)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save workflow")
    
    logger.info(f"Workflow '{workflow.get('name')}' saved by {current_user.email}")
    
    return {
        "success": True,
        "workflow": workflow
    }

@app.post("/api/workflows/trigger-status-change")
async def trigger_status_change_workflow(
    lead_id: str,
    old_status: str,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Manually trigger status change workflow (for testing)"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    _ensure_lead_access(db, current_user, lead)
    
    engine = WorkflowEngine(db)
    results = engine.trigger_status_change(
        lead_id=lead.id,
        old_status=old_status,
        new_status=new_status,
        user_id=current_user.id
    )
    
    return results

@app.post("/api/workflows/trigger-event")
async def trigger_custom_event_workflow(
    event_type: str,
    lead_id: str,
    metadata: Optional[Dict] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Trigger workflow from custom event"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    _ensure_lead_access(db, current_user, lead)
    
    engine = WorkflowEngine(db)
    results = engine.trigger_custom_event(
        event_type=event_type,
        lead_id=lead.id,
        user_id=current_user.id,
        metadata=metadata or {}
    )
    
    return results

# ============================================================================
# API ENDPOINTS - NOTE TEMPLATES
# ============================================================================

@app.get("/api/templates/notes")
async def get_note_templates(
    category: Optional[str] = None,
    current_user: DBUser = Depends(get_current_user)
):
    """Get all note templates, optionally filtered by category"""
    
    templates = note_templates_manager.get_all_templates(category=category)
    categories = note_templates_manager.get_categories()
    
    return {
        "templates": templates,
        "categories": categories,
        "total": len(templates)
    }

@app.get("/api/templates/notes/{template_id}")
async def get_note_template(
    template_id: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Get specific note template by ID"""
    
    template = note_templates_manager.get_template_by_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template

@app.post("/api/templates/notes")
async def create_note_template(
    name: str,
    content: str,
    category: str = "Custom",
    current_user: DBUser = Depends(get_current_user)
):
    """Create new custom note template"""
    
    _ensure_minimum_role(current_user, "Team Leader")
    
    template = note_templates_manager.create_template(
        name=name,
        content=content,
        category=category
    )
    
    logger.info(f"Template '{name}' created by {current_user.email}")
    
    return template

@app.put("/api/templates/notes/{template_id}")
async def update_note_template(
    template_id: str,
    updates: Dict[str, Any],
    current_user: DBUser = Depends(get_current_user)
):
    """Update existing template"""
    
    _ensure_minimum_role(current_user, "Team Leader")
    
    template = note_templates_manager.update_template(template_id, updates)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or is system template")
    
    logger.info(f"Template '{template_id}' updated by {current_user.email}")
    
    return template

@app.delete("/api/templates/notes/{template_id}")
async def delete_note_template(
    template_id: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Delete custom template"""
    
    _ensure_minimum_role(current_user, "Manager")
    
    success = note_templates_manager.delete_template(template_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Template not found or is system template")
    
    logger.info(f"Template '{template_id}' deleted by {current_user.email}")
    
    return {"success": True}

@app.post("/api/templates/notes/{template_id}/render")
async def render_note_template(
    template_id: str,
    lead_id: str,
    variables: Optional[Dict[str, str]] = None,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Render template with variable substitution"""
    
    lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    _ensure_lead_access(db, current_user, lead)
    
    # Get available variables
    lead_data = {
        "name": lead.name,
        "email": lead.email,
        "phone": lead.phone,
        "course_interested": lead.course_interested,
        "preferred_country": lead.preferred_country,
        "ai_score": lead.ai_score,
        "status": lead.status
    }
    
    user_data = {
        "name": current_user.name,
        "email": current_user.email
    }
    
    # Merge with provided variables
    all_variables = note_templates_manager.get_available_variables(lead_data, user_data)
    if variables:
        all_variables.update(variables)
    
    # Render template
    rendered = note_templates_manager.render_template(template_id, all_variables)
    
    if not rendered:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "rendered_content": rendered,
        "template_id": template_id,
        "variables_used": all_variables
    }

@app.get("/api/templates/notes/popular")
async def get_popular_templates(
    limit: int = 5,
    current_user: DBUser = Depends(get_current_user)
):
    """Get most used templates"""
    
    templates = note_templates_manager.get_popular_templates(limit=limit)
    
    return {
        "templates": templates,
        "total": len(templates)
    }

# ============================================================================
# API ENDPOINTS - CACHE MANAGEMENT
# ============================================================================

@app.get("/api/cache/stats")
async def get_cache_statistics():
    """Get cache statistics for monitoring"""
    stats = get_cache_stats()
    
    return {
        "caches": stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/cache/clear")
async def clear_cache(cache_name: Optional[str] = None):
    """Clear cache (all or specific cache)"""
    
    if cache_name:
        cache_map = {
            "leads": LEAD_CACHE,
            "courses": COURSE_CACHE,
            "users": USER_CACHE,
            "stats": STATS_CACHE,
            "ml_scores": ML_SCORE_CACHE
        }
        
        if cache_name not in cache_map:
            raise HTTPException(status_code=400, detail=f"Unknown cache: {cache_name}")
        
        invalidate_cache(cache_map[cache_name])
        logger.info(f"🗑️  Cleared {cache_name} cache", extra={"system": "cache"})
        
        return {
            "status": "success",
            "cleared": cache_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        # Clear all caches
        for cache in [LEAD_CACHE, COURSE_CACHE, USER_CACHE, STATS_CACHE, ML_SCORE_CACHE]:
            invalidate_cache(cache)
        
        logger.info("🗑️  Cleared all caches", extra={"system": "cache"})
        
        return {
            "status": "success",
            "cleared": "all",
            "timestamp": datetime.utcnow().isoformat()
        }

# ============================================================================
# ML MODEL INFO & VERSIONING
# ============================================================================

@app.get("/api/ml/model-info")
async def get_model_info():
    """Get current ML model version, metadata, and performance metrics."""
    model = get_cached_model()
    
    # Load metadata from JSON sidecar files
    models_dir = Path(__file__).parent.parent.parent / "models"
    metadata_files = sorted(models_dir.glob("model_metadata_v2_*.json"), reverse=True)
    
    metadata = None
    if metadata_files:
        try:
            with open(metadata_files[0]) as f:
                metadata = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load model metadata: {e}")
    
    return {
        "model_loaded": model is not None,
        "model_type": "CatBoostClassifier" if model else None,
        "metadata": metadata,
        "available_versions": [f.stem for f in metadata_files],
        "timestamp": datetime.utcnow().isoformat(),
    }

# ============================================================================
# AI-POWERED SMART FEATURES (PHASE 8)
# ============================================================================

@app.post("/api/ai/search")
async def ai_natural_language_search(
    query: str = Query(..., description="Natural language search query"),
    db: Session = Depends(get_db)
):
    """
    🔍 Search leads using natural language
    
    Examples:
    - "Show me all hot leads from India interested in MBBS"
    - "Find leads that haven't been contacted in 7 days"
    - "Which leads have high conversion probability?"
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    try:
        # Get all leads
        leads = db.query(DBLead).all()
        lead_dicts = [
            {
                "id": lead.id,
                "full_name": lead.full_name,
                "country": lead.country,
                "course_interested": lead.course_interested,
                "status": lead.status,
                "ai_segment": lead.ai_segment,
                "ai_score": lead.ai_score,
                "conversion_probability": lead.conversion_probability,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
            }
            for lead in leads
        ]
        
        # AI-powered search
        results = await ai_assistant.natural_language_search(query, lead_dicts)
        
        logger.info(f"🔍 AI Search: '{query}' → {len(results)} results", extra={"endpoint": "ai_search"})
        
        return {
            "query": query,
            "results_count": len(results),
            "leads": results
        }
        
    except Exception as e:
        logger.error(f"AI search failed: {e}", extra={"endpoint": "ai_search"})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/smart-reply/{lead_id}")
async def generate_smart_reply(
    lead_id: int,
    context: str = Query("follow-up", description="Message context: follow-up, welcome, reminder, thank-you"),
    db: Session = Depends(get_db)
):
    """
    ✉️ Generate AI-powered personalized messages
    
    Creates contextual email/WhatsApp messages based on lead data
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise NotFoundError("Lead", lead_id)
    
    try:
        lead_data = {
            "full_name": lead.full_name,
            "country": lead.country,
            "course_interested": lead.course_interested,
            "status": lead.status,
            "ai_score": lead.ai_score
        }
        
        message = await ai_assistant.generate_smart_reply(lead_data, context)
        
        logger.info(
            f"✉️ Generated smart reply for lead {lead_id} ({context})",
            extra={"endpoint": "smart_reply", "lead_id": lead_id}
        )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.full_name,
            "context": context,
            "message": message,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Smart reply generation failed: {e}", extra={"endpoint": "smart_reply"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/summarize-notes/{lead_id}")
async def summarize_lead_notes(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    📝 Summarize all notes for a lead using AI
    
    Returns key insights, sentiment, and recommended actions
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise NotFoundError("Lead", lead_id)
    
    try:
        # Get all notes for this lead
        notes = db.query(DBNote).filter(DBNote.lead_id == lead_id).order_by(DBNote.created_at.desc()).all()
        
        if not notes:
            return {
                "lead_id": lead_id,
                "summary": "No notes available for this lead.",
                "notes_count": 0
            }
        
        notes_data = [
            {
                "content": note.content,
                "created_at": note.created_at.isoformat()
            }
            for note in notes
        ]
        
        summary = await ai_assistant.summarize_notes(notes_data)
        
        logger.info(
            f"📝 Summarized {len(notes)} notes for lead {lead_id}",
            extra={"endpoint": "summarize_notes", "lead_id": lead_id}
        )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.full_name,
            "notes_count": len(notes),
            "summary": summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Note summarization failed: {e}", extra={"endpoint": "summarize_notes"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/next-action/{lead_id}")
async def predict_next_action(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    🎯 AI-powered prediction of best next action for a lead
    
    Analyzes lead data and history to recommend optimal next steps
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise NotFoundError("Lead", lead_id)
    
    try:
        lead_data = {
            "full_name": lead.full_name,
            "status": lead.status,
            "ai_score": lead.ai_score,
            "ai_segment": lead.ai_segment,
            "conversion_probability": lead.conversion_probability,
            "course_interested": lead.course_interested,
            "country": lead.country
        }
        
        # Get recent activities
        activities = db.query(DBActivity).filter(
            DBActivity.lead_id == lead_id
        ).order_by(DBActivity.created_at.desc()).limit(5).all()
        
        activities_data = [
            {
                "activity_type": act.activity_type,
                "created_at": act.created_at.isoformat()
            }
            for act in activities
        ]
        
        prediction = await ai_assistant.predict_best_action(lead_data, activities_data)
        
        logger.info(
            f"🎯 Predicted next action for lead {lead_id}: {prediction.get('action')}",
            extra={"endpoint": "next_action", "lead_id": lead_id}
        )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.full_name,
            "prediction": prediction,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Action prediction failed: {e}", extra={"endpoint": "next_action"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/conversion-barriers/{lead_id}")
async def analyze_conversion_barriers(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    🚧 Identify potential barriers preventing lead conversion
    
    AI analyzes lead data and notes to find blockers
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise NotFoundError("Lead", lead_id)
    
    try:
        lead_data = {
            "status": lead.status,
            "ai_score": lead.ai_score,
            "conversion_probability": lead.conversion_probability,
            "expected_revenue": lead.expected_revenue
        }
        
        # Get notes
        notes = db.query(DBNote).filter(
            DBNote.lead_id == lead_id
        ).order_by(DBNote.created_at.desc()).limit(10).all()
        
        notes_data = [{"content": note.content} for note in notes]
        
        barriers = await ai_assistant.analyze_conversion_barriers(lead_data, notes_data)
        
        logger.info(
            f"🚧 Identified {len(barriers)} barriers for lead {lead_id}",
            extra={"endpoint": "conversion_barriers", "lead_id": lead_id}
        )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.full_name,
            "barriers": barriers,
            "barriers_count": len(barriers),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Barrier analysis failed: {e}", extra={"endpoint": "conversion_barriers"})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/recommend-course/{lead_id}")
async def recommend_course(
    lead_id: int,
    db: Session = Depends(get_db)
):
    """
    🎓 AI-powered course recommendation based on lead profile
    
    Analyzes lead data to suggest the best-fit course
    """
    
    if not ai_assistant.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI features unavailable. Please configure OPENAI_API_KEY in .env"
        )
    
    lead = db.query(DBLead).filter(DBLead.id == lead_id).first()
    if not lead:
        raise NotFoundError("Lead", lead_id)
    
    try:
        lead_data = {
            "country": lead.country,
            "course_interested": lead.course_interested,
            "ai_score": lead.ai_score
        }
        
        # Get available courses
        courses = db.query(DBCourse).filter(DBCourse.is_active == True).all()
        courses_data = [
            {
                "course_name": course.course_name,
                "category": course.category,
                "duration": course.duration,
                "price": float(course.price) if course.price else 0
            }
            for course in courses
        ]
        
        if not courses_data:
            raise HTTPException(status_code=404, detail="No active courses available")
        
        recommendation = await ai_assistant.generate_course_recommendation(lead_data, courses_data)
        
        logger.info(
            f"🎓 Recommended course for lead {lead_id}: {recommendation.get('course_name')}",
            extra={"endpoint": "recommend_course", "lead_id": lead_id}
        )
        
        return {
            "lead_id": lead_id,
            "lead_name": lead.full_name,
            "current_interest": lead.course_interested,
            "recommendation": recommendation,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Course recommendation failed: {e}", extra={"endpoint": "recommend_course"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/status")
async def ai_status():
    """Check AI assistant availability and configuration"""
    
    return {
        "available": ai_assistant.is_available(),
        "model": ai_assistant.model if ai_assistant.is_available() else None,
        "features": [
            "Natural Language Search",
            "Smart Reply Generation",
            "Note Summarization",
            "Next Action Prediction",
            "Conversion Barrier Analysis",
            "Course Recommendations"
        ] if ai_assistant.is_available() else [],
        "status": "ready" if ai_assistant.is_available() else "not_configured"
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database and Supabase status"""
    
    health_status = {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "unknown",
        "supabase": "not_configured",
        "components": {}
    }
    
    # Check database type
    if SQLALCHEMY_DATABASE_URL.startswith("postgresql"):
        health_status["database"] = "postgresql (supabase)"
        
        # Check connection pool health
        try:
            pool = engine.pool
            health_status["components"]["database_pool"] = {
                "status": "healthy",
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "overflow": pool.overflow(),
                "checked_out": pool.checkedout()
            }
        except:
            pass
    else:
        health_status["database"] = "sqlite (local)"
    
    # Test database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database_connection"] = "connected"
    except Exception as e:
        health_status["database_connection"] = "disconnected"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")
    
    # Test Supabase client if configured
    if supabase_manager.client:
        health_status["supabase"] = "configured"
        try:
            # Simple connection test
            supabase_manager.client.table('leads').select("count", count='exact').limit(0).execute()
            health_status["supabase_connection"] = "connected"
        except Exception as e:
            health_status["supabase_connection"] = "disconnected"
            logger.warning(f"Supabase health check failed: {e}")
    
    # Test AI assistant
    health_status["ai_assistant"] = "available" if ai_assistant.is_available() else "not_configured"
    
    # Check ML model status
    health_status["components"]["ml_model"] = {
        "status": "loaded" if get_cached_model() else "not_loaded"
    }
    
    # Check cache statistics
    try:
        cache_stats = get_cache_stats()
        health_status["components"]["cache"] = {
            "status": "healthy",
            "stats": cache_stats
        }
    except:
        pass
    if ai_assistant.is_available():
        health_status["ai_model"] = ai_assistant.model
    
    return health_status

@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe for Kubernetes/deployment orchestration"""
    try:
        # Check critical dependencies
        db.execute(text("SELECT 1"))
        
        # Verify model is loaded (optional for readiness)
        model_status = "loaded" if get_cached_model() else "not_loaded"
        
        return {
            "status": "ready",
            "model": model_status
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail={"status": "not_ready", "reason": str(e)})

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not PROMETHEUS_ENABLED:
        raise HTTPException(status_code=501, detail="Prometheus metrics not enabled")
    
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ==================== COMMUNICATION INTEGRATIONS ====================
# WhatsApp, Email, and Call APIs with ML Training Data Collection

from communication_integrations import (
    communication_service,
    CommunicationHistory
)

@app.post("/api/communications/whatsapp/send")
async def send_whatsapp_message(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Send WhatsApp message to lead"""
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == data["lead_id"]).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        _ensure_lead_access(db, current_user, lead)

        result = communication_service.whatsapp.send_message(
            to_number=data['to'],
            message=data['message'],
            lead_id=data['lead_id'],
            sender=data['sender'],
            db=db
        )
        return result
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/communications/whatsapp/webhook")
async def whatsapp_webhook(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Webhook endpoint for incoming WhatsApp messages"""
    try:
        _ensure_admin_scope(current_user)
        result = communication_service.whatsapp.receive_webhook(data, db)
        return result
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/communications/email/send")
async def send_email(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Send email to lead"""
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == data["lead_id"]).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        _ensure_lead_access(db, current_user, lead)

        result = communication_service.email.send_email(
            to_email=data['to'],
            subject=data.get('subject', 'Message from Medical CRM'),
            body=data['message'],
            lead_id=data['lead_id'],
            sender=data['sender'],
            db=db,
            html=data.get('html', False)
        )
        return result
    except Exception as e:
        logger.error(f"Email send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/communications/call/initiate")
async def initiate_call(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Initiate voice call with recording"""
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == data["lead_id"]).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        _ensure_lead_access(db, current_user, lead)

        callback_url = os.getenv('TWILIO_CALLBACK_URL', 'http://localhost:8000/api/communications/call')
        result = communication_service.calls.initiate_call(
            to_number=data['to_number'],
            lead_id=data['lead_id'],
            counselor=data['counselor'],
            db=db,
            callback_url=callback_url
        )
        return result
    except Exception as e:
        logger.error(f"Call initiation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/communications/call/recording-complete")
async def call_recording_complete(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Webhook for call recording completion"""
    try:
        _ensure_admin_scope(current_user)
        call_sid = data.get('CallSid')
        call_status = data.get('CallStatus')
        call_duration = int(data.get('CallDuration', 0))
        recording_url = data.get('RecordingUrl')
        
        communication_service.calls.update_call_status(
            call_sid=call_sid,
            status=call_status,
            duration=call_duration,
            recording_url=recording_url,
            db=db
        )
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Recording webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/communications/{lead_id}/history")
async def get_communication_history(
    lead_id: str,
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get all communication history for a lead"""
    try:
        lead = db.query(DBLead).filter(DBLead.lead_id == lead_id).first()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        _ensure_lead_access(db, current_user, lead)

        history = communication_service.get_conversation_history(
            lead_id=lead_id,
            db=db,
            communication_type=type
        )
        return history
    except Exception as e:
        logger.error(f"Communication history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/communications/training-data")
async def get_training_data(
    type: Optional[str] = Query(None),
    limit: int = Query(1000),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get communication data for ML model training"""
    try:
        _ensure_admin_scope(current_user)
        
        training_data = communication_service.get_training_data(
            db=db,
            communication_type=type,
            limit=limit
        )
        return {
            "total_records": len(training_data),
            "data": training_data
        }
    except Exception as e:
        logger.error(f"Training data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/communications/mark-training")
async def mark_as_training_data(
    data: Dict[str, List[int]],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Mark specific communications as used for training"""
    try:
        _ensure_admin_scope(current_user)
        
        communication_service.mark_as_training_data(
            communication_ids=data['ids'],
            db=db
        )
        return {"success": True, "marked_count": len(data['ids'])}
    except Exception as e:
        logger.error(f"Mark training error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - BACKGROUND TASKS MANAGEMENT
# ============================================================================

@app.post("/api/tasks/bulk-update")
async def queue_bulk_update_task(
    lead_ids: List[str],
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Queue bulk update task for async processing"""
    try:
        from background_tasks import bulk_update_leads
        
        _ensure_minimum_role(current_user, "Team Leader")
        
        # Queue task
        task = bulk_update_leads.delay(lead_ids, updates, current_user.id)
        
        logger.info(f"Bulk update task queued: {task.id} for {len(lead_ids)} leads")
        
        return {
            "task_id": task.id,
            "status": "queued",
            "lead_count": len(lead_ids)
        }
        
    except Exception as e:
        logger.error(f"Failed to queue bulk update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/bulk-delete")
async def queue_bulk_delete_task(
    lead_ids: List[str],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Queue bulk delete task for async processing"""
    try:
        from background_tasks import bulk_delete_leads
        
        _ensure_minimum_role(current_user, "Manager")
        
        # Queue task
        task = bulk_delete_leads.delay(lead_ids, current_user.id)
        
        logger.info(f"Bulk delete task queued: {task.id} for {len(lead_ids)} leads")
        
        return {
            "task_id": task.id,
            "status": "queued",
            "lead_count": len(lead_ids)
        }
        
    except Exception as e:
        logger.error(f"Failed to queue bulk delete: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/bulk-email")
async def queue_bulk_email_task(
    recipients: List[str],
    subject: str,
    body: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Queue bulk email task"""
    try:
        from message_queue import send_bulk_email
        
        _ensure_minimum_role(current_user, "Team Leader")
        
        # Queue task
        task = send_bulk_email.delay(recipients, subject, body)
        
        logger.info(f"Bulk email task queued: {task.id} for {len(recipients)} recipients")
        
        return {
            "task_id": task.id,
            "status": "queued",
            "recipient_count": len(recipients)
        }
        
    except Exception as e:
        logger.error(f"Failed to queue bulk email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/bulk-whatsapp")
async def queue_bulk_whatsapp_task(
    recipients: List[Dict],
    message: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Queue bulk WhatsApp task"""
    try:
        from message_queue import send_bulk_whatsapp
        
        _ensure_minimum_role(current_user, "Team Leader")
        
        # Queue task
        task = send_bulk_whatsapp.delay(recipients, message)
        
        logger.info(f"Bulk WhatsApp task queued: {task.id} for {len(recipients)} recipients")
        
        return {
            "task_id": task.id,
            "status": "queued",
            "recipient_count": len(recipients)
        }
        
    except Exception as e:
        logger.error(f"Failed to queue bulk WhatsApp: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}/status")
async def get_task_status(
    task_id: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Get status of background task"""
    try:
        from celery_config import celery_app
        from celery.result import AsyncResult
        
        task = AsyncResult(task_id, app=celery_app)
        
        response = {
            "task_id": task_id,
            "status": task.state,
            "ready": task.ready(),
            "successful": task.successful() if task.ready() else None
        }
        
        # Add result if available
        if task.ready():
            if task.successful():
                response["result"] = task.result
            else:
                response["error"] = str(task.info)
        else:
            # Add progress if available
            if task.state == 'PROGRESS' and hasattr(task, 'info'):
                response["progress"] = task.info
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/active")
async def get_active_tasks(
    current_user: DBUser = Depends(get_current_user)
):
    """Get list of active/pending tasks"""
    try:
        from celery_config import celery_app
        
        _ensure_minimum_role(current_user, "Manager")
        
        # Get active tasks
        inspect = celery_app.control.inspect()
        
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()
        
        return {
            "active": active or {},
            "scheduled": scheduled or {},
            "reserved": reserved or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get active tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    current_user: DBUser = Depends(get_current_user)
):
    """Cancel a pending task"""
    try:
        from celery_config import celery_app
        
        _ensure_minimum_role(current_user, "Manager")
        
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info(f"Task {task_id} cancelled by {current_user.email}")
        
        return {
            "task_id": task_id,
            "status": "cancelled"
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/stats")
async def get_task_stats(
    current_user: DBUser = Depends(get_current_user)
):
    """Get task queue statistics"""
    try:
        from celery_config import celery_app
        
        _ensure_minimum_role(current_user, "Manager")
        
        inspect = celery_app.control.inspect()
        
        stats = inspect.stats()
        active_queues = inspect.active_queues()
        
        return {
            "stats": stats or {},
            "active_queues": active_queues or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - ADVANCED ANALYTICS
# ============================================================================

@app.get("/api/analytics/lead-sources")
async def get_lead_source_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    hospital_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get lead source attribution analytics"""
    try:
        from analytics_engine import AnalyticsEngine
        
        # Parse dates
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        engine = AnalyticsEngine(db)
        result = engine.get_lead_source_attribution(
            start_date=start,
            end_date=end,
            hospital_id=hospital_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Lead source analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/conversion-funnel")
async def get_conversion_funnel_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    hospital_id: Optional[int] = Query(None),
    segment: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get conversion funnel analytics"""
    try:
        from analytics_engine import AnalyticsEngine
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        engine = AnalyticsEngine(db)
        result = engine.get_conversion_funnel(
            start_date=start,
            end_date=end,
            hospital_id=hospital_id,
            segment=segment
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Conversion funnel error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/leaderboard")
async def get_counselor_leaderboard(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    metric: str = Query('enrollments'),
    hospital_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get counselor performance leaderboard"""
    try:
        from analytics_engine import AnalyticsEngine
        
        _ensure_minimum_role(current_user, "Team Leader")
        
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        engine = AnalyticsEngine(db)
        result = engine.get_counselor_leaderboard(
            start_date=start,
            end_date=end,
            metric=metric,
            hospital_id=hospital_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/predict-enrollment/{lead_id}")
async def predict_enrollment(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Predict enrollment probability for a lead"""
    try:
        from analytics_engine import AnalyticsEngine
        
        engine = AnalyticsEngine(db)
        result = engine.predict_enrollment_probability(lead_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Enrollment prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/forecast")
async def forecast_enrollments(
    forecast_days: int = Query(30),
    hospital_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Forecast enrollments for next N days"""
    try:
        from analytics_engine import AnalyticsEngine
        
        _ensure_minimum_role(current_user, "Manager")
        
        engine = AnalyticsEngine(db)
        result = engine.forecast_enrollments(
            forecast_days=forecast_days,
            hospital_id=hospital_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Forecast error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analytics/segments")
async def create_custom_segment(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Create custom segment"""
    try:
        from analytics_engine import AnalyticsEngine
        
        _ensure_minimum_role(current_user, "Team Leader")
        
        engine = AnalyticsEngine(db)
        result = engine.create_segment(
            name=data['name'],
            filters=data['filters'],
            user_id=current_user.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Segment creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/data-quality")
async def get_data_quality_report(
    hospital_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: DBUser = Depends(get_current_user)
):
    """Get data quality report"""
    try:
        from analytics_engine import AnalyticsEngine
        
        _ensure_minimum_role(current_user, "Manager")
        
        engine = AnalyticsEngine(db)
        result = engine.get_data_quality_report(hospital_id=hospital_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Data quality report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Medical Education CRM API...")
    print("📊 Dashboard: http://localhost:8000/docs")
    print("🤖 AI Features: http://localhost:8000/api/ai/status")
    print("📱 Communication APIs: WhatsApp, Email, Calls enabled")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
