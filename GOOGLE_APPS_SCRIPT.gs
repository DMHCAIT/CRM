// ============================================================================
// GOOGLE SHEETS TO CRM - APPS SCRIPT
// ============================================================================
// This script automatically syncs leads from Google Sheets to your CRM
// ============================================================================

// ============================================================================
// CONFIGURATION - UPDATE THESE VALUES
// ============================================================================

// Your CRM backend URL (no trailing slash)
const API_URL = 'https://your-backend.onrender.com'; // Change this!
// For local testing: 'http://your-ngrok-url' or 'http://localhost:8000'

// Your authentication token (get from login)
// SECURITY: Use Script Properties instead (see setupAuth function)
const AUTH_TOKEN = 'your-jwt-token-here'; // Change this!

// Sheet configuration
const SHEET_NAME = 'Sheet1'; // Name of your sheet with leads
const HEADER_ROW = 1; // Row number where headers are
const STATUS_COLUMN = 'Sync_Status'; // Column to track sync status

// ============================================================================
// MAIN SYNC FUNCTION - Run this automatically via trigger
// ============================================================================

function syncNewLeads() {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    if (!sheet) {
      Logger.log('ERROR: Sheet not found: ' + SHEET_NAME);
      return;
    }

    // Get headers
    const headers = sheet.getRange(HEADER_ROW, 1, 1, sheet.getLastColumn()).getValues()[0];
    const columnMap = buildColumnMap(headers);
    
    // Ensure status column exists
    const statusColIndex = ensureStatusColumn(sheet, headers);
    
    // Get all data rows
    const lastRow = sheet.getLastRow();
    if (lastRow <= HEADER_ROW) {
      Logger.log('No data rows to process');
      return;
    }
    
    const dataRange = sheet.getRange(HEADER_ROW + 1, 1, lastRow - HEADER_ROW, sheet.getLastColumn());
    const rows = dataRange.getValues();
    
    let syncedCount = 0;
    let errorCount = 0;
    
    // Process each row
    rows.forEach((row, index) => {
      const rowNumber = HEADER_ROW + 1 + index;
      const statusCell = sheet.getRange(rowNumber, statusColIndex);
      const currentStatus = statusCell.getValue();
      
      // Skip already synced rows
      if (currentStatus === 'Synced' || currentStatus.toString().startsWith('Error:')) {
        return;
      }
      
      try {
        // Map row data to CRM format
        const leadData = mapRowToLead(row, columnMap);
        
        // Validate required fields
        const validation = validateLead(leadData);
        if (!validation.valid) {
          throw new Error(validation.error);
        }
        
        // Send to CRM
        const response = createLeadInCRM(leadData);
        
        if (response.success) {
          statusCell.setValue('Synced');
          statusCell.setBackground('#d4edda'); // Green
          statusCell.setFontColor('#155724');
          syncedCount++;
          Logger.log(`✅ Row ${rowNumber}: Synced successfully`);
        } else {
          throw new Error(response.error || 'Unknown error');
        }
        
      } catch (error) {
        statusCell.setValue('Error: ' + error.message);
        statusCell.setBackground('#f8d7da'); // Red
        statusCell.setFontColor('#721c24');
        errorCount++;
        Logger.log(`❌ Row ${rowNumber}: ${error.message}`);
      }
      
      // Avoid rate limiting - pause between rows
      Utilities.sleep(500);
    });
    
    Logger.log(`\n=== Sync Complete ===`);
    Logger.log(`✅ Synced: ${syncedCount}`);
    Logger.log(`❌ Errors: ${errorCount}`);
    Logger.log(`Total processed: ${syncedCount + errorCount}`);
    
  } catch (error) {
    Logger.log('FATAL ERROR: ' + error.message);
    Logger.log(error.stack);
  }
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

function mapRowToLead(row, columnMap) {
  const getValue = (columnName) => {
    const index = columnMap[columnName.toLowerCase()];
    return index !== undefined ? row[index] : null;
  };
  
  // Map Google Sheet columns to CRM fields
  const lead = {
    full_name: getValue('full_name') || '',
    phone: getValue('phone_number') || '',
    email: getValue('email') || '',
    country: getValue('country') || 'India',
    qualification: getValue('your_highest_qualification') || '',
    course_interested: getValue('in_which_program_are_you_interested_?') || getValue('course') || '',
    source: getValue('platform') || 'Google Sheet Import',
    whatsapp: getValue('phone_number') || '', // Use same as phone
    branch: null,
    company: null,
    assigned_to: null, // Will be auto-assigned to Super Admin
    notes_text: buildNotesFromMetadata(row, columnMap)
  };
  
  return lead;
}

function buildNotesFromMetadata(row, columnMap) {
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
  if (campaignName) metadata.push(`Campaign: ${campaignName}`);
  if (adName) metadata.push(`Ad: ${adName}`);
  if (adsetName) metadata.push(`Ad Set: ${adsetName}`);
  if (formName) metadata.push(`Form: ${formName}`);
  if (createdTime) metadata.push(`Lead Created: ${createdTime}`);
  if (isOrganic !== null) metadata.push(`Organic: ${isOrganic ? 'Yes' : 'No'}`);
  
  const notes = metadata.length > 0 
    ? `📊 Lead Source Details:\n${metadata.join('\n')}\n\nImported from Google Sheet on ${new Date().toLocaleString()}`
    : `Imported from Google Sheet on ${new Date().toLocaleString()}`;
  
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
  
  const email = 'admin@dmhca.in'; // Change this
  const password = 'Admin@123'; // Change this
  
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
