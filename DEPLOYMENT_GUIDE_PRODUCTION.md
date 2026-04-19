# ============================================================================
# PRODUCTION DEPLOYMENT GUIDE
# ============================================================================
# Deploy to: Vercel (Frontend) + Render (Backend) + Supabase (Database)
#
# Author: DMHCAIT
# Date: April 2026
# ============================================================================

## STEP 1: SUPABASE DATABASE SETUP
# --------------------------------
# 1. Go to supabase.com → Create new project
# 2. Get credentials from Settings → API:
#    - Project URL: https://xxxxx.supabase.co
#    - Anon/Public Key: eyJhbGciOi...
#    - Service Role Key: eyJhbGciOi... (keep secret!)
# 3. Copy to environment variables below

## STEP 2: BACKEND DEPLOYMENT (Render)
# --------------------------------
# 1. Go to render.com → New → Web Service
# 2. Connect GitHub: DMHCAIT/CRM
# 3. Configure:
#    - Name: crm-backend
#    - Root Directory: lead-ai/crm/backend
#    - Environment: Python 3
#    - Build Command: pip install -r requirements.txt
#    - Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
# 4. Add Environment Variables (see below)
# 5. Deploy!

## BACKEND ENVIRONMENT VARIABLES (Render)
# --------------------------------

# Database (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI Model - Choose ONE:

# Option A: Claude (Anthropic) - Recommended if you have access
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
USE_CLAUDE=true

# Option B: OpenAI GPT-4
# OPENAI_API_KEY=sk-your-openai-key-here
# USE_CLAUDE=false

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password

# WhatsApp Business API (Optional)
WHATSAPP_API_URL=https://graph.facebook.com/v17.0
WHATSAPP_API_KEY=your-whatsapp-token
WHATSAPP_PHONE_NUMBER_ID=your-phone-id

# Redis (Optional - for Celery background tasks)
# REDIS_URL=redis://red-xxxxx.redis.cloud.com:6379

# Environment
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.vercel.app

## STEP 3: FRONTEND DEPLOYMENT (Vercel)
# --------------------------------
# 1. Go to vercel.com → Import Project
# 2. Connect GitHub: DMHCAIT/CRM
# 3. Configure:
#    - Root Directory: lead-ai/crm/frontend
#    - Framework Preset: Create React App
# 4. Add Environment Variable:
#    REACT_APP_API_URL=https://crm-backend.onrender.com
# 5. Deploy!

## FRONTEND ENVIRONMENT VARIABLES (Vercel)
# --------------------------------
REACT_APP_API_URL=https://your-backend-name.onrender.com

## STEP 4: POST-DEPLOYMENT
# --------------------------------
# 1. Test API: https://your-backend.onrender.com/docs
# 2. Create admin user via API
# 3. Login at: https://your-frontend.vercel.app
# 4. Import leads data (if needed)

## OPTIONAL: CELERY WORKER (Background Tasks)
# --------------------------------
# Deploy separate worker on Render:
# - Service Type: Background Worker
# - Start Command: celery -A celery_config worker --loglevel=info
# - Add same environment variables as backend
# - Requires Redis (add REDIS_URL)

## COST ESTIMATE (Monthly)
# --------------------------------
# Supabase: FREE (up to 500MB database)
# Render: FREE tier (limited hours) or $7/month
# Vercel: FREE (unlimited bandwidth)
# Claude API: Pay-as-you-go (~$0.01 per request)
# Redis (Optional): $5-10/month for Upstash/Redis Cloud

## MONITORING
# --------------------------------
# Backend logs: Render Dashboard → Logs
# Frontend logs: Vercel Dashboard → Deployments
# Database: Supabase Dashboard → Logs
# API health: https://your-backend.onrender.com/health
