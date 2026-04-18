import React, { useState } from 'react';
import {
  Card, Row, Col, Button, Input, Typography, Space, Steps, Tag,
  Alert, Divider, Table, Statistic, message, Tooltip, Badge,
} from 'antd';
import {
  LinkOutlined, CopyOutlined, CheckCircleOutlined, ApiOutlined,
  ThunderboltOutlined, FileTextOutlined, SyncOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { sheetSyncAPI } from '../api/api';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// The API key is set in .env — displayed here so admin can copy it
const API_KEY = 'Q8NBK5k8_OyPwo61SnibtH_cjvEnLfQym-4qAun4_nM';
const CRM_BASE_URL = window.location.origin.includes('localhost')
  ? 'http://localhost:8000'
  : window.location.origin;

const WEBHOOK_URL = `${CRM_BASE_URL}/api/webhook/sheet-sync?api_key=${API_KEY}`;
const STATUS_URL  = `${CRM_BASE_URL}/api/webhook/sheet-sync/status?api_key=${API_KEY}`;

// ── Apps Script code ───────────────────────────────────────────────────────

const APPS_SCRIPT = `/**
 * ============================================================
 *  MEDFELLOW CRM — Google Sheet Sync
 *  Copy this entire script into your Google Sheet:
 *    Extensions → Apps Script → paste → Save → Run syncToCRM
 * ============================================================
 */

// ── CONFIGURATION ────────────────────────────────────────────
const CRM_WEBHOOK_URL = "${WEBHOOK_URL}";
const SHEET_NAME      = "Sheet1";   // change if your tab has a different name
const SYNC_COL_HEADER = "CRM Sync Status"; // column auto-added to track sync state
// ─────────────────────────────────────────────────────────────

function syncToCRM() {
  const ss    = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    SpreadsheetApp.getUi().alert("Sheet '" + SHEET_NAME + "' not found.");
    return;
  }

  const allData    = sheet.getDataRange().getValues();
  const headers    = allData[0].map(String);          // row 1 = headers

  // Find or create the "CRM Sync Status" column
  let syncColIndex = headers.indexOf(SYNC_COL_HEADER);
  if (syncColIndex === -1) {
    syncColIndex = headers.length;
    sheet.getRange(1, syncColIndex + 1).setValue(SYNC_COL_HEADER);
    headers.push(SYNC_COL_HEADER);
  }
  const syncCol = syncColIndex + 1; // 1-based for setValues

  // Collect rows not yet synced
  const rowsToSync   = [];
  const rowIndices   = [];

  for (let i = 1; i < allData.length; i++) {
    const syncStatus = String(allData[i][syncColIndex] || "").trim();
    const hasData    = allData[i].some(cell => String(cell).trim() !== "");
    if (hasData && syncStatus !== "✓ Synced") {
      rowsToSync.push(allData[i]);
      rowIndices.push(i + 1); // 1-based sheet row
    }
  }

  if (rowsToSync.length === 0) {
    SpreadsheetApp.getUi().alert("All rows are already synced to CRM!");
    return;
  }

  Logger.log("Sending " + rowsToSync.length + " rows to CRM...");

  const payload = JSON.stringify({
    headers: headers.slice(0, syncColIndex),  // don't send the sync-status column
    rows: rowsToSync.map(r => r.slice(0, syncColIndex)),
    sheet_name: SHEET_NAME
  });

  const options = {
    method: "post",
    contentType: "application/json",
    payload: payload,
    muteHttpExceptions: true
  };

  let response;
  try {
    response = UrlFetchApp.fetch(CRM_WEBHOOK_URL, options);
  } catch (e) {
    SpreadsheetApp.getUi().alert("Network error: " + e.message);
    return;
  }

  const code = response.getResponseCode();
  if (code !== 200) {
    SpreadsheetApp.getUi().alert("CRM returned error " + code + ":\\n" + response.getContentText());
    return;
  }

  const result = JSON.parse(response.getContentText());
  Logger.log("Sync result: " + JSON.stringify(result));

  // Update sync status column per row
  result.details.forEach(function(detail) {
    // detail.row is 1-based sheet row (2 = first data row)
    const sheetRow = detail.row;
    const cell     = sheet.getRange(sheetRow, syncCol);
    if (detail.status === "created") {
      cell.setValue("✓ Synced");
      cell.setBackground("#d9f7be");
    } else if (detail.status === "skipped") {
      cell.setValue("↩ " + detail.reason);
      cell.setBackground("#fff7e6");
    } else {
      cell.setValue("✗ Error: " + detail.reason);
      cell.setBackground("#fff1f0");
    }
  });

  const msg = [
    "Sync complete!",
    "  Created : " + result.created,
    "  Skipped : " + result.skipped  + " (duplicates / missing name)",
    "  Errors  : " + result.errors,
    "  Total   : " + result.total
  ].join("\\n");
  SpreadsheetApp.getUi().alert(msg);
}

/**
 * Creates a "CRM" menu in the spreadsheet toolbar.
 * Runs automatically when the sheet is opened.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("CRM Sync")
    .addItem("Sync to MedFellow CRM", "syncToCRM")
    .addItem("Check Connection",      "checkConnection")
    .addToUi();
}

function checkConnection() {
  const statusUrl = "${STATUS_URL}";
  try {
    const res  = UrlFetchApp.fetch(statusUrl, { muteHttpExceptions: true });
    const data = JSON.parse(res.getContentText());
    SpreadsheetApp.getUi().alert(
      "✓ Connected to MedFellow CRM\\n\\n" +
      "Total leads in CRM  : " + data.total_leads_in_crm + "\\n" +
      "Imported via sheet  : " + data.sheet_imported_leads
    );
  } catch (e) {
    SpreadsheetApp.getUi().alert("Connection failed: " + e.message);
  }
}

/**
 * Optional: auto-sync every hour via time-based trigger.
 * Run setupTrigger() once from the Apps Script editor to activate.
 */
function setupTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger("syncToCRM")
    .timeBased()
    .everyHours(1)
    .create();
  SpreadsheetApp.getUi().alert("Auto-sync trigger set: every 1 hour");
}

function removeTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  SpreadsheetApp.getUi().alert("All triggers removed.");
}
`;

// ── column mapping table ───────────────────────────────────────────────────

const MAPPING_DATA = [
  { sheet: 'Full Name / Name',         crm: 'full_name',         required: true  },
  { sheet: 'Phone / Mobile',           crm: 'phone',             required: true  },
  { sheet: 'Email',                    crm: 'email',             required: false },
  { sheet: 'WhatsApp',                 crm: 'whatsapp',          required: false },
  { sheet: 'Country',                  crm: 'country',           required: false },
  { sheet: 'Branch',                   crm: 'branch',            required: false },
  { sheet: 'Qualification',            crm: 'qualification',     required: false },
  { sheet: 'Source / Lead Source',     crm: 'source',            required: false },
  { sheet: 'Course / Course Interested', crm: 'course_interested', required: false },
  { sheet: 'Company / Hospital',       crm: 'company',           required: false },
  { sheet: 'Status / Lead Status',     crm: 'status',            required: false },
  { sheet: 'Assigned To / Counselor',  crm: 'assigned_to',       required: false },
  { sheet: 'Follow Up / Follow Up Date', crm: 'follow_up_date',  required: false },
  { sheet: 'Notes / Remarks',          crm: 'notes_text',        required: false },
  { sheet: 'ID / Created At / Updated At', crm: '(skipped)',     required: false },
];

// ── component ──────────────────────────────────────────────────────────────

const GoogleSheetSync = () => {
  const [copied, setCopied] = useState(null);

  const { data: status, isLoading, refetch } = useQuery({
    queryKey: ['sheet-sync-status'],
    queryFn: () => sheetSyncAPI.getStatus(API_KEY).then(r => r.data).catch(() => null),
  });

  const copy = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    message.success('Copied!');
    setTimeout(() => setCopied(null), 2000);
  };

  const mappingCols = [
    { title: 'Google Sheet Column Header(s)', dataIndex: 'sheet', key: 'sheet',
      render: v => <Text code>{v}</Text> },
    { title: 'CRM Field', dataIndex: 'crm', key: 'crm',
      render: v => v === '(skipped)'
        ? <Tag color="default">Skipped</Tag>
        : <Tag color="blue">{v}</Tag> },
    { title: 'Required', dataIndex: 'required', key: 'required',
      render: v => v ? <Tag color="red">Required</Tag> : <Tag>Optional</Tag> },
  ];

  return (
    <div style={{ maxWidth: 960 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Google Sheet → CRM Sync</Title>
        <Text type="secondary">Import leads from your Google Sheet automatically via Apps Script</Text>
      </div>

      {/* Connection status */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="Connection"
              value={status ? 'Connected' : isLoading ? 'Checking…' : 'Not reachable'}
              prefix={status ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ApiOutlined />}
              valueStyle={{ color: status ? '#52c41a' : '#8c8c8c', fontSize: 16 }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="Total Leads in CRM" value={status?.total_leads_in_crm ?? '—'} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="Imported via Sheet" value={status?.sheet_imported_leads ?? '—'}
              valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
      </Row>

      {/* Step-by-step guide */}
      <Card style={{ marginBottom: 24 }}>
        <Steps
          direction="vertical"
          size="small"
          current={-1}
          items={[
            {
              title: 'Open your Google Sheet',
              description: (
                <Space>
                  <a href="https://docs.google.com/spreadsheets/d/1icOnwhO-kqdw-h716CBuQ01J5Anhl-SwqXBctY0qfZU/edit"
                     target="_blank" rel="noreferrer">
                    Open Sheet <LinkOutlined />
                  </a>
                </Space>
              ),
            },
            {
              title: 'Open Apps Script editor',
              description: <Text type="secondary">In the sheet: <Text code>Extensions → Apps Script</Text></Text>,
            },
            {
              title: 'Paste the script below',
              description: <Text type="secondary">Delete any existing code, paste the full script, then click Save.</Text>,
            },
            {
              title: 'Run onOpen once',
              description: <Text type="secondary">Click <Text code>Run → onOpen</Text> to add the "CRM Sync" menu to your sheet.</Text>,
            },
            {
              title: 'Sync leads',
              description: <Text type="secondary">In your Sheet toolbar: <Text code>CRM Sync → Sync to MedFellow CRM</Text>. New rows auto-marked ✓ Synced.</Text>,
            },
            {
              title: '(Optional) Auto-sync every hour',
              description: <Text type="secondary">Run <Text code>setupTrigger()</Text> once from Apps Script to enable automatic hourly sync.</Text>,
            },
          ]}
        />
      </Card>

      {/* API Key + Webhook URL */}
      <Card title={<><ApiOutlined /> Webhook Details</>} style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>API Key</Text>
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
              (already embedded in the script below — keep it private)
            </Text>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Input.Password value={API_KEY} readOnly style={{ fontFamily: 'monospace' }} />
              <Tooltip title="Copy API key">
                <Button icon={<CopyOutlined />} onClick={() => copy(API_KEY, 'apikey')}>
                  {copied === 'apikey' ? 'Copied!' : 'Copy'}
                </Button>
              </Tooltip>
            </div>
          </div>
          <div>
            <Text strong>Webhook URL</Text>
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              <Input value={WEBHOOK_URL} readOnly style={{ fontFamily: 'monospace', fontSize: 12 }} />
              <Button icon={<CopyOutlined />} onClick={() => copy(WEBHOOK_URL, 'url')}>
                {copied === 'url' ? 'Copied!' : 'Copy'}
              </Button>
            </div>
          </div>
          <Button icon={<SyncOutlined />} onClick={refetch} loading={isLoading}>
            Test Connection
          </Button>
        </Space>
      </Card>

      {/* Column Mapping */}
      <Card title={<><FileTextOutlined /> Column Mapping</>} style={{ marginBottom: 24 }}>
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: 12 }}
          message="Your sheet columns are matched automatically — headers are case-insensitive and multiple name variations are accepted. Any unrecognised column is safely ignored."
        />
        <Table
          dataSource={MAPPING_DATA}
          columns={mappingCols}
          rowKey="crm"
          size="small"
          pagination={false}
          rowClassName={r => r.required ? 'ant-table-row-selected' : ''}
        />
      </Card>

      {/* Apps Script */}
      <Card
        title={<><ThunderboltOutlined /> Apps Script Code</>}
        extra={
          <Button icon={<CopyOutlined />} type="primary"
            onClick={() => copy(APPS_SCRIPT, 'script')}>
            {copied === 'script' ? 'Copied!' : 'Copy Script'}
          </Button>
        }
        style={{ marginBottom: 24 }}
      >
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="Replace YOUR_SHEET_NAME if your tab is not called 'Sheet1'. The CRM URL and API key are already filled in." />
        <TextArea
          value={APPS_SCRIPT}
          readOnly
          autoSize={{ minRows: 20, maxRows: 40 }}
          style={{ fontFamily: 'monospace', fontSize: 12, background: '#1e1e1e', color: '#d4d4d4' }}
        />
      </Card>

      {/* Notes */}
      <Card title="How it works" size="small">
        <Paragraph>
          <ul style={{ paddingLeft: 20, lineHeight: 2 }}>
            <li><Text strong>Duplicate detection</Text> — rows with a phone or email already in the CRM are skipped.</li>
            <li><Text strong>Sync column</Text> — a <Text code>CRM Sync Status</Text> column is auto-added to your sheet; each row shows ✓ Synced, ↩ Skipped, or ✗ Error.</li>
            <li><Text strong>Re-sync</Text> — re-running the script only sends rows that are not yet marked ✓ Synced.</li>
            <li><Text strong>Assigned to</Text> — leads without an "Assigned To" column are assigned to the Super Admin.</li>
            <li><Text strong>Status values</Text> — Fresh, Follow Up, Warm, Hot, Enrolled, Will Enroll Later, Not Answering, Not Interested, Junk. Any unrecognised value defaults to <Text code>Fresh</Text>.</li>
            <li><Text strong>Auto-sync</Text> — run <Text code>setupTrigger()</Text> once to sync every hour automatically.</li>
          </ul>
        </Paragraph>
      </Card>
    </div>
  );
};

export default GoogleSheetSync;
