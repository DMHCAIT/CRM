import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Tag, 
  Switch, 
  Modal, 
  Form, 
  Input, 
  Select, 
  InputNumber,
  message,
  Tooltip,
  Divider,
  Alert,
  Typography,
  Row,
  Col,
  Collapse
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

const WorkflowSettings = () => {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/workflows`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      const data = await response.json();
      setWorkflows(data.workflows || []);
    } catch (error) {
      message.error('Failed to load workflows');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveWorkflow = async (values) => {
    setLoading(true);
    try {
      const workflow = {
        ...editingWorkflow,
        ...values,
        enabled: values.enabled !== false
      };

      const response = await fetch(`${process.env.REACT_APP_API_URL}/api/workflows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify(workflow)
      });

      if (response.ok) {
        message.success('Workflow saved successfully');
        setModalVisible(false);
        form.resetFields();
        setEditingWorkflow(null);
        fetchWorkflows();
      } else {
        message.error('Failed to save workflow');
      }
    } catch (error) {
      message.error('Error saving workflow');
    } finally {
      setLoading(false);
    }
  };

  const handleEditWorkflow = (workflow) => {
    setEditingWorkflow(workflow);
    form.setFieldsValue(workflow);
    setModalVisible(true);
  };

  const handleToggleWorkflow = async (workflow) => {
    const updated = {
      ...workflow,
      enabled: !workflow.enabled
    };

    setLoading(true);
    try {
      await fetch(`${process.env.REACT_APP_API_URL}/api/workflows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify(updated)
      });
      
      message.success(updated.enabled ? 'Workflow enabled' : 'Workflow disabled');
      fetchWorkflows();
    } catch (error) {
      message.error('Failed to update workflow');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Status',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={() => handleToggleWorkflow(record)}
          checkedChildren={<PlayCircleOutlined />}
          unCheckedChildren={<PauseCircleOutlined />}
        />
      )
    },
    {
      title: 'Workflow Name',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{name}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.description}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: 'Trigger',
      dataIndex: 'trigger',
      key: 'trigger',
      width: 150,
      render: (trigger, record) => (
        <Space direction="vertical" size={0}>
          <Tag color={trigger === 'status_change' ? 'blue' : 'green'}>
            {trigger === 'status_change' ? 'Status Change' : 'Custom Event'}
          </Tag>
          {record.statuses && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {record.statuses.join(', ')}
            </Text>
          )}
          {record.event_type && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {record.event_type}
            </Text>
          )}
        </Space>
      )
    },
    {
      title: 'Actions',
      dataIndex: 'actions',
      key: 'actions',
      width: 200,
      render: (actions = []) => (
        <Space direction="vertical" size={2}>
          {actions.map((action, idx) => (
            <Tag key={idx} color="processing" style={{ fontSize: 11 }}>
              {action.type.replace(/_/g, ' ')}
            </Tag>
          ))}
        </Space>
      )
    },
    {
      title: 'Conditions',
      dataIndex: 'conditions',
      key: 'conditions',
      width: 150,
      render: (conditions = {}) => {
        const conditionCount = Object.keys(conditions).length;
        return conditionCount > 0 ? (
          <Tooltip title={JSON.stringify(conditions, null, 2)}>
            <Tag color="orange">{conditionCount} condition(s)</Tag>
          </Tooltip>
        ) : (
          <Text type="secondary">No conditions</Text>
        );
      }
    },
    {
      title: 'Actions',
      key: 'operations',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button 
            size="small" 
            icon={<EditOutlined />}
            onClick={() => handleEditWorkflow(record)}
          >
            Edit
          </Button>
        </Space>
      )
    }
  ];

  const actionTypes = [
    { value: 'send_email', label: 'Send Email' },
    { value: 'send_whatsapp', label: 'Send WhatsApp' },
    { value: 'schedule_followup', label: 'Schedule Follow-up' },
    { value: 'create_task', label: 'Create Task' },
    { value: 'update_priority', label: 'Update Priority' },
    { value: 'assign_to', label: 'Auto-Assign' },
    { value: 'add_note', label: 'Add Note' },
    { value: 'webhook', label: 'Call Webhook' }
  ];

  const statusOptions = ['new', 'contacted', 'qualified', 'hot', 'warm', 'cold', 'not_answering', 'not_interested', 'enrolled', 'junk'];

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={18}>
          <Space direction="vertical" size={0}>
            <Title level={2}>
              <ThunderboltOutlined style={{ color: '#1890ff' }} /> Workflow Automation
            </Title>
            <Paragraph type="secondary">
              Configure automated workflows that trigger actions when lead status changes or custom events occur
            </Paragraph>
          </Space>
        </Col>
        <Col span={6} style={{ textAlign: 'right' }}>
          <Button 
            type="primary" 
            size="large"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingWorkflow(null);
              form.resetFields();
              setModalVisible(true);
            }}
          >
            Create Workflow
          </Button>
        </Col>
      </Row>

      {/* Info Alert */}
      <Alert
        message="About Workflow Automation"
        description={
          <div>
            <p>Workflows automatically execute actions when specific triggers occur:</p>
            <ul style={{ marginBottom: 0 }}>
              <li><strong>Status Change:</strong> When a lead's status changes (e.g., Hot → schedule call within 2 hours)</li>
              <li><strong>Custom Events:</strong> When events like high churn risk or lead inactivity are detected</li>
              <li><strong>Actions:</strong> Send emails/WhatsApp, schedule follow-ups, create tasks, reassign leads, etc.</li>
            </ul>
          </div>
        }
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        closable
        style={{ marginBottom: 24 }}
      />

      {/* Workflows Table */}
      <Card>
        <Table
          columns={columns}
          dataSource={workflows}
          loading={loading}
          rowKey="name"
          pagination={false}
        />
      </Card>

      {/* Workflow Editor Modal */}
      <Modal
        title={editingWorkflow ? `Edit Workflow: ${editingWorkflow.name}` : 'Create New Workflow'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingWorkflow(null);
        }}
        onOk={() => form.submit()}
        width={800}
        okText="Save Workflow"
        confirmLoading={loading}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveWorkflow}
          initialValues={{
            enabled: true,
            trigger: 'status_change',
            conditions: {},
            actions: []
          }}
        >
          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="name"
                label="Workflow Name"
                rules={[{ required: true, message: 'Please enter workflow name' }]}
              >
                <Input placeholder="e.g., Hot Lead Follow-up" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="enabled"
                label="Status"
                valuePropName="checked"
              >
                <Switch checkedChildren="Enabled" unCheckedChildren="Disabled" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={2} placeholder="Describe what this workflow does" />
          </Form.Item>

          <Divider>Trigger Configuration</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="trigger"
                label="Trigger Type"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="status_change">Status Change</Option>
                  <Option value="event">Custom Event</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) => prevValues.trigger !== currentValues.trigger}
              >
                {({ getFieldValue }) =>
                  getFieldValue('trigger') === 'status_change' ? (
                    <Form.Item
                      name="statuses"
                      label="Trigger on Status(es)"
                      rules={[{ required: true, message: 'Select at least one status' }]}
                    >
                      <Select mode="multiple" placeholder="Select statuses">
                        {statusOptions.map(status => (
                          <Option key={status} value={status}>{status}</Option>
                        ))}
                      </Select>
                    </Form.Item>
                  ) : (
                    <Form.Item
                      name="event_type"
                      label="Event Type"
                      rules={[{ required: true, message: 'Enter event type' }]}
                    >
                      <Input placeholder="e.g., high_churn_risk, lead_inactive" />
                    </Form.Item>
                  )
                }
              </Form.Item>
            </Col>
          </Row>

          <Divider>Conditions (Optional)</Divider>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name={['conditions', 'min_score']} label="Minimum AI Score">
                <InputNumber min={0} max={100} style={{ width: '100%' }} placeholder="e.g., 80" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name={['conditions', 'max_score']} label="Maximum AI Score">
                <InputNumber min={0} max={100} style={{ width: '100%' }} placeholder="e.g., 100" />
              </Form.Item>
            </Col>
          </Row>

          <Alert
            message="Note: Leave conditions empty to apply workflow to all matching triggers"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        </Form>

        <Divider>Actions to Execute</Divider>
        <Alert
          message="Action configuration is simplified in this version. Full visual action builder coming soon."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      </Modal>
    </div>
  );
};

export default WorkflowSettings;
