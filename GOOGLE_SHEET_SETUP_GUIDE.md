# ✅ Google Sheets Integration - Step by Step Setup

## 🎯 Complete Checklist

Follow these steps exactly to connect your Google Sheet to the CRM.

---

## ✅ Step 1: Prepare Your CRM Backend

### Option A: Local Testing (Development)

1. **Start your CRM backend:**
   ```bash
   cd /Users/guneswaribokam/crm/lead-ai/crm/backend
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```

2. **Install ngrok** (to expose localhost to internet):
   ```bash
   # Download from https://ngrok.com/download
   # Or install via brew:
   brew install ngrok
   ```

3. **Start ngrok:**
   ```bash
   ngrok http 8000
   ```

4. **Copy the HTTPS URL** shown (e.g., `https://abc123.ngrok.io`)
   - This is your `API_URL` for Apps Script

### Option B: Production (Recommended)

1. **Deploy to Render** (follow DEPLOYMENT_CHECKLIST.md)
2. **Your API_URL will be:** `https://your-app-name.onrender.com`
3. **Make sure it's running:** Visit `https://your-app-name.onrender.com/docs`

---

## ✅ Step 2: Create Super Admin Account

### If you haven't created an admin yet:

```bash
curl -X POST "https://your-backend-url.com/api/auth/bootstrap-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Super Admin",
    "email": "admin@dmhca.in",
    "password": "Admin@123",
    "phone": "+919876543210",
    "hospital_id": null
  }'
```

**Response should be:**
```json
{
  "id": 1,
  "full_name": "Super Admin",
  "email": "admin@dmhca.in",
  "role": "Super Admin",
  ...
}
```

✅ **Success!** Admin created.

---

## ✅ Step 3: Get Authentication Token

### Login to get JWT token:

```bash
curl -X POST "https://your-backend-url.com/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@dmhca.in&password=Admin@123"
```

**Response will include:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": { ... }
}
```

**📋 COPY the `access_token`** - you'll need this!

⚠️ **Note:** Token expires in 7 days. See auto-refresh option in script.

---

## ✅ Step 4: Prepare Your Google Sheet

### A. Check Your Column Headers

Your sheet should have these columns (exact names):

| Required Columns | Optional Columns |
|-----------------|------------------|
| `full_name` | `ad_id` |
| `phone_number` | `ad_name` |
| `country` | `adset_id` |
| `in_which_program_are_you_interested_?` | `adset_name` |
| `platform` | `campaign_id` |
| | `campaign_name` |
| | `form_id` |
| | `form_name` |
| | `email` |
| | `your_highest_qualification` |
| | `created_time` |
| | `is_organic` |
| | `lead_status` |

### B. Add a Status Column (Optional - Script will create it)

Add a column called: `Sync_Status`
- This will track which rows have been synced

### C. Sample Test Data

Add this row for testing:

```
full_name: John Doe
phone_number: +919876543210
email: john@example.com
country: India
your_highest_qualification: Bachelor's Degree
in_which_program_are_you_interested_?: MBBS
platform: Google Ads
created_time: 2024-03-20 10:00:00
campaign_name: Spring Admissions 2024
ad_name: MBBS Top Colleges
```

---

## ✅ Step 5: Add Apps Script to Google Sheet

### A. Open Apps Script Editor

1. Open your Google Sheet
2. Click **Extensions** → **Apps Script**
3. You'll see a code editor

### B. Copy the Script

1. Delete any existing code in the editor
2. Open the file: `GOOGLE_APPS_SCRIPT.gs`
3. Copy ALL the code
4. Paste into Apps Script editor

### C. Configure the Script

Find these lines at the top (around line 11-13):

```javascript
const API_URL = 'https://your-backend.onrender.com'; // CHANGE THIS!
const AUTH_TOKEN = 'your-jwt-token-here'; // CHANGE THIS!
const SHEET_NAME = 'Sheet1'; // CHANGE THIS if different
```

**Update:**
- `API_URL` → Your backend URL (from Step 1)
- `AUTH_TOKEN` → Your JWT token (from Step 3)
- `SHEET_NAME` → Your sheet tab name (check bottom of Google Sheets)

### D. Save the Script

1. Click **Save** (💾 icon) or Ctrl/Cmd + S
2. Name it: "CRM Lead Sync"
3. ✅ Saved!

---

## ✅ Step 6: Setup Secure Authentication (Recommended)

Instead of hardcoding the token, store it securely:

### A. Run Setup Function

1. In Apps Script editor, select function: `setupAuth`
2. Click **Run** (▶️ button)
3. First time: Click **Review permissions**
4. Choose your Google account
5. Click **Advanced** → **Go to [Your Project]**
6. Click **Allow**
7. A dialog will appear asking for your token
8. Paste your JWT token
9. Click OK

✅ **Token stored securely!**

Now you can remove the hardcoded token from line 13:
```javascript
const AUTH_TOKEN = ''; // Empty - using Script Properties
```

---

## ✅ Step 7: Test the Integration

### A. Test with One Row

1. Make sure you have at least one test row in your sheet
2. In Apps Script, select function: `testSync`
3. Click **Run** (▶️)
4. Check the **Execution log** (bottom panel)

**Expected Output:**
```
=== TEST SYNC ===
✅ Row 2: Synced successfully
=== Sync Complete ===
✅ Synced: 1
❌ Errors: 0
Total processed: 1
```

### B. Verify in CRM

1. Open your CRM backend API docs: `https://your-backend-url.com/docs`
2. Use `GET /api/leads` endpoint
3. Or login to CRM frontend
4. You should see the new lead!

