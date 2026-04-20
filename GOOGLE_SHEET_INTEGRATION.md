# 🔗 Google Sheets to CRM Integration

## 📊 Field Mapping

### Your Google Sheet Structure → CRM Fields

| Google Sheet Column | CRM Field | Required | Notes |
|---------------------|-----------|----------|-------|
| `full_name` | `full_name` | ✅ Yes | Lead's full name |
| `phone_number` | `phone` | ✅ Yes | Primary contact number |
| `email` | `email` | ⚠️ Optional | Email address |
| `country` | `country` | ✅ Yes | Lead's country |
| `your_highest_qualification` | `qualification` | ⚠️ Optional | Education level |
| `in_which_program_are_you_interested_?` | `course_interested` | ✅ Yes | Course name |
| `platform` | `source` | ✅ Yes | Lead source (Facebook/Google/etc) |
| `created_time` | *(metadata)* | - | Stored in initial note |
| `ad_name` | *(metadata)* | - | Stored in initial note |
| `campaign_name` | *(metadata)* | - | Stored in initial note |
| `adset_name` | *(metadata)* | - | Stored in initial note |
| `form_name` | *(metadata)* | - | Stored in initial note |
| `is_organic` | *(metadata)* | - | Stored in initial note |
| `lead_status` | *(ignored)* | - | CRM sets own status |

---

## 🚀 Setup Instructions

### Step 1: Prepare Your CRM API

Your CRM needs to be accessible:

**For Local Testing:**
- Backend running at: `http://localhost:8000`
- You'll need ngrok or similar to expose it to Google Sheets

**For Production:**
- Backend deployed at: `https://your-backend.onrender.com`
- Use this URL in the Apps Script

### Step 2: Create Superadmin Account

If you haven't already:

```bash
curl -X POST "https://your-backend.onrender.com/api/auth/bootstrap-admin" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Super Admin",
    "email": "admin@dmhca.in",
    "password": "Admin@123",
    "phone": "+919876543210",
    "hospital_id": null
  }'
```

### Step 3: Get Authentication Token

```bash
curl -X POST "https://your-backend.onrender.com/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@dmhca.in&password=Admin@123"
```

Copy the `access_token` from the response.

### Step 4: Add Apps Script to Your Google Sheet

1. Open your Google Sheet
2. Click **Extensions** → **Apps Script**
3. Delete any existing code
4. Copy the script from `GOOGLE_APPS_SCRIPT.gs` (see below)
5. Update the configuration variables:
   - `API_URL` - Your CRM backend URL
   - `AUTH_TOKEN` - Your JWT token from Step 3
6. Save the script (Ctrl/Cmd + S)
7. Name it "CRM Lead Sync"

### Step 5: Test the Integration

1. In Apps Script editor, select `testSync` function
2. Click **Run** (▶️ button)
3. First time: Grant permissions when prompted
4. Check **Execution log** for results
5. Verify leads appear in CRM

### Step 6: Setup Automatic Sync

1. In Apps Script, click **Triggers** (⏰ icon)
2. Click **+ Add Trigger**
3. Settings:
   - Function: `syncNewLeads`
   - Deployment: Head
   - Event source: Time-driven
   - Type: Minutes timer
   - Interval: Every 5 minutes (or your preference)
4. Save

---

## 📋 How It Works

### Process Flow

```
Google Sheet (New Row)
        ↓
Apps Script (Every 5 min)
        ↓
Check for unprocessed rows
        ↓
Map fields to CRM format
        ↓
Send to CRM API
        ↓
CRM creates lead with AI scoring
        ↓
Mark row as "Synced" in Sheet
        ↓
Assign to Super Admin
```

### What Happens When Lead is Created

1. **Apps Script reads** new row from Sheet
2. **Maps fields** according to table above
3. **Creates initial note** with campaign metadata:
   ```
   Lead from Google Ads
   Campaign: Summer Admission 2024
   Ad: MBBS Course - Top Colleges
   Created: 2024-03-15 10:30:00
   Form: Contact Form - Homepage
   ```
4. **Sends POST request** to `/api/leads`
5. **CRM automatically**:
   - Generates unique lead ID (e.g., `LEAD00123`)
   - Runs AI scoring (conversion probability)
   - Assigns to Super Admin
   - Sets status to "New Lead"
   - Creates activity log
6. **Sheet updated** with sync status

---

## 🔐 Security Best Practices

### ⚠️ Important: Token Security

**Option 1: Use Script Properties (Recommended)**
```javascript
// In Apps Script
const scriptProperties = PropertiesService.getScriptProperties();
scriptProperties.setProperty('AUTH_TOKEN', 'your-token-here');

// Then in code:
const AUTH_TOKEN = scriptProperties.getProperty('AUTH_TOKEN');
```

**Option 2: Refresh Token Automatically**
- Tokens expire after 7 days
- Apps Script can auto-login and refresh
- See advanced script below

### 🔒 API Key Authentication (Alternative)

Instead of JWT tokens, you can create an API key:
- More secure for automation
- No expiration
- See "ADVANCED: API Key Auth" section below

---

## 🧪 Testing

### Test Data Row

Add this test row to your Google Sheet:

| Column | Value |
|--------|-------|
| full_name | Test Lead |
| phone_number | +919876543210 |
| email | test@example.com |
| country | India |
| your_highest_qualification | Bachelor's Degree |
| in_which_program_are_you_interested_? | MBBS |
| platform | Google Ads |
| created_time | 2024-03-15 10:30:00 |
| ad_name | MBBS Course - Top Colleges |
| campaign_name | Summer Admission 2024 |
| lead_status | *(leave empty)* |

Then run `testSync()` in Apps Script.

---

## 📊 Monitoring

### Check Sync Status

The script adds a new column: **`CRM_Sync_Status`**

Values:
- `Synced` ✅ - Successfully sent to CRM
- `Error: [message]` ❌ - Failed with error
- *(empty)* - Not yet processed

### View Logs

1. In Apps Script, click **View** → **Executions**
2. See all sync attempts with timestamps
3. Click any execution to see detailed logs

---

## 🚨 Troubleshooting

### "Authentication failed"
- Token expired (they last 7 days)
- Get new token and update script
- Or implement auto-refresh (see advanced section)

### "Required field missing"
- Check your sheet has all required columns
- Verify column names match exactly
- Ensure row has `full_name`, `phone_number`, `country`, `course_interested`

### "Lead already exists"
- CRM prevents duplicate phone numbers
- Check if lead was already imported
- Update existing lead instead

### "Network error"
- Check CRM backend is running
- Verify API_URL is correct
- For local testing, use ngrok

---

## 📚 Next Steps

1. ✅ Copy Apps Script code (next file)
2. ✅ Configure API URL and token
3. ✅ Test with one row
4. ✅ Setup automatic trigger
5. ✅ Monitor sync status
6. ✅ Train team on system

---

## 🎯 Summary

**What You Get:**
- ✅ Automatic lead import from Google Sheets
- ✅ AI scoring on all imported leads
- ✅ Campaign metadata preserved
- ✅ Assigned to Super Admin automatically
- ✅ Sync status tracking
- ✅ Error handling and logging

**Sync Frequency:** Every 5 minutes (configurable)

**Data Flow:** Sheet → Apps Script → CRM API → Database → AI Scoring → Dashboard

Ready to implement! See `GOOGLE_APPS_SCRIPT.gs` for the code.
