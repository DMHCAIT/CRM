# ============================================================================
# DEPLOYMENT CHECKLIST - VERCEL + RENDER + SUPABASE
# ============================================================================
# Complete CRM deployment in 30 minutes
# Frontend: Vercel | Backend: Render | Database: Supabase | AI: Claude
# ============================================================================

## ✅ PHASE 1: SUPABASE DATABASE (5 minutes)
# --------------------------------
[ ] 1. Go to https://supabase.com → Sign in
[ ] 2. Create new project:
      - Name: crm-database
      - Database password: (save this!)
      - Region: Choose nearest to your users
[ ] 3. Wait for provisioning (~2 minutes)
[ ] 4. Go to Settings → API → Copy these:
      ✓ Project URL
      ✓ Anon/Public key
      ✓ Service Role key (secret!)
[ ] 5. Save credentials (you'll need them for Render)

## ✅ PHASE 2: RENDER BACKEND (10 minutes)
# --------------------------------
[ ] 1. Go to https://render.com → Sign in with GitHub
[ ] 2. Dashboard → New → Web Service
[ ] 3. Connect repository: DMHCAIT/CRM
[ ] 4. Configure service:
      Name: crm-backend
      Region: Same as Supabase
      Branch: main
      Root Directory: lead-ai/crm/backend
      Runtime: Python 3
      Build Command: pip install -r requirements.txt
      Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT

[ ] 5. Add Environment Variables (click "Add Environment Variable"):

      SUPABASE_URL = (paste from Supabase)
      SUPABASE_KEY = (paste anon key)
      SUPABASE_SERVICE_KEY = (paste service key)
      
      JWT_SECRET_KEY = (generate random: openssl rand -hex 32)
      JWT_ALGORITHM = HS256
      ACCESS_TOKEN_EXPIRE_MINUTES = 10080
      
      # CHOOSE AI MODEL:
      # Option A: Claude (Recommended)
      USE_CLAUDE = true
      ANTHROPIC_API_KEY = sk-ant-... (your Claude API key)
      
      # Option B: OpenAI GPT-4
      # USE_CLAUDE = false
      # OPENAI_API_KEY = sk-... (your OpenAI key)
      
      ENVIRONMENT = production
      CORS_ORIGINS = https://your-app.vercel.app
      
      # Optional: Email
      SMTP_HOST = smtp.gmail.com
      SMTP_PORT = 587
      SMTP_USER = your-email@gmail.com
      SMTP_PASSWORD = your-app-password

[ ] 6. Click "Create Web Service"
[ ] 7. Wait for deployment (~5 minutes)
[ ] 8. Copy your backend URL: https://crm-backend-xxxx.onrender.com
[ ] 9. Test API: Open https://your-backend-url.onrender.com/docs

## ✅ PHASE 3: VERCEL FRONTEND (5 minutes)
# --------------------------------
[ ] 1. Go to https://vercel.com → Sign in with GitHub
[ ] 2. Click "Add New" → Project
[ ] 3. Import repository: DMHCAIT/CRM
[ ] 4. Configure project:
      Framework Preset: Create React App
      Root Directory: lead-ai/crm/frontend
      Build Command: (auto-detected)
      Output Directory: build

[ ] 5. Add Environment Variable:
      REACT_APP_API_URL = https://your-backend.onrender.com
      
[ ] 6. Click "Deploy"
[ ] 7. Wait for deployment (~3 minutes)
[ ] 8. Copy your frontend URL: https://your-app.vercel.app

## ✅ PHASE 4: CONFIGURE CORS (2 minutes)
# --------------------------------
[ ] 1. Go back to Render → Your backend service
[ ] 2. Environment → Edit CORS_ORIGINS
[ ] 3. Update to: https://your-app.vercel.app
[ ] 4. Save changes → Service will auto-redeploy

## ✅ PHASE 5: CREATE ADMIN USER (5 minutes)
# --------------------------------
[ ] 1. Open backend API docs: https://your-backend.onrender.com/docs
[ ] 2. Find POST /api/auth/register endpoint
[ ] 3. Click "Try it out"
[ ] 4. Fill in admin user details:
      {
        "email": "admin@dmhca.in",
        "password": "YourSecurePassword123!",
        "full_name": "Admin User",
        "role": "Super Admin",
        "phone": "+919876543210"
      }
[ ] 5. Click "Execute"
[ ] 6. Copy the access_token from response

## ✅ PHASE 6: LOGIN & TEST (3 minutes)
# --------------------------------
[ ] 1. Open your frontend: https://your-app.vercel.app
[ ] 2. Login with admin credentials
[ ] 3. Test features:
      ✓ Dashboard loads
      ✓ Add a test lead
      ✓ AI features work (search, suggestions)
      ✓ Lead scoring displays

## ✅ PHASE 7: IMPORT DATA (Optional)
# --------------------------------
[ ] 1. Export data from local SQLite:
      sqlite3 crm_database.db .dump > backup.sql
[ ] 2. Go to Supabase → SQL Editor
[ ] 3. Paste and run SQL
[ ] 4. Refresh frontend → Data appears

## ============================================================================
## 🎉 DEPLOYMENT COMPLETE!
## ============================================================================

Your CRM is live at:
- Frontend: https://your-app.vercel.app
- Backend API: https://your-backend.onrender.com
- API Docs: https://your-backend.onrender.com/docs
- Database: Supabase Dashboard

## COSTS (Monthly):
- Supabase: FREE (500MB database)
- Render: FREE tier or $7/month (recommended)
- Vercel: FREE (unlimited)
- Claude API: ~$5-20/month (pay-as-you-go)
- TOTAL: $0-27/month

## NEXT STEPS:
1. Set up custom domain (optional)
2. Configure WhatsApp Business API
3. Import historical lead data
4. Train your team
5. Monitor performance in dashboards

## MONITORING:
- Backend logs: Render Dashboard
- Frontend logs: Vercel Dashboard  
- Database: Supabase Dashboard
- API health: https://backend-url/health

## SUPPORT:
- GitHub: https://github.com/DMHCAIT/CRM
- Issues: Open a GitHub issue
