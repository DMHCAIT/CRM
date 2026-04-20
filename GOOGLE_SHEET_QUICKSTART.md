# 🚀 QUICK START: Connect Your Google Sheet to CRM

## ✅ Everything is Ready!

I've created a complete Google Sheets integration for your CRM. Here's what you need to do:

---

## 📋 Your 3-Step Setup

### Step 1: Get Your Auth Token (2 minutes)

```bash
# Login to get JWT token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@dmhca.in&password=Admin@123"
```

Copy the `access_token` from the response.

### Step 2: Add Apps Script (3 minutes)

1. Open your Google Sheet
2. Click **Extensions** → **Apps Script**
3. Copy **ALL** code from: [`GOOGLE_APPS_SCRIPT.gs`](GOOGLE_APPS_SCRIPT.gs)
4. Paste into Apps Script editor
5. **Update these 2 lines:**
   ```javascript
   const API_URL = 'http://localhost:8000';  // Or your production URL
   const AUTH_TOKEN = 'paste-your-token-here';
   ```
6. Save (Ctrl/Cmd + S)

### Step 3: Test It! (1 minute)

1. In Apps Script, select function: `testSync`
2. Click **Run** (▶️)
3. Grant permissions if asked
4. Check execution log - should say "✅ Synced: 1"
5. Check your CRM - lead should appear!

**DONE!** 🎉

---

## 🎯 What Your Script Does

### Automatic Lead Import
- Runs every 5 minutes (configurable)
- Reads new rows from your Google Sheet
- Sends to CRM API automatically
- Marks rows as "Synced" ✅

### Field Mapping
Your exact Google Sheet columns → CRM fields:

| Google Sheet | → | CRM Field |
|--------------|---|-----------|
| `full_name` | → | Full Name |
| `phone_number` | → | Phone |
| `email` | → | Email |
| `country` | → | Country |
| `your_highest_qualification` | → | Qualification |
| `in_which_program_are_you_interested_?` | → | Course Interested |
| `platform` | → | Source |
| `ad_name`, `campaign_name`, etc. | → | Saved in Notes |

**No need to rename your columns!** Everything is mapped automatically.

### Smart Features
- ✅ Validates data before sending
- ✅ Skips already synced rows
- ✅ Shows errors in red if validation fails
- ✅ Preserves campaign metadata
- ✅ Auto-assigns to Super Admin
- ✅ Runs AI scoring on each lead

---

## 📊 Example: What Happens

### 1. New row in Google Sheet:
```
full_name: Priya Sharma
phone_number: +919876543210
email: priya@example.com
country: India
your_highest_qualification: Bachelor's
in_which_program_are_you_interested_?: MBBS
platform: Google Ads
campaign_name: Spring 2024 Admission
ad_name: MBBS Top Colleges
```

### 2. Apps Script processes it:
- ✅ Validates required fields
- ✅ Maps to CRM format
- ✅ Sends to API

### 3. CRM creates lead:
- 📝 ID: `LEAD00123`
- 🎯 AI Score: 78.5
- 📊 Conversion Probability: 72%
- 👤 Assigned to: Super Admin
- 📋 Status: New Lead
- 📝 Notes: Full campaign details

### 4. Google Sheet updated:
- Column `Sync_Status`: **Synced** (green background)

---

## ⚙️ Setup Automatic Sync

After testing works, enable auto-sync:

1. In Apps Script, click **Triggers** (⏰ icon)
2. Click **+ Add Trigger**
3. Settings:
   - Function: `syncNewLeads`
   - Event source: Time-driven
   - Type: Minutes timer
   - Interval: **Every 5 minutes**
4. Save

**Now it runs automatically!** Every 5 minutes, new leads sync to CRM.

---

## 📁 Files Created for You

| File | Purpose |
|------|---------|
| **[GOOGLE_APPS_SCRIPT.gs](GOOGLE_APPS_SCRIPT.gs)** | 📝 Copy this code to Apps Script |
| **[GOOGLE_SHEET_SETUP_GUIDE.md](GOOGLE_SHEET_SETUP_GUIDE.md)** | 📖 Complete step-by-step guide |
| **[GOOGLE_SHEET_FIELD_MAPPING.md](GOOGLE_SHEET_FIELD_MAPPING.md)** | 🗺️ Detailed field mapping |
| **[GOOGLE_SHEET_INTEGRATION.md](GOOGLE_SHEET_INTEGRATION.md)** | 📚 Technical overview |

