import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  InputNumber,
  Select, 
  Button, 
  Space, 
  Table, 
  Tag,
  message,
  Modal,
  Divider,
  Row,
  Col,
  Statistic,
  Progress
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  TeamOutlined,
  FilterOutlined,
  SaveOutlined,
  ExportOutlined
} from '@ant-design/icons';
import api from '../api/api';

const { Option } = Select;
const { TextArea } = Input;

/**
 * Advanced Segmentation System
 * Create, save, and manage custom lead segments with complex filters
 */
const AdvancedSegmentation = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [segments, setSegments] = useState([]);
  const [selectedSegment, setSelectedSegment] = useState(null);
  const [segmentPreview, setSegmentPreview] = useState(null);

  useEffect(() => {
    loadSavedSegments();
  }, []);

  const loadSavedSegments = () => {
    try {
      const saved = JSON.parse(localStorage.getItem('custom_segments') || '[]');
      setSegments(saved);
    } catch (error) {
      console.error('Failed to load segments:', error);
    }
  };

  const handlePreviewSegment = async (values) => {
    setLoading(true);
    
    try {
      const filters = {
        status: values.status,
        ai_segment: values.ai_segment,
        score_min: values.score_min,
        score_max: values.score_max,
        countries: values.countries,
        courses: values.courses,
        source: values.source,
        days_inactive_min: values.days_inactive_min
      };
      
      // Call analytics engine to create segment
      const response = await api.post('/api/analytics/segments', {
        name: values.name || 'Preview Segment',
        filters
      });
      
      setSegmentPreview(response.data);
      message.success(`Segment preview generated: ${response.data.total_leads} leads match`);
      
    } catch (error) {
      message.error('Failed to preview segment');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSegment = async (values) => {
    try {
      const filters = {
        status: values.status,
        ai_segment: values.ai_segment,
        score_min: values.score_min,
        score_max: values.score_max,
        countries: values.countries,
        courses: values.courses,
        source: values.source,
        days_inactive_min: values.days_inactive_min
      };
      
      // Call API to create segment
      const response = await api.post('/api/analytics/segments', {
        name: values.name,
        filters
      });
      
      // Save to local storage
      const newSegment = {
        id: Date.now(),
        ...response.data
      };
      
      const updated = [...segments, newSegment];
      setSegments(updated);
      localStorage.setItem('custom_segments', JSON.stringify(updated));
      
      message.success(`Segment "${values.name}" saved successfully`);
      form.resetFields();
      setSegmentPreview(null);
      
    } catch (error) {
      message.error('Failed to save segment');
      console.error(error);
    }
  };

  const handleLoadSegment = (segment) => {
    form.setFieldsValue({
      name: segment.name,
      ...segment.filters
    });
    setSelectedSegment(segment);
    setSegmentPreview(segment);
    message.success(`Loaded segment: ${segment.name}`);
  };

  const handleDeleteSegment = (segmentId) => {
    Modal.confirm({
      title: 'Delete Segment',
      content: 'Are you sure you want to delete this segment?',
      okText: 'Delete',
      okType: 'danger',
      onOk: () => {
        const updated = segments.filter(s => s.id !== segmentId);
        setSegments(updated);
        localStorage.setItem('custom_segments', JSON.stringify(updated));
        message.success('Segment deleted');
      }
    });
  };

  const handleExportSegment = async (segment) => {
    message.info('Exporting segment... (Feature coming soon)');
    // Would call API to export segment leads to CSV
  };

  const segmentColumns = [
    {
      title: 'Segment Name',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <strong>{name}</strong>
    },
    {
      title: 'Total Leads',
      dataIndex: 'total_leads',
      key: 'total_leads',
      render: (val) => <Tag color="blue">{val}</Tag>
    },
    {
      title: 'Enrolled',
      dataIndex: 'enrolled',
      key: 'enrolled',
      render: (val) => <Tag color="success">{val}</Tag>
    },
    {
      title: 'Conversion Rate',
      dataIndex: 'conversion_rate',
      key: 'conversion_rate',
      render: (rate) => (
        <Progress 
          percent={rate} 
          size="small" 
          status={rate >= 15 ? 'success' : 'normal'}
        />
      )
    },
    {
      title: 'Avg Score',
      dataIndex: 'avg_score',
      key: 'avg_score'
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString()
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            size="small" 
            onClick={() => handleLoadSegment(record)}
          >
            Load
          </Button>
          <Button 
            size="small" 
            icon={<ExportOutlined />}
            onClick={() => handleExportSegment(record)}
          >
            Export
          </Button>
          <Button 
            size="small" 
            danger 
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteSegment(record.id)}
          />
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <h1><FilterOutlined /> Advanced Segmentation</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        Create and manage custom lead segments based on multiple criteria
      </p>

      <Row gutter={16}>
        {/* Segment Builder */}
        <Col xs={24} lg={10}>
          <Card title="Create New Segment">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSaveSegment}
            >
              <Form.Item
                label="Segment Name"
                name="name"
                rules={[{ required: true, message: 'Please enter a name' }]}
              >
                <Input placeholder="e.g., High-Value UK Leads" />
              </Form.Item>

              <Divider>Lead Criteria</Divider>

              <Form.Item label="Lead Status" name="status">
                <Select mode="multiple" placeholder="All statuses" allowClear>
                  <Option value="new">New</Option>
                  <Option value="contacted">Contacted</Option>
                  <Option value="qualified">Qualified</Option>
                  <Option value="warm">Warm</Option>
                  <Option value="hot">Hot</Option>
                  <Option value="cold">Cold</Option>
                  <Option value="not_answering">Not Answering</Option>
                  <Option value="enrolled">Enrolled</Option>
                  <Option value="lost">Lost</Option>
                </Select>
              </Form.Item>

              <Form.Item label="AI Segment" name="ai_segment">
                <Select mode="multiple" placeholder="All segments" allowClear>
                  <Option value="Hot">🔥 Hot</Option>
                  <Option value="Warm">🌡️ Warm</Option>
                  <Option value="Cold">❄️ Cold</Option>
                </Select>
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item label="Min AI Score" name="score_min">
                    <InputNumber 
                      min={0} 
                      max={100} 
                      style={{ width: '100%' }}
                      placeholder="0"
                    />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item label="Max AI Score" name="score_max">
                    <InputNumber 
                      min={0} 
                      max={100} 
                      style={{ width: '100%' }}
                      placeholder="100"
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item label="Countries" name="countries">
                <Select mode="multiple" placeholder="All countries" allowClear>
                  <Option value="UK">UK</Option>
                  <Option value="USA">USA</Option>
                  <Option value="Canada">Canada</Option>
                  <Option value="Australia">Australia</Option>
                  <Option value="Germany">Germany</Option>
                  <Option value="Ireland">Ireland</Option>
                </Select>
              </Form.Item>

              <Form.Item label="Courses" name="courses">
                <Select mode="multiple" placeholder="All courses" allowClear>
                  <Option value="MBBS">MBBS</Option>
                  <Option value="BDS">BDS</Option>
                  <Option value="Nursing">Nursing</Option>
                  <Option value="Pharmacy">Pharmacy</Option>
                  <Option value="Physiotherapy">Physiotherapy</Option>
                </Select>
              </Form.Item>

              <Form.Item label="Lead Source" name="source">
                <Select mode="multiple" placeholder="All sources" allowClear>
                  <Option value="Google Ads">Google Ads</Option>
                  <Option value="Facebook">Facebook</Option>
                  <Option value="Instagram">Instagram</Option>
                  <Option value="Website">Website</Option>
                  <Option value="Referral">Referral</Option>
                  <Option value="Direct">Direct</Option>
                </Select>
              </Form.Item>

              <Form.Item 
                label="Days Inactive (Minimum)" 
                name="days_inactive_min"
                tooltip="Find leads with no activity for at least this many days"
              >
                <InputNumber 
                  min={0} 
                  style={{ width: '100%' }}
                  placeholder="e.g., 30"
                />
              </Form.Item>

              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                <Button 
                  onClick={() => handlePreviewSegment(form.getFieldsValue())}
                  loading={loading}
                >
                  Preview Segment
                </Button>
                <Button 
                  type="primary" 
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  disabled={!segmentPreview}
                >
                  Save Segment
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        {/* Preview & Saved Segments */}
        <Col xs={24} lg={14}>
          {/* Preview */}
          {segmentPreview && (
            <Card title="Segment Preview" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={12} md={6}>
                  <Statistic
                    title="Total Leads"
                    value={segmentPreview.total_leads}
                    prefix={<TeamOutlined />}
                    valueStyle={{ color: '#1890ff' }}
                  />
                </Col>
                <Col xs={12} md={6}>
                  <Statistic
                    title="Enrolled"
                    value={segmentPreview.enrolled}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col xs={12} md={6}>
                  <Statistic
                    title="Conversion Rate"
                    value={segmentPreview.conversion_rate}
                    suffix="%"
                    valueStyle={{ color: '#faad14' }}
                  />
                </Col>
                <Col xs={12} md={6}>
                  <Statistic
                    title="Avg Score"
                    value={segmentPreview.avg_score}
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Col>
              </Row>

              <Divider />

              <div>
                <strong>Applied Filters:</strong>
                <div style={{ marginTop: 8 }}>
                  {segmentPreview.filters && Object.entries(segmentPreview.filters).map(([key, value]) => {
                    if (value && value.length > 0) {
                      return (
                        <Tag key={key} color="blue" style={{ marginBottom: 4 }}>
                          {key}: {Array.isArray(value) ? value.join(', ') : value}
                        </Tag>
                      );
                    }
                    return null;
                  })}
                </div>
              </div>
            </Card>
          )}

          {/* Saved Segments */}
          <Card title={`Saved Segments (${segments.length})`}>
            {segments.length > 0 ? (
              <Table
                columns={segmentColumns}
                dataSource={segments}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                <FilterOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <p>No saved segments yet</p>
                <p>Create your first segment using the form on the left</p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdvancedSegmentation;
