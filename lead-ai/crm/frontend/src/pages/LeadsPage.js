import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Button,
  Tag,
  Space,
  Input,
  Select,
  DatePicker,
  Drawer,
  Form,
  message,
  Popconfirm,
  Row,
  Col,
  Card,
  Tooltip,
  Modal,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  WhatsAppOutlined,
  MailOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  PhoneOutlined,
  EditOutlined,
  CommentOutlined,
} from '@ant-design/icons';
import { leadsAPI, coursesAPI, counselorsAPI } from '../api/api';
import ChatInterface from '../components/ChatInterface';
import CallInterface from '../components/CallInterface';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { Text } = Typography;
const { TextArea } = Input;

// ── helpers ────────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  Fresh: 'cyan',
  'Follow Up': 'blue',
  Warm: 'orange',
  Hot: 'red',
  'Not Interested': 'default',
  Junk: 'default',
  'Not Answering': 'purple',
  Enrolled: 'green',
};

const COUNTRIES = [
  'India', 'UAE', 'Saudi Arabia', 'Kuwait', 'Oman', 'Qatar', 'Bahrain',
  'USA', 'UK', 'Canada', 'Australia', 'Germany', 'Singapore',
];

const SOURCES = [
  'Facebook', 'Instagram', 'Google Ads', 'YouTube', 'LinkedIn',
  'Website', 'Referral', 'WhatsApp', 'Cold Call', 'Walk In', 'Email Campaign',
];

const QUALIFICATIONS = [
  'MBBS', 'MD', 'MS', 'BDS', 'MDS', 'BAMS', 'BHMS', 'B.Sc Nursing',
  'M.Sc Nursing', 'BPT', 'MPT', 'DMLT', 'B.Pharma', 'M.Pharma', 'Other',
];

const STATUSES = [
  'Fresh', 'Follow Up', 'Warm', 'Hot', 'Enrolled',
  'Will Enroll Later', 'Not Answering', 'Not Interested', 'Junk',
];

const STATUS_COLORS_FULL = {
  Fresh: 'cyan',
  'Follow Up': 'blue',
  Warm: 'orange',
  Hot: 'red',
  Enrolled: 'green',
  'Will Enroll Later': 'purple',
  'Not Answering': 'geekblue',
  'Not Interested': 'default',
  Junk: 'default',
};

// ── component ───────────────────────────────────────────────────────────────

const LeadsPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [createDrawerOpen, setCreateDrawerOpen] = useState(false);
  const [editDrawerOpen, setEditDrawerOpen] = useState(false);
  const [filterDrawerOpen, setFilterDrawerOpen] = useState(false);
  const [notesModalOpen, setNotesModalOpen] = useState(false);

  const [selectedLead, setSelectedLead] = useState(null);
  const [filters, setFilters] = useState({});
  const [searchText, setSearchText] = useState('');

  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  // Communication
  const [chatVisible, setChatVisible] = useState(false);
  const [callVisible, setCallVisible] = useState(false);
  const [communicationType, setCommunicationType] = useState('whatsapp');

  // ── queries ──────────────────────────────────────────────────────────────

  const { data: leads = [], isLoading, refetch } = useQuery({
    queryKey: ['leads', filters],
    queryFn: () => leadsAPI.getAll(filters).then(r => r.data),
    keepPreviousData: true,
  });

  const { data: courses = [] } = useQuery({
    queryKey: ['courses'],
    queryFn: () => coursesAPI.getAll().then(r => r.data),
  });

  const { data: counselors = [] } = useQuery({
    queryKey: ['counselors'],
    queryFn: () => counselorsAPI.getAll().then(r => r.data),
  });

  // ── mutations ────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: data => leadsAPI.create(data),
    onSuccess: () => {
      message.success('Lead created successfully');
      setCreateDrawerOpen(false);
      createForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
    onError: err => message.error(`Failed: ${err.message}`),
  });

  const updateMutation = useMutation({
    mutationFn: ({ leadId, data }) => leadsAPI.update(leadId, data),
    onSuccess: () => {
      message.success('Lead updated');
      setEditDrawerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
    onError: err => message.error(`Failed: ${err.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: leadId => leadsAPI.delete(leadId),
    onSuccess: () => {
      message.success('Lead deleted');
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
    onError: err => message.error(`Failed: ${err.message}`),
  });

  const addNoteMutation = useMutation({
    mutationFn: ({ leadId, data }) => leadsAPI.addNote(leadId, data),
    onSuccess: () => {
      message.success('Note added');
      queryClient.invalidateQueries({ queryKey: ['leads'] });
    },
    onError: err => message.error(`Failed: ${err.message}`),
  });

  // ── handlers ─────────────────────────────────────────────────────────────

  const openEdit = lead => {
    setSelectedLead(lead);
    editForm.setFieldsValue({
      full_name: lead.full_name,
      email: lead.email,
      phone: lead.phone,
      whatsapp: lead.whatsapp,
      country: lead.country,
      branch: lead.branch,
      qualification: lead.qualification,
      source: lead.source,
      course_interested: lead.course_interested,
      company: lead.company,
      status: lead.status,
      assigned_to: lead.assigned_to,
      follow_up_date: lead.follow_up_date ? dayjs(lead.follow_up_date) : null,
    });
    setEditDrawerOpen(true);
  };

  const handleEdit = values => {
    const payload = { ...values };
    if (payload.follow_up_date) {
      payload.follow_up_date = payload.follow_up_date.toISOString();
    }
    updateMutation.mutate({ leadId: selectedLead.lead_id, data: payload });
  };

  const openNotes = lead => {
    setSelectedLead(lead);
    setNotesModalOpen(true);
  };

  const handleAddNote = values => {
    addNoteMutation.mutate({
      leadId: selectedLead.lead_id,
      data: { content: values.content, created_by: 'Counselor', channel: 'manual' },
    });
  };

  const handleFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value || undefined }));
  };

  const clearFilters = () => {
    setFilters({ _updatedMode: undefined });
    setSearchText('');
  };

  // client-side search across visible text fields
  const displayed = leads.filter(lead => {
    if (!searchText) return true;
    const q = searchText.toLowerCase();
    return (
      lead.full_name?.toLowerCase().includes(q) ||
      lead.phone?.toLowerCase().includes(q) ||
      lead.email?.toLowerCase().includes(q) ||
      lead.lead_id?.toLowerCase().includes(q) ||
      lead.company?.toLowerCase().includes(q) ||
      lead.branch?.toLowerCase().includes(q)
    );
  });

  // summary stats
  const totalRevenue = leads.reduce((s, l) => s + (l.actual_revenue || 0), 0);
  const hotLeads    = leads.filter(l => l.ai_segment === 'Hot').length;
  const enrolled    = leads.filter(l => l.status === 'Enrolled').length;
  const todayFollowups = leads.filter(l =>
    l.follow_up_date && dayjs(l.follow_up_date).isSame(dayjs(), 'day')
  ).length;

  // ── columns ───────────────────────────────────────────────────────────────

  const columns = [
    {
      title: 'ID',
      dataIndex: 'lead_id',
      key: 'lead_id',
      fixed: 'left',
      width: 110,
      render: text => (
        <a onClick={() => navigate(`/leads/${text}`)} style={{ fontWeight: 600, fontSize: 12 }}>
          {text}
        </a>
      ),
    },
    {
      title: 'Full Name',
      dataIndex: 'full_name',
      key: 'full_name',
      width: 170,
      sorter: (a, b) => a.full_name.localeCompare(b.full_name),
      render: (name, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{name}</div>
          {record.company && (
            <div style={{ fontSize: 11, color: '#8c8c8c' }}>{record.company}</div>
          )}
        </div>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 190,
      ellipsis: true,
      render: email => email || <Text type="secondary">—</Text>,
    },
    {
      title: 'Phone',
      dataIndex: 'phone',
      key: 'phone',
      width: 140,
    },
    {
      title: 'Country',
      dataIndex: 'country',
      key: 'country',
      width: 110,
      filters: [...new Set(leads.map(l => l.country))].map(c => ({ text: c, value: c })),
      onFilter: (v, r) => r.country === v,
    },
    {
      title: 'Branch',
      dataIndex: 'branch',
      key: 'branch',
      width: 130,
      render: v => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Qualification',
      dataIndex: 'qualification',
      key: 'qualification',
      width: 130,
      render: v => v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      width: 120,
      filters: SOURCES.map(s => ({ text: s, value: s })),
      onFilter: (v, r) => r.source === v,
      render: source => {
        const sourceColors = {
          Facebook: 'blue', Instagram: 'magenta', 'Google Ads': 'gold',
          YouTube: 'red', LinkedIn: 'geekblue', Website: 'cyan',
          Referral: 'green', WhatsApp: 'lime', 'Cold Call': 'orange',
          'Walk In': 'purple', 'Email Campaign': 'volcano',
        };
        return <Tag color={sourceColors[source] || 'default'}>{source}</Tag>;
      },
    },
    {
      title: 'Course',
      dataIndex: 'course_interested',
      key: 'course_interested',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      filters: STATUSES.map(s => ({ text: s, value: s })),
      onFilter: (v, r) => r.status === v,
      render: status => <Tag color={STATUS_COLORS_FULL[status] || STATUS_COLORS[status]}>{status}</Tag>,
    },
    {
      title: 'Assigned To',
      dataIndex: 'assigned_to',
      key: 'assigned_to',
      width: 140,
      render: v => v || <Text type="secondary">Unassigned</Text>,
    },
    {
      title: 'Follow Up',
      dataIndex: 'follow_up_date',
      key: 'follow_up_date',
      width: 130,
      sorter: (a, b) => new Date(a.follow_up_date || 0) - new Date(b.follow_up_date || 0),
      render: date => {
        if (!date) return <Text type="secondary">—</Text>;
        const d = dayjs(date);
        const isToday  = d.isSame(dayjs(), 'day');
        const isPast   = d.isBefore(dayjs(), 'day');
        return (
          <span style={{ color: isPast ? '#ff4d4f' : isToday ? '#faad14' : undefined, fontWeight: isToday ? 600 : undefined }}>
            {d.format('DD MMM YYYY')}
          </span>
        );
      },
    },
    {
      title: 'Company',
      dataIndex: 'company',
      key: 'company',
      width: 150,
      ellipsis: true,
      render: v => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Notes',
      key: 'notes',
      width: 100,
      render: (_, record) => {
        const count = record.notes?.length || 0;
        return (
          <Button
            type="text"
            size="small"
            icon={<CommentOutlined />}
            onClick={() => openNotes(record)}
            style={{ color: count > 0 ? '#1890ff' : '#8c8c8c' }}
          >
            {count > 0 ? count : 'Add'}
          </Button>
        );
      },
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      sorter: (a, b) => new Date(a.created_at) - new Date(b.created_at),
      defaultSortOrder: 'descend',
      render: date => dayjs(date).format('DD MMM YYYY'),
    },
    {
      title: 'Updated At',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 130,
      sorter: (a, b) => new Date(a.updated_at) - new Date(b.updated_at),
      render: date => date ? dayjs(date).format('DD MMM YYYY') : '—',
    },
    {
      title: 'Actions',
      key: 'actions',
      fixed: 'right',
      width: 180,
      render: (_, record) => (
        <Space size={2}>
          <Tooltip title="View Details">
            <Button type="text" size="small" icon={<EyeOutlined />}
              onClick={() => navigate(`/leads/${record.lead_id}`)} />
          </Tooltip>
          <Tooltip title="Edit">
            <Button type="text" size="small" icon={<EditOutlined />}
              onClick={() => openEdit(record)} />
          </Tooltip>
          <Tooltip title="Call">
            <Button type="text" size="small" icon={<PhoneOutlined style={{ color: '#1890ff' }} />}
              onClick={() => { setSelectedLead(record); setCallVisible(true); }}
              disabled={!record.phone} />
          </Tooltip>
          <Tooltip title="WhatsApp">
            <Button type="text" size="small" icon={<WhatsAppOutlined style={{ color: '#25D366' }} />}
              onClick={() => { setSelectedLead(record); setCommunicationType('whatsapp'); setChatVisible(true); }}
              disabled={!record.whatsapp} />
          </Tooltip>
          <Tooltip title="Email">
            <Button type="text" size="small" icon={<MailOutlined style={{ color: '#fa8c16' }} />}
              onClick={() => { setSelectedLead(record); setCommunicationType('email'); setChatVisible(true); }}
              disabled={!record.email} />
          </Tooltip>
          <Popconfirm
            title="Delete this lead?"
            onConfirm={() => deleteMutation.mutate(record.lead_id)}
            okText="Yes" cancelText="No"
          >
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // ── shared form fields ────────────────────────────────────────────────────

  const LeadFormFields = ({ forEdit = false }) => (
    <>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true }]}>
            <Input placeholder="Dr. Jane Smith" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="phone" label="Phone" rules={[{ required: true }]}>
            <Input placeholder="+91-9876543210" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="email" label="Email" rules={[{ type: 'email' }]}>
            <Input placeholder="jane@hospital.com" />
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="whatsapp" label="WhatsApp">
            <Input placeholder="+91-9876543210" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="country" label="Country" rules={[{ required: true }]}>
            <Select placeholder="Select country" showSearch>
              {COUNTRIES.map(c => <Option key={c} value={c}>{c}</Option>)}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="branch" label="Branch">
            <Input placeholder="e.g. Delhi, Mumbai, Hyderabad" />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="qualification" label="Qualification">
            <Select placeholder="Select qualification" showSearch allowClear>
              {QUALIFICATIONS.map(q => <Option key={q} value={q}>{q}</Option>)}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="company" label="Company / Hospital">
            <Input placeholder="Apollo Hospitals, AIIMS..." />
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="source" label="Source" rules={[{ required: true }]}>
            <Select placeholder="Select source">
              {SOURCES.map(s => <Option key={s} value={s}>{s}</Option>)}
            </Select>
          </Form.Item>
        </Col>
        <Col span={12}>
          <Form.Item name="course_interested" label="Course" rules={[{ required: true }]}>
            <Select placeholder="Select course" showSearch>
              {courses.map(c => (
                <Option key={c.id} value={c.course_name}>
                  {c.course_name} — ₹{(c.price / 1000).toFixed(0)}K
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Col>
      </Row>
      <Row gutter={16}>
        <Col span={12}>
          <Form.Item name="assigned_to" label="Assigned To">
            <Select placeholder="Select counselor" allowClear showSearch>
              {counselors.map(c => <Option key={c.id} value={c.name}>{c.name}</Option>)}
            </Select>
          </Form.Item>
        </Col>
        {forEdit && (
          <Col span={12}>
            <Form.Item name="status" label="Status">
              <Select placeholder="Select status">
                {STATUSES.map(s => <Option key={s} value={s}>{s}</Option>)}
              </Select>
            </Form.Item>
          </Col>
        )}
      </Row>
      {forEdit && (
        <Row gutter={16}>
          <Col span={12}>
            <Form.Item name="follow_up_date" label="Follow Up Date">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="source" label="Source">
              <Select placeholder="Select source">
                {SOURCES.map(s => <Option key={s} value={s}>{s}</Option>)}
              </Select>
            </Form.Item>
          </Col>
        </Row>
      )}
      {!forEdit && (
        <Form.Item name="notes_text" label="Initial Notes">
          <TextArea rows={3} placeholder="Add any notes about this lead..." />
        </Form.Item>
      )}
    </>
  );

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, margin: 0 }}>Leads Management</h1>
        <Space>
          <Input
            placeholder="Search by name, phone, email, company..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 280 }}
            allowClear
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh</Button>
          <Button icon={<FilterOutlined />} onClick={() => setFilterDrawerOpen(true)}>Filters</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateDrawerOpen(true)}>
            Add Lead
          </Button>
        </Space>
      </div>

      {/* Summary Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Leads',     value: leads.length,    color: '#1890ff' },
          { label: 'Hot Leads',       value: hotLeads,        color: '#ff4d4f' },
          { label: 'Enrolled',        value: enrolled,        color: '#52c41a' },
          { label: "Today's Follow Ups", value: todayFollowups, color: '#faad14' },
          { label: 'Total Revenue',   value: `₹${(totalRevenue / 100000).toFixed(2)}L`, color: '#722ed1' },
        ].map(card => (
          <Col key={card.label} xs={24} sm={12} md={8} lg={6} xl={5}>
            <Card size="small" hoverable>
              <div style={{ fontSize: 13, color: '#8c8c8c' }}>{card.label}</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: card.color }}>{card.value}</div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Table */}
      <Table
        dataSource={displayed}
        columns={columns}
        loading={isLoading}
        rowKey="id"
        size="small"
        scroll={{ x: 2400 }}
        pagination={{
          pageSize: 25,
          showSizeChanger: true,
          pageSizeOptions: ['25', '50', '100'],
          showTotal: total => `${total} leads`,
        }}
      />

      {/* ── Create Lead Drawer ── */}
      <Drawer
        title="Add New Lead"
        width={720}
        open={createDrawerOpen}
        onClose={() => { setCreateDrawerOpen(false); createForm.resetFields(); }}
        bodyStyle={{ paddingBottom: 80 }}
      >
        <Form form={createForm} layout="vertical" onFinish={v => createMutation.mutate(v)}>
          <LeadFormFields forEdit={false} />
          <Space>
            <Button type="primary" htmlType="submit" loading={createMutation.isLoading}>
              Create Lead
            </Button>
            <Button onClick={() => { setCreateDrawerOpen(false); createForm.resetFields(); }}>
              Cancel
            </Button>
          </Space>
        </Form>
      </Drawer>

      {/* ── Edit Lead Drawer ── */}
      <Drawer
        title={`Edit Lead — ${selectedLead?.lead_id || ''}`}
        width={720}
        open={editDrawerOpen}
        onClose={() => setEditDrawerOpen(false)}
        bodyStyle={{ paddingBottom: 80 }}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <LeadFormFields forEdit={true} />
          <Space>
            <Button type="primary" htmlType="submit" loading={updateMutation.isLoading}>
              Save Changes
            </Button>
            <Button onClick={() => setEditDrawerOpen(false)}>Cancel</Button>
          </Space>
        </Form>
      </Drawer>

      {/* ── Filter Drawer ── */}
      <Drawer
        title="Filter Leads"
        width={380}
        open={filterDrawerOpen}
        onClose={() => setFilterDrawerOpen(false)}
        extra={<Button size="small" onClick={clearFilters}>Clear All</Button>}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">

          {/* Status */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Status</div>
            <Select style={{ width: '100%' }} placeholder="All Status" allowClear
              value={filters.status} onChange={v => handleFilter('status', v)}>
              {STATUSES.map(s => (
                <Option key={s} value={s}>
                  <Tag color={STATUS_COLORS_FULL[s]} style={{ marginRight: 6 }}>{s}</Tag>
                </Option>
              ))}
            </Select>
          </div>

          {/* Country */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Country</div>
            <Select style={{ width: '100%' }} placeholder="All countries" allowClear showSearch
              value={filters.country} onChange={v => handleFilter('country', v)}>
              {COUNTRIES.map(c => <Option key={c} value={c}>{c}</Option>)}
            </Select>
          </div>

          {/* Source */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Source</div>
            <Select style={{ width: '100%' }} placeholder="All sources" allowClear
              value={filters.source} onChange={v => handleFilter('source', v)}>
              {SOURCES.map(s => <Option key={s} value={s}>{s}</Option>)}
            </Select>
          </div>

          {/* Assigned To */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Assigned To</div>
            <Select style={{ width: '100%' }} placeholder="All counselors" allowClear showSearch
              value={filters.assigned_to} onChange={v => handleFilter('assigned_to', v)}>
              {counselors.map(c => <Option key={c.id} value={c.name}>{c.name}</Option>)}
            </Select>
          </div>

          {/* Follow-up Range */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Follow-up Date</div>
            <RangePicker style={{ width: '100%' }} onChange={dates => {
              if (dates) {
                handleFilter('follow_up_from', dates[0].toISOString());
                handleFilter('follow_up_to', dates[1].toISOString());
              } else {
                handleFilter('follow_up_from', undefined);
                handleFilter('follow_up_to', undefined);
              }
            }} />
          </div>

          {/* Created Range */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Created Date</div>
            <RangePicker style={{ width: '100%' }} onChange={dates => {
              if (dates) {
                handleFilter('created_from', dates[0].toISOString());
                handleFilter('created_to', dates[1].toISOString());
              } else {
                handleFilter('created_from', undefined);
                handleFilter('created_to', undefined);
              }
            }} />
          </div>

          {/* Updated At — on / after / before */}
          <div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>Updated At</div>
            <Select
              style={{ width: '100%', marginBottom: 8 }}
              placeholder="Filter type"
              allowClear
              value={filters._updatedMode}
              onChange={mode => {
                setFilters(prev => ({
                  ...prev,
                  _updatedMode: mode,
                  updated_on: undefined,
                  updated_after: undefined,
                  updated_before: undefined,
                }));
              }}
            >
              <Option value="on">On (exact date)</Option>
              <Option value="after">After date</Option>
              <Option value="before">Before date</Option>
            </Select>
            {filters._updatedMode && (
              <DatePicker
                style={{ width: '100%' }}
                onChange={date => {
                  if (!date) {
                    setFilters(prev => ({
                      ...prev,
                      updated_on: undefined,
                      updated_after: undefined,
                      updated_before: undefined,
                    }));
                    return;
                  }
                  if (filters._updatedMode === 'on') {
                    handleFilter('updated_on', date.format('YYYY-MM-DD'));
                    handleFilter('updated_after', undefined);
                    handleFilter('updated_before', undefined);
                  } else if (filters._updatedMode === 'after') {
                    handleFilter('updated_after', date.startOf('day').toISOString());
                    handleFilter('updated_on', undefined);
                    handleFilter('updated_before', undefined);
                  } else {
                    handleFilter('updated_before', date.endOf('day').toISOString());
                    handleFilter('updated_on', undefined);
                    handleFilter('updated_after', undefined);
                  }
                }}
              />
            )}
          </div>

          <Button block type="default" onClick={clearFilters}>Clear All Filters</Button>
        </Space>
      </Drawer>

      {/* ── Notes Modal ── */}
      <Modal
        title={`Notes — ${selectedLead?.full_name || ''}`}
        open={notesModalOpen}
        onCancel={() => { setNotesModalOpen(false); setSelectedLead(null); }}
        footer={null}
        width={560}
      >
        {/* Existing notes */}
        <div style={{ maxHeight: 300, overflowY: 'auto', marginBottom: 16 }}>
          {(selectedLead?.notes || []).length === 0 ? (
            <Text type="secondary">No notes yet.</Text>
          ) : (
            [...(selectedLead?.notes || [])].reverse().map(note => (
              <Card key={note.id} size="small" style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 13 }}>{note.content}</div>
                <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 4 }}>
                  {note.created_by} · {dayjs(note.created_at).format('DD MMM YYYY HH:mm')} · {note.channel}
                </div>
              </Card>
            ))
          )}
        </div>
        {/* Add note */}
        <Form layout="vertical" onFinish={handleAddNote}>
          <Form.Item name="content" label="Add Note" rules={[{ required: true, message: 'Enter a note' }]}>
            <TextArea rows={3} placeholder="Write your note here..." />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={addNoteMutation.isLoading}>
            Add Note
          </Button>
        </Form>
      </Modal>

      {/* Chat Interface */}
      <ChatInterface
        visible={chatVisible}
        onClose={() => { setChatVisible(false); setSelectedLead(null); }}
        lead={selectedLead}
        type={communicationType}
      />

      {/* Call Interface */}
      <CallInterface
        visible={callVisible}
        onClose={() => { setCallVisible(false); setSelectedLead(null); }}
        lead={selectedLead}
      />
    </div>
  );
};

export default LeadsPage;