### C. Check Google Sheet

Your sheet should now have:
- New column: `Sync_Status`
- Value in that column: `Synced` (with green background)

✅ **Test successful!**

---

## ✅ Step 8: Setup Automatic Sync

### A. Create Time-Based Trigger

1. In Apps Script editor, click **Triggers** icon (⏰ on left sidebar)
2. Click **+ Add Trigger** (bottom right)
3. Configure:
   - **Function to run:** `syncNewLeads`
   - **Deployment:** Head
   - **Event source:** Time-driven
   - **Type of time based trigger:** Minutes timer
   - **Select minute interval:** Every 5 minutes
4. Click **Save**

### B. Grant Permissions (if needed)

- First time: Review and accept permissions
- Allow the script to access your Google Sheets

### C. Verify Trigger

- You should see your trigger in the list
- Status: Active ✅

✅ **Automatic sync enabled!**

Now every 5 minutes, the script will:
1. Check for new rows without "Synced" status
2. Send them to CRM
3. Mark as "Synced" or show error

---

## ✅ Step 9: Monitor & Maintain

### View Sync History

1. In Apps Script, click **Executions** (📊 on left sidebar)
2. See all sync attempts with timestamps
3. Click any row to see detailed logs

### Check Sync Status in Sheet

- **Green "Synced"** ✅ - Successfully imported
- **Red "Error: [message]"** ❌ - Failed (see error message)
- **Empty** - Not yet processed

### Common Errors & Fixes

| Error Message | Solution |
|---------------|----------|
| `Authentication failed - token expired?` | Get new token (tokens expire in 7 days) or use auto-login |
| `Missing required field: phone_number` | Ensure row has phone number |
| `HTTP 400: Email already registered` | Duplicate email - check CRM |
| `Network error` | Check backend is running |

### Refresh Token (Every 7 Days)

**Option 1: Manual**
1. Get new token: `curl -X POST .../api/auth/login ...`
2. Run `setupAuth()` in Apps Script
3. Paste new token

**Option 2: Automatic (Advanced)**
1. Change trigger function from `syncNewLeads` to `syncWithAutoRefresh`
2. Update credentials in `autoLogin()` function
3. Token will auto-refresh before each sync

---

## ✅ Step 10: Add Custom Menu (Optional)

The script includes a custom menu in Google Sheets.

After running the script once, you'll see:
- **Menu:** 🏥 CRM Sync
- **Options:**
  - Sync Now
  - Test Sync
  - Setup Auth Token
  - Show Config
  - Clear All Sync Status

To enable this menu:
1. Close and reopen your Google Sheet
2. Menu will appear after a few seconds

---

## 🎯 Final Checklist

Before going live, verify:

- [ ] CRM backend is running and accessible
- [ ] Super Admin account created
- [ ] JWT token obtained and stored securely
- [ ] Apps Script configured with correct API_URL
- [ ] Test sync successful (one row)
- [ ] Trigger setup for automatic sync (every 5 minutes)
- [ ] Sync status column appears in sheet
- [ ] Test lead appears in CRM dashboard
- [ ] Team trained on monitoring sync status

---

## 📊 What Happens When Lead is Synced

### In Google Sheet:
1. Row marked as "Synced" with green background
2. Or shows error message with red background

