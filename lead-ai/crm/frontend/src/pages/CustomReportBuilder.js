import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Select, 
  Button, 
  Space, 
  Table, 
  DatePicker,
  Input,
  Row,
  Col,
  Divider,
  Tag,
  message,
  Modal,
  Checkbox
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  DownloadOutlined,
  SaveOutlined,
  FileExcelOutlined,
  FilePdfOutlined
} from '@ant-design/icons';
import api from '../api/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { Option } = Select;
const { TextArea } = Input;

/**
 * Custom Report Builder
 * Drag-and-drop style report creation with custom metrics and dimensions
 */
const CustomReportBuilder = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [savedReports, setSavedReports] = useState([]);
  const [selectedDimensions, setSelectedDimensions] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);

  // Available dimensions (group by fields)
  const dimensions = [
    { value: 'status', label: 'Lead Status' },
    { value: 'ai_segment', label: 'AI Segment' },
    { value: 'source', label: 'Lead Source' },
    { value: 'preferred_country', label: 'Country' },
    { value: 'course_interested', label: 'Course' },
    { value: 'assigned_to', label: 'Assigned Counselor' },
    { value: 'hospital_id', label: 'Hospital' },
    { value: 'created_month', label: 'Month Created' },
    { value: 'priority', label: 'Priority' }
  ];

  // Available metrics (calculated fields)
  const metrics = [
    { value: 'count', label: 'Lead Count', icon: '📊' },
    { value: 'avg_score', label: 'Average AI Score', icon: '⭐' },
    { value: 'conversion_rate', label: 'Conversion Rate', icon: '📈' },
    { value: 'enrolled_count', label: 'Enrollments', icon: '✅' },
    { value: 'contact_rate', label: 'Contact Rate', icon: '📞' },
    { value: 'avg_response_time', label: 'Avg Response Time', icon: '⏱️' },
    { value: 'revenue', label: 'Revenue', icon: '💰' }
  ];

  useEffect(() => {
    loadSavedReports();
  }, []);

  const loadSavedReports = () => {
    try {
      const saved = JSON.parse(localStorage.getItem('custom_reports') || '[]');
      setSavedReports(saved);
    } catch (error) {
      console.error('Failed to load saved reports:', error);
    }
  };

  const handleRunReport = async (values) => {
    setLoading(true);
    
    try {
      // Build report configuration
      const config = {
        dimensions: selectedDimensions,
        metrics: selectedMetrics,
        filters: {
          date_range: values.date_range ? {
            start: values.date_range[0].format('YYYY-MM-DD'),
            end: values.date_range[1].format('YYYY-MM-DD')
          } : null,
          status: values.status,
          ai_segment: values.ai_segment,
          source: values.source,
          country: values.country,
          course: values.course
        }
      };
      
      // For now, we'll generate report data client-side
      // In production, this would be a backend API call
      const response = await api.get('/api/leads', {
        params: {
          start_date: config.filters.date_range?.start,
          end_date: config.filters.date_range?.end,
          status: config.filters.status,
          segment: config.filters.ai_segment,
          limit: 10000
        }
      });
      
      const leads = response.data.leads || [];
      
      // Process data based on dimensions and metrics
      const processedData = processReportData(leads, config);
      
      setReportData({
        config,
        data: processedData,
        timestamp: new Date().toISOString()
      });
      
    } catch (error) {
      message.error('Failed to generate report');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const processReportData = (leads, config) => {
    if (config.dimensions.length === 0) {
      // No grouping - aggregate all
      return [{
        group: 'All Leads',
        ...calculateMetrics(leads, config.metrics)
      }];
    }
    
    // Group by first dimension
    const primaryDimension = config.dimensions[0];
    const grouped = {};
    
    leads.forEach(lead => {
      const key = lead[primaryDimension] || 'Unknown';
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(lead);
    });
    
    // Calculate metrics for each group
    return Object.entries(grouped).map(([group, groupLeads]) => ({
      group,
      dimension: primaryDimension,
      ...calculateMetrics(groupLeads, config.metrics)
    }));
  };

  const calculateMetrics = (leads, metrics) => {
    const result = {};
    
    metrics.forEach(metric => {
      switch (metric) {
        case 'count':
          result.count = leads.length;
          break;
        case 'avg_score':
          const scores = leads.map(l => l.ai_score || 0);
          result.avg_score = scores.length > 0 
            ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) 
            : 0;
          break;
        case 'conversion_rate':
          const enrolled = leads.filter(l => l.status === 'enrolled').length;
          result.conversion_rate = leads.length > 0 
            ? ((enrolled / leads.length) * 100).toFixed(2) 
            : 0;
          break;
        case 'enrolled_count':
          result.enrolled_count = leads.filter(l => l.status === 'enrolled').length;
          break;
        case 'contact_rate':
          const contacted = leads.filter(l => ['contacted', 'qualified', 'enrolled'].includes(l.status)).length;
          result.contact_rate = leads.length > 0 
            ? ((contacted / leads.length) * 100).toFixed(2) 
            : 0;
          break;
        case 'avg_response_time':
          const responseTimes = leads
            .filter(l => l.last_contacted && l.created_at)
            .map(l => (new Date(l.last_contacted) - new Date(l.created_at)) / (1000 * 60 * 60));
          result.avg_response_time = responseTimes.length > 0
            ? (responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length).toFixed(1)
            : 0;
          break;
        case 'revenue':
          result.revenue = leads.filter(l => l.status === 'enrolled').length * 5000; // Placeholder
          break;
      }
    });
    
    return result;
  };

  const handleSaveReport = () => {
    Modal.confirm({
      title: 'Save Report',
      content: (
        <Form layout="vertical">
          <Form.Item label="Report Name" name="name">
            <Input placeholder="e.g., Monthly Conversion by Source" id="report-name-input" />
          </Form.Item>
        </Form>
      ),
      onOk: () => {
        const nameInput = document.getElementById('report-name-input');
        const name = nameInput?.value || `Report ${savedReports.length + 1}`;
        
        const newReport = {
          id: Date.now(),
          name,
          config: reportData.config,
          created_at: new Date().toISOString()
        };
        
        const updated = [...savedReports, newReport];
        setSavedReports(updated);
        localStorage.setItem('custom_reports', JSON.stringify(updated));
        
        message.success('Report saved successfully');
      }
    });
  };

  const handleLoadReport = (report) => {
    setSelectedDimensions(report.config.dimensions);
    setSelectedMetrics(report.config.metrics);
    
    // Populate form
    form.setFieldsValue({
      dimensions: report.config.dimensions,
      metrics: report.config.metrics,
      ...report.config.filters
    });
    
    message.success(`Loaded report: ${report.name}`);
  };

  const handleExportCSV = () => {
    if (!reportData || !reportData.data) {
      message.warning('No data to export');
      return;
    }
    
    // Convert to CSV
    const headers = ['Group', ...selectedMetrics];
    const rows = reportData.data.map(row => [
      row.group,
      ...selectedMetrics.map(m => row[m] || '')
    ]);
    
    const csv = [
      headers.join(','),
      ...rows.map(r => r.join(','))
    ].join('\n');
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report-${Date.now()}.csv`;
    a.click();
    
    message.success('Report exported to CSV');
  };

  // Dynamic columns based on selected metrics
  const getTableColumns = () => {
    const cols = [
      {
        title: 'Group',
        dataIndex: 'group',
        key: 'group',
        fixed: 'left',
        render: (text) => <strong>{text}</strong>
      }
    ];
    
    selectedMetrics.forEach(metric => {
      const metricInfo = metrics.find(m => m.value === metric);
      cols.push({
        title: metricInfo?.label || metric,
        dataIndex: metric,
        key: metric,
        sorter: (a, b) => (parseFloat(a[metric]) || 0) - (parseFloat(b[metric]) || 0),
        render: (val) => {
          if (metric.includes('rate')) return `${val}%`;
          if (metric === 'revenue') return `$${val}`;
          if (metric === 'avg_response_time') return `${val}h`;
          return val;
        }
      });
    });
    
    return cols;
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>📊 Custom Report Builder</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        Create custom reports by selecting dimensions and metrics
      </p>

      <Row gutter={16}>
        {/* Report Configuration */}
        <Col xs={24} lg={8}>
          <Card title="Report Configuration">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleRunReport}
            >
              {/* Dimensions */}
              <Form.Item
                label="Dimensions (Group By)"
                name="dimensions"
                tooltip="Choose what to group your data by"
              >
                <Select
                  mode="multiple"
                  placeholder="Select dimensions"
                  value={selectedDimensions}
                  onChange={setSelectedDimensions}
                  maxTagCount={2}
                >
                  {dimensions.map(d => (
                    <Option key={d.value} value={d.value}>{d.label}</Option>
                  ))}
                </Select>
              </Form.Item>

              {/* Metrics */}
              <Form.Item
                label="Metrics (What to Measure)"
                name="metrics"
                tooltip="Choose what metrics to calculate"
                rules={[{ required: true, message: 'Select at least one metric' }]}
              >
                <Checkbox.Group
                  value={selectedMetrics}
                  onChange={setSelectedMetrics}
                  style={{ width: '100%' }}
                >
                  <Row>
                    {metrics.map(m => (
                      <Col span={24} key={m.value} style={{ marginBottom: 8 }}>
                        <Checkbox value={m.value}>
                          {m.icon} {m.label}
                        </Checkbox>
                      </Col>
                    ))}
                  </Row>
                </Checkbox.Group>
              </Form.Item>

              <Divider />

              {/* Filters */}
              <h4>Filters</h4>
              
              <Form.Item label="Date Range" name="date_range">
                <RangePicker format="MMM DD, YYYY" />
              </Form.Item>

              <Form.Item label="Status" name="status">
                <Select mode="multiple" placeholder="All statuses" allowClear>
                  <Option value="new">New</Option>
                  <Option value="contacted">Contacted</Option>
                  <Option value="qualified">Qualified</Option>
                  <Option value="enrolled">Enrolled</Option>
                  <Option value="lost">Lost</Option>
                </Select>
              </Form.Item>

              <Form.Item label="AI Segment" name="ai_segment">
                <Select mode="multiple" placeholder="All segments" allowClear>
                  <Option value="Hot">Hot</Option>
                  <Option value="Warm">Warm</Option>
                  <Option value="Cold">Cold</Option>
                </Select>
              </Form.Item>

              <Form.Item label="Source" name="source">
                <Select mode="multiple" placeholder="All sources" allowClear>
                  <Option value="Google Ads">Google Ads</Option>
                  <Option value="Facebook">Facebook</Option>
                  <Option value="Website">Website</Option>
                  <Option value="Referral">Referral</Option>
                  <Option value="Direct">Direct</Option>
                </Select>
              </Form.Item>

              <Form.Item>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  block 
                  loading={loading}
                  disabled={selectedMetrics.length === 0}
                >
                  Generate Report
                </Button>
              </Form.Item>
            </Form>

            {/* Saved Reports */}
            {savedReports.length > 0 && (
              <>
                <Divider />
                <h4>Saved Reports</h4>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {savedReports.map(report => (
                    <Button
                      key={report.id}
                      onClick={() => handleLoadReport(report)}
                      block
                      size="small"
                    >
                      {report.name}
                    </Button>
                  ))}
                </Space>
              </>
            )}
          </Card>
        </Col>

        {/* Report Results */}
        <Col xs={24} lg={16}>
          <Card 
            title="Report Results"
            extra={
              reportData && (
                <Space>
                  <Button 
                    icon={<SaveOutlined />} 
                    onClick={handleSaveReport}
                  >
                    Save Report
                  </Button>
                  <Button 
                    icon={<FileExcelOutlined />} 
                    onClick={handleExportCSV}
                  >
                    Export CSV
                  </Button>
                </Space>
              )
            }
          >
            {reportData ? (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <Tag>
                    Dimensions: {reportData.config.dimensions.join(', ') || 'None'}
                  </Tag>
                  <Tag>
                    Metrics: {reportData.config.metrics.join(', ')}
                  </Tag>
                  <Tag>
                    Generated: {new Date(reportData.timestamp).toLocaleString()}
                  </Tag>
                </div>

                <Table
                  columns={getTableColumns()}
                  dataSource={reportData.data}
                  rowKey="group"
                  pagination={{ pageSize: 20 }}
                  scroll={{ x: true }}
                />
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                <BarChartOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>Configure your report and click "Generate Report" to see results</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default CustomReportBuilder;
