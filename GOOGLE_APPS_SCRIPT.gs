// ============================================================================
// GOOGLE SHEETS TO CRM - APPS SCRIPT
// ============================================================================
// This script automatically syncs leads from Google Sheets to your CRM
// ============================================================================

// ============================================================================
// CONFIGURATION - UPDATE THESE VALUES
// ============================================================================

// Your CRM backend URL (no trailing slash)
const API_URL = 'https://crm-backend-kd86.onrender.com';
// For local testing: 'http://your-ngrok-url' or 'http://localhost:8000'

// Your authentication token (get from login)
// SECURITY: Use Script Properties instead (see setupAuth function)
const AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBkbWhjYS5pbiIsInJvbGUiOiJTdXBlciBBZG1pbiIsImhvc3BpdGFsX2lkIjpudWxsLCJleHAiOjE3NzcyODUxMjR9.jHtzR1j0qM3vrrXPYhTji6XLM5zkJfa9cPoAXB5rvVQ';

// Sheet configuration
// Set to null to sync ALL sheets, or specify a name like 'Pediatric' to sync just one
const SHEET_NAME = null; // null = ALL sheets
const HEADER_ROW = 1; // Row number where headers are
const STATUS_COLUMN = 'Sync_Status'; // Column to track sync status

// Sheets to SKIP (system sheets, summaries, etc.)
const SKIP_SHEETS = ['Summary', 'Config', 'Template', 'Instructions'];

// ============================================================================
// MAIN SYNC FUNCTION - Run this automatically via trigger
// ============================================================================

function syncNewLeads() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheets;

  if (SHEET_NAME) {
    // Sync specific sheet only
    const sheet = spreadsheet.getSheetByName(SHEET_NAME);
    if (!sheet) {
      Logger.log('ERROR: Sheet not found: ' + SHEET_NAME);
      return;
    }
    sheets = [sheet];
  } else {
    // Sync ALL sheets (skip system sheets)
    sheets = spreadsheet.getSheets().filter(s => !SKIP_SHEETS.includes(s.getName()));
  }

  Logger.log(`=== Syncing ${sheets.length} sheet(s) ===`);

  let totalSynced = 0;
  let totalErrors = 0;

  sheets.forEach(sheet => {
    Logger.log(`\n--- Processing sheet: ${sheet.getName()} ---`);
    const result = syncSheet(sheet);
    totalSynced += result.synced;
    totalErrors += result.errors;
  });

  Logger.log(`\n============================`);
  Logger.log(`✅ TOTAL Synced: ${totalSynced}`);
  Logger.log(`❌ TOTAL Errors: ${totalErrors}`);
  Logger.log(`============================`);
}