### In CRM:
1. Lead created with unique ID (e.g., `LEAD00123`)
2. AI scoring runs automatically
3. Conversion probability calculated
4. Lead assigned to Super Admin
5. Status set to "New Lead"
6. Initial note added with campaign metadata
7. Activity log created: "Lead created"
8. Email/SMS workflow triggered (if enabled)

### Campaign Metadata Preserved:

The following info from your Google Sheet is saved in the lead's notes:
- Platform (Google Ads, Facebook, etc.)
- Campaign Name
- Ad Name
- Ad Set Name
- Form Name
- Created Time
- Organic vs Paid

This helps you track ROI and lead sources!

---

## 🚨 Troubleshooting Guide

### Issue: "Script function not found: syncNewLeads"
**Solution:** You didn't save the script. Click Save and try again.

### Issue: "Authorization required"
**Solution:** Run any function once manually to grant permissions.

### Issue: "Cannot read property '0' of undefined"
**Solution:** Sheet is empty or SHEET_NAME is wrong. Check configuration.

### Issue: "Exception: Request failed with status 401"
**Solution:** Authentication failed. Token expired or invalid. Get new token.

### Issue: All rows show "Error: Authentication failed"
**Solution:** 
1. Check API_URL is correct
2. Get fresh JWT token (expires in 7 days)
3. Run `setupAuth()` again
4. Or enable auto-login feature

### Issue: "Error: Missing required field: ..."
**Solution:** Check your sheet has all required columns with exact names.

### Issue: Leads syncing multiple times
**Solution:** 
1. Check Sync_Status column exists
2. Don't manually clear "Synced" status
3. Check you don't have multiple triggers running

### Issue: Sync is slow
**Solution:** 
1. Script includes 500ms delay between rows (prevents rate limiting)
2. Normal: ~2 seconds per lead
3. For bulk import, run manually overnight

---

## 🎉 Success Criteria

You'll know it's working when:

✅ Google Sheet shows "Synced" status on new rows
✅ CRM shows new leads appearing automatically
✅ Leads have proper campaign metadata in notes
✅ AI scoring is calculated for each lead
✅ Leads are assigned to Super Admin
✅ No errors in Apps Script execution log

---

## 📚 Quick Reference

### Apps Script Functions

| Function | Purpose | When to Use |
|----------|---------|-------------|
| `syncNewLeads()` | Sync all unsynced rows | Trigger function (auto) |
| `testSync()` | Test with first row only | Testing |
| `setupAuth()` | Store token securely | Initial setup / token refresh |
| `showConfig()` | Display configuration | Debugging |
| `clearAllSyncStatus()` | Reset all sync statuses | Re-import all data |
| `autoLogin()` | Get fresh token | Auto-refresh setup |
| `syncWithAutoRefresh()` | Sync with auto-login | Alternative trigger |

### Important URLs

| What | URL |
|------|-----|
| **Backend API Docs** | `https://your-backend-url.com/docs` |
| **Login Endpoint** | `POST /api/auth/login` |
| **Create Lead** | `POST /api/leads` |
| **List Leads** | `GET /api/leads` |
| **CRM Frontend** | `https://your-frontend.vercel.app` |

### Files Reference

| File | Purpose |
|------|---------|
| `GOOGLE_SHEET_INTEGRATION.md` | Overview & field mapping |
| `GOOGLE_APPS_SCRIPT.gs` | Copy this into Apps Script |
| `GOOGLE_SHEET_SETUP_GUIDE.md` | This file - step by step |

---

## ✨ Summary

**You've successfully connected Google Sheets to your CRM!**

**Data Flow:**
```
Facebook/Google Ads Lead Form
         ↓
   Google Sheet
         ↓
Apps Script (every 5 min)
         ↓
    CRM API
         ↓
   AI Scoring
         ↓
Super Admin Dashboard
```

**What Happens Automatically:**
1. ✅ New row added to Google Sheet (from ad form)
2. ✅ Apps Script detects it (every 5 minutes)
3. ✅ Validates required fields
4. ✅ Sends to CRM API
5. ✅ CRM creates lead + AI scores it
6. ✅ Assigns to Super Admin
7. ✅ Sheet marked as "Synced"
8. ✅ Team can follow up in CRM

**No manual work needed!** 🎉

---

Need help? Check:
- Apps Script execution logs
- CRM API docs at `/docs`
- Error messages in Sync_Status column