---

## 🔐 Security Tips

### Option 1: Hardcode Token (Quick)
```javascript
const AUTH_TOKEN = 'your-jwt-token-here';
```
⚠️ Token expires in 7 days - need to update manually

### Option 2: Secure Storage (Recommended)
1. Run `setupAuth()` function in Apps Script
2. Paste token when prompted
3. Delete hardcoded token from code
4. More secure!

### Option 3: Auto-Refresh (Advanced)
1. Change trigger to `syncWithAutoRefresh`
2. Update credentials in `autoLogin()` function
3. Token refreshes automatically!

---

## ✅ Pre-Flight Checklist

Before going live:

- [ ] Backend running (localhost:8000 or production URL)
- [ ] Super Admin account created
- [ ] JWT token obtained
- [ ] Apps Script code copied
- [ ] API_URL configured
- [ ] AUTH_TOKEN configured
- [ ] Test sync successful (one row)
- [ ] Lead appears in CRM
- [ ] Automatic trigger setup (5 min interval)
- [ ] Team trained on monitoring

---

## 🧪 Quick Test

### Test Data (Add to your sheet):

```
full_name: Test Lead
phone_number: +919999999999
email: test@test.com
country: India
your_highest_qualification: Bachelor's
in_which_program_are_you_interested_?: MBBS
platform: Google Ads
```

### Run Test:
1. Apps Script → Select `testSync`
2. Click Run
3. Check log: "✅ Synced: 1"
4. Check CRM: New lead "Test Lead"
5. Check Sheet: "Synced" status

**If all ✅ → Ready for production!**

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| "Authentication failed" | Token expired - get new one |
| "Missing required field" | Check row has all required columns |
| "Network error" | Check backend is running |
| "Sheet not found" | Update `SHEET_NAME` in config |
| Script runs but nothing happens | Check execution log for errors |

---

## 📊 Monitoring

### Check Sync Status in Google Sheet:
- **Green "Synced"** ✅ = Success
- **Red "Error: ..."** ❌ = Failed (see error)
- **Empty** = Not yet processed

### Check Execution Log in Apps Script:
1. Click **Executions** (📊 icon)
2. See all sync attempts
3. Click row for detailed logs

### Check Leads in CRM:
- Open http://localhost:8000/docs
- Use `GET /api/leads` endpoint
- Or login to frontend dashboard

---

## 🎯 Summary

**What You Have:**
- ✅ Complete Apps Script code (ready to use)
- ✅ Automatic field mapping (no changes needed)
- ✅ Step-by-step setup guides
- ✅ Test functions included
- ✅ Error handling built-in
- ✅ Campaign metadata preserved

**What Happens:**
```
Google Sheet (new row)
        ↓
Apps Script (every 5 min)
        ↓
Validate & Map Fields
        ↓
Send to CRM API
        ↓
AI Scoring + Auto-Assignment
        ↓
Mark as "Synced" ✅
```

**Time to Setup:** 10 minutes
**Effort After Setup:** Zero! Fully automatic 🎉

---

## 🚀 Next Steps

1. **Now:** Test with one row manually
2. **Today:** Setup automatic trigger (5 min)
3. **This Week:** Monitor sync status daily
4. **Going Forward:** Leads flow automatically!

---

## 📚 Need More Details?

Read the complete guides:
- **Quick Setup:** This file (you're reading it!)
- **Step by Step:** [GOOGLE_SHEET_SETUP_GUIDE.md](GOOGLE_SHEET_SETUP_GUIDE.md)
- **Field Mapping:** [GOOGLE_SHEET_FIELD_MAPPING.md](GOOGLE_SHEET_FIELD_MAPPING.md)
- **Technical Docs:** [GOOGLE_SHEET_INTEGRATION.md](GOOGLE_SHEET_INTEGRATION.md)

---

## ✨ You're All Set!

**Your Google Sheet is ready to sync with CRM!**

Just copy the script, configure 2 variables, test it, and enable the trigger.

**Leads will flow automatically from your Google Sheet to CRM with AI scoring!** 🚀

Questions? Check the troubleshooting section in [GOOGLE_SHEET_SETUP_GUIDE.md](GOOGLE_SHEET_SETUP_GUIDE.md)