function syncSheet(sheet) {
  let syncedCount = 0;
  let errorCount = 0;

  try {
    const lastRow = sheet.getLastRow();
    const lastCol = sheet.getLastColumn();

    if (lastRow <= HEADER_ROW || lastCol < 1) {
      Logger.log(`  Skipping empty sheet: ${sheet.getName()}`);
      return { synced: 0, errors: 0 };
    }

    // Get headers
    const headers = sheet.getRange(HEADER_ROW, 1, 1, lastCol).getValues()[0];
    const columnMap = buildColumnMap(headers);

    // Check sheet has required columns
    if (!columnMap['full_name'] && !columnMap['phone_number']) {
      Logger.log(`  Skipping sheet (no lead columns): ${sheet.getName()}`);
      return { synced: 0, errors: 0 };
    }

    // Ensure status column exists
    const statusColIndex = ensureStatusColumn(sheet, headers);

    // Get all data rows
    const dataRange = sheet.getRange(HEADER_ROW + 1, 1, lastRow - HEADER_ROW, lastCol);
    const rows = dataRange.getValues();

    rows.forEach((row, index) => {
      const rowNumber = HEADER_ROW + 1 + index;

      // Skip empty rows
      if (row.every(cell => cell === '' || cell === null)) return;

      const statusCell = sheet.getRange(rowNumber, statusColIndex);
      const currentStatus = statusCell.getValue();

      // Skip already synced rows
      if (currentStatus === 'Synced' || currentStatus.toString().startsWith('Error:')) {
        return;
      }

      try {
        const leadData = mapRowToLead(row, columnMap, sheet.getName());
        const validation = validateLead(leadData);
        if (!validation.valid) throw new Error(validation.error);

        const response = createLeadInCRM(leadData);

        if (response.success) {
          statusCell.setValue('Synced');
          statusCell.setBackground('#d4edda');
          statusCell.setFontColor('#155724');
          syncedCount++;
          Logger.log(`  ✅ Row ${rowNumber}: ${leadData.full_name} synced`);
        } else {
          throw new Error(response.error || 'Unknown error');
        }

      } catch (error) {
        statusCell.setValue('Error: ' + error.message);
        statusCell.setBackground('#f8d7da');
        statusCell.setFontColor('#721c24');
        errorCount++;
        Logger.log(`  ❌ Row ${rowNumber}: ${error.message}`);
      }

      Utilities.sleep(300);
    });

    Logger.log(`  Sheet "${sheet.getName()}": ✅${syncedCount} synced, ❌${errorCount} errors`);

  } catch (error) {
    Logger.log(`  FATAL ERROR in sheet "${sheet.getName()}": ${error.message}`);
  }

  return { synced: syncedCount, errors: errorCount };
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function buildColumnMap(headers) {
  const map = {};
  headers.forEach((header, index) => {
    map[header.toString().toLowerCase().trim()] = index;
  });
  return map;
}

function ensureStatusColumn(sheet, headers) {
  const statusColName = STATUS_COLUMN;
  let statusColIndex = headers.indexOf(statusColName);
  
  if (statusColIndex === -1) {
    // Add status column
    statusColIndex = headers.length;
    sheet.getRange(HEADER_ROW, statusColIndex + 1).setValue(statusColName);
    sheet.getRange(HEADER_ROW, statusColIndex + 1).setFontWeight('bold');
  }
  
  return statusColIndex + 1; // Convert to 1-based index
}

function mapRowToLead(row, columnMap, sheetName) {
  const getValue = (columnName) => {
    const index = columnMap[columnName.toLowerCase()];
    return index !== undefined ? row[index] : null;
  };
  
  // Map Google Sheet columns to CRM fields
  // Use sheet name as fallback course (e.g. 'Pediatric', 'Pulmonology')
  const lead = {
    full_name: getValue('full_name') || '',
    phone: getValue('phone_number') || '',
    email: getValue('email') || '',
    country: getValue('country') || 'India',
    qualification: getValue('your_highest_qualification') || '',
    course_interested: getValue('in_which_program_are_you_interested_?') || getValue('course') || sheetName || '',
    source: getValue('platform') || 'Google Sheet Import',
    whatsapp: getValue('phone_number') || '',
    branch: null,
    company: null,
    assigned_to: null,
    notes_text: buildNotesFromMetadata(row, columnMap, sheetName)
  };
  
  return lead;
}

function buildNotesFromMetadata(row, columnMap, sheetName) {
  const getValue = (columnName) => {
    const index = columnMap[columnName.toLowerCase()];
    return index !== undefined ? row[index] : null;
  };
  
  const metadata = [];
  
  // Add campaign information
  const platform = getValue('platform');
  const campaignName = getValue('campaign_name');
  const adName = getValue('ad_name');
  const adsetName = getValue('adset_name');
  const formName = getValue('form_name');
  const createdTime = getValue('created_time');
  const isOrganic = getValue('is_organic');
  
  if (platform) metadata.push(`Platform: ${platform}`);
  if (sheetName) metadata.push(`Sheet/Campaign: ${sheetName}`);
  if (campaignName) metadata.push(`Campaign: ${campaignName}`);
  if (adName) metadata.push(`Ad: ${adName}`);
  if (adsetName) metadata.push(`Ad Set: ${adsetName}`);
  if (formName) metadata.push(`Form: ${formName}`);
  if (createdTime) metadata.push(`Lead Created: ${createdTime}`);
  if (isOrganic !== null) metadata.push(`Organic: ${isOrganic ? 'Yes' : 'No'}`);
  
  const notes = metadata.length > 0 
    ? `📊 Lead Source Details:\n${metadata.join('\n')}\n\nImported from Google Sheet (${sheetName || 'Unknown'}) on ${new Date().toLocaleString()}`
    : `Imported from Google Sheet (${sheetName || 'Unknown'}) on ${new Date().toLocaleString()}`;
  
  return notes;
}

function validateLead(lead) {
  // Check required fields
  if (!lead.full_name || lead.full_name.trim() === '') {
    return { valid: false, error: 'Missing required field: full_name' };
  }
  
  if (!lead.phone || lead.phone.trim() === '') {
    return { valid: false, error: 'Missing required field: phone_number' };
  }
  
  if (!lead.country || lead.country.trim() === '') {
    return { valid: false, error: 'Missing required field: country' };
  }
  
  if (!lead.course_interested || lead.course_interested.trim() === '') {
    return { valid: false, error: 'Missing required field: course_interested' };
  }
  
  if (!lead.source || lead.source.trim() === '') {
    return { valid: false, error: 'Missing required field: platform/source' };
  }
  
  return { valid: true };
}

function createLeadInCRM(leadData) {
  try {
    const url = `${API_URL}/api/leads`;
    
    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: {
        'Authorization': `Bearer ${getAuthToken()}`
      },
      payload: JSON.stringify(leadData),
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const statusCode = response.getResponseCode();
    const responseBody = response.getContentText();
    
    if (statusCode === 200 || statusCode === 201) {
      const data = JSON.parse(responseBody);
      Logger.log(`Lead created: ${data.lead_id || 'ID not returned'}`);
      return { success: true, data: data };
    } else if (statusCode === 401) {
      return { success: false, error: 'Authentication failed - token expired?' };
    } else if (statusCode === 400) {
      const error = JSON.parse(responseBody);
      return { success: false, error: error.detail || 'Bad request' };
    } else {
      return { success: false, error: `HTTP ${statusCode}: ${responseBody}` };
    }
    
  } catch (error) {
    return { success: false, error: error.message };
  }
}

function getAuthToken() {
  // Try to get from Script Properties first (more secure)
  const scriptProperties = PropertiesService.getScriptProperties();
  const token = scriptProperties.getProperty('AUTH_TOKEN');
  
  if (token) {
    return token;
  }
  
  // Fallback to hardcoded token
  return AUTH_TOKEN;
}

// ============================================================================
// SETUP & UTILITY FUNCTIONS
// ============================================================================

function setupAuth() {
  // Run this once to store auth token securely
  const token = Browser.inputBox('Enter your JWT token:', Browser.Buttons.OK_CANCEL);
  
  if (token !== 'cancel') {
    const scriptProperties = PropertiesService.getScriptProperties();
    scriptProperties.setProperty('AUTH_TOKEN', token);
    Browser.msgBox('Auth token saved securely!');
  }
}

function testSync() {
  // Test function - syncs just the first unsynced row
  Logger.log('=== TEST SYNC ===');
  syncNewLeads();
}

function clearAllSyncStatus() {
  // Utility to reset all sync statuses (use with caution!)
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const headers = sheet.getRange(HEADER_ROW, 1, 1, sheet.getLastColumn()).getValues()[0];
  const statusColIndex = headers.indexOf(STATUS_COLUMN);
  
  if (statusColIndex !== -1) {
    const lastRow = sheet.getLastRow();
    if (lastRow > HEADER_ROW) {
      sheet.getRange(HEADER_ROW + 1, statusColIndex + 1, lastRow - HEADER_ROW, 1)
        .clearContent()
        .clearFormat();
      Logger.log(`Cleared sync status for ${lastRow - HEADER_ROW} rows`);
    }
  }
}

function showConfig() {
  // Display current configuration
  Logger.log('=== CONFIGURATION ===');
  Logger.log(`API URL: ${API_URL}`);
  Logger.log(`Sheet Name: ${SHEET_NAME}`);
  Logger.log(`Header Row: ${HEADER_ROW}`);
  Logger.log(`Status Column: ${STATUS_COLUMN}`);
  
  const scriptProperties = PropertiesService.getScriptProperties();
  const hasToken = scriptProperties.getProperty('AUTH_TOKEN') !== null;
  Logger.log(`Auth Token Stored: ${hasToken ? 'Yes ✅' : 'No ❌'}`);
}

// ============================================================================
// ADVANCED: AUTO-LOGIN (Optional)
// ============================================================================

function autoLogin() {
  // Automatically get fresh JWT token
  // Use this if you want auto-refresh instead of manual token updates
  
  const email = 'admin@dmhca.in';
  const password = 'Admin@123';
  
  try {
    const url = `${API_URL}/api/auth/login`;
    const formData = `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`;
    
    const options = {
      method: 'post',
      contentType: 'application/x-www-form-urlencoded',
      payload: formData,
      muteHttpExceptions: true
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const data = JSON.parse(response.getContentText());
    
    if (data.access_token) {
      // Store token
      const scriptProperties = PropertiesService.getScriptProperties();
      scriptProperties.setProperty('AUTH_TOKEN', data.access_token);
      Logger.log('✅ Auto-login successful! Token refreshed.');
      return data.access_token;
    } else {
      Logger.log('❌ Auto-login failed: No token in response');
      return null;
    }
    
  } catch (error) {
    Logger.log('❌ Auto-login error: ' + error.message);
    return null;
  }
}

function syncWithAutoRefresh() {
  // Sync with automatic token refresh
  // Use this as your trigger function instead of syncNewLeads()
  
  // Try to login first to ensure fresh token
  autoLogin();
  
  // Then sync
  syncNewLeads();
}

// ============================================================================
// MENU FUNCTIONS (Optional - adds menu to Google Sheets)
// ============================================================================

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🏥 CRM Sync')
    .addItem('Sync Now', 'syncNewLeads')
    .addItem('Test Sync (First Row)', 'testSync')
    .addSeparator()
    .addItem('Setup Auth Token', 'setupAuth')
    .addItem('Show Config', 'showConfig')
    .addSeparator()
    .addItem('Clear All Sync Status', 'clearAllSyncStatus')
    .addToUi();
}

// ============================================================================
// END OF SCRIPT
// ============================================================================

/*
SETUP INSTRUCTIONS:

1. Update Configuration (lines 11-13):
   - API_URL: Your CRM backend URL
   - AUTH_TOKEN: Your JWT token (or use setupAuth function)

2. Save the script (Ctrl/Cmd + S)

3. Run setupAuth() to store token securely (optional but recommended)

4. Test with testSync() function

5. Setup automatic trigger:
   - Click Triggers icon (⏰)
   - Add Trigger
   - Function: syncNewLeads (or syncWithAutoRefresh for auto-login)
   - Event: Time-driven
   - Type: Minutes timer
   - Interval: Every 5 minutes

6. Grant permissions when prompted

7. Monitor in Executions log

Done! Leads will auto-sync every 5 minutes.
*/
