import React, { useState } from 'react';
import {
  Card, Row, Col, Table, Tag, Avatar, Typography,
  Select, DatePicker, Button, Space, Tabs, Badge,
  Statistic, Timeline, Input, Empty, Spin,
} from 'antd';
import { useQuery } from '@tanstack/react-query';
import { monitoringAPI, usersAPI, leadsAPI } from '../api/api';
import {
  UserOutlined, PhoneOutlined, WhatsAppOutlined, MailOutlined,
  CommentOutlined, SwapOutlined, TeamOutlined, TrophyOutlined,
  CalendarOutlined, ReloadOutlined, FilterOutlined, SearchOutlined,
  FireOutlined, CheckCircleOutlined, EditOutlined, RiseOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, Legend, ResponsiveContainer, LineChart, Line, Cell,
} from 'recharts';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

// ── helpers ────────────────────────────────────────────────────────────────

const ACTIVITY_META = {
  call:          { color: '#1890ff', icon: <PhoneOutlined />,     label: 'Call' },
  whatsapp:      { color: '#25D366', icon: <WhatsAppOutlined />,  label: 'WhatsApp' },
  email:         { color: '#fa8c16', icon: <MailOutlined />,      label: 'Email' },
  note:          { color: '#722ed1', icon: <CommentOutlined />,   label: 'Note' },
  status_change: { color: '#eb2f96', icon: <SwapOutlined />,      label: 'Status Change' },
  assignment:    { color: '#13c2c2', icon: <UserOutlined />,      label: 'Assignment' },
  follow_up_set: { color: '#faad14', icon: <CalendarOutlined />,  label: 'Follow-up Set' },
  field_update:  { color: '#8c8c8c', icon: <EditOutlined />,      label: 'Field Update' },
  lead_created:  { color: '#52c41a', icon: <RiseOutlined />,      label: 'Lead Created' },
};

const getMeta = type => ACTIVITY_META[type] || { color: '#8c8c8c', icon: <EditOutlined />, label: type };

// ── component ───────────────────────────────────────────────────────────────

const UserActivityPage = () => {
  const [activeTab, setActiveTab] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(dayjs());
  const [selectedCounselor, setSelectedCounselor] = useState(null);
  const [summaryRange, setSummaryRange] = useState([dayjs().subtract(30, 'days'), dayjs()]);
  const [logFilters, setLogFilters] = useState({ activity_type: null, counselor: null, lead_id_filter: '' });

  // ── queries ──────────────────────────────────────────────────────────────

  const { data: usersData } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersAPI.getAll().then(r => r.data),
  });

  const { data: dailyData, isLoading: dailyLoading, refetch: refetchDaily } = useQuery({
    queryKey: ['monitoring-daily', selectedDate?.format('YYYY-MM-DD'), selectedCounselor],
    queryFn: () => monitoringAPI.getDailyActivity(
      selectedDate?.format('YYYY-MM-DD'),
      selectedCounselor || undefined
    ).then(r => r.data),
    enabled: !!selectedDate,
  });

  const { data: summaryData, isLoading: summaryLoading, refetch: refetchSummary } = useQuery({
    queryKey: ['monitoring-summary', summaryRange?.[0]?.toISOString(), summaryRange?.[1]?.toISOString()],
    queryFn: () => monitoringAPI.getCounselorSummary(
      summaryRange?.[0]?.toISOString(),
      summaryRange?.[1]?.toISOString()
    ).then(r => r.data),
    enabled: !!summaryRange,
  });

  const { data: logData, isLoading: logLoading, refetch: refetchLog } = useQuery({
    queryKey: ['monitoring-log', logFilters],
    queryFn: () => monitoringAPI.getActivityLog({
      ...logFilters,
      lead_id_filter: logFilters.lead_id_filter || undefined,
    }).then(r => r.data),
  });

  // ── helpers ───────────────────────────────────────────────────────────────

  const users = Array.isArray(usersData) ? usersData : (usersData?.users || []);
  const counselors = dailyData?.counselors || [];
  const allCounselors = summaryData?.counselors || [];

  // Build bar chart data for daily breakdown
  const dailyBarData = counselors.map(c => ({
    name: c.counselor.split(' ')[0],   // first name only for brevity
    Calls: c.calls,
    WhatsApp: c.whatsapp_sent,
    Email: c.emails_sent,
    Notes: c.notes_added,
    'Status Changes': c.status_changes,
  }));

  // ── columns ───────────────────────────────────────────────────────────────

  const dailyColumns = [
    {
      title: 'Counselor',
      dataIndex: 'counselor',
      key: 'counselor',
      render: name => (
        <Space>
          <Avatar style={{ backgroundColor: '#1890ff' }}>{(name || '?')[0].toUpperCase()}</Avatar>
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    { title: 'Calls', dataIndex: 'calls', key: 'calls',
      render: v => <Tag color="blue" icon={<PhoneOutlined />}>{v}</Tag> },
    { title: 'WhatsApp', dataIndex: 'whatsapp_sent', key: 'whatsapp_sent',
      render: v => <Tag color="green" icon={<WhatsAppOutlined />}>{v}</Tag> },
    { title: 'Emails', dataIndex: 'emails_sent', key: 'emails_sent',
      render: v => <Tag color="orange" icon={<MailOutlined />}>{v}</Tag> },
    { title: 'Notes', dataIndex: 'notes_added', key: 'notes_added',
      render: v => <Tag color="purple" icon={<CommentOutlined />}>{v}</Tag> },
    { title: 'Status Changes', dataIndex: 'status_changes', key: 'status_changes',
      render: v => <Tag color="magenta" icon={<SwapOutlined />}>{v}</Tag> },
    { title: 'Leads Touched', dataIndex: 'leads_touched', key: 'leads_touched',
      render: v => <Badge count={v} showZero style={{ backgroundColor: '#52c41a' }} /> },
    { title: 'Total Actions', dataIndex: 'total_actions', key: 'total_actions',
      sorter: (a, b) => a.total_actions - b.total_actions,
      defaultSortOrder: 'descend',
      render: v => <Text strong style={{ fontSize: 16, color: '#1890ff' }}>{v}</Text> },
  ];

  const summaryColumns = [
    {
      title: '#',
      key: 'rank',
      width: 50,
      render: (_, __, i) => (
        <Avatar size="small"
          style={{ backgroundColor: i === 0 ? '#faad14' : i === 1 ? '#bfbfbf' : i === 2 ? '#d48806' : '#1890ff' }}>
          {i + 1}
        </Avatar>
      ),
    },
    {
      title: 'Counselor',
      dataIndex: 'counselor',
      render: name => (
        <Space>
          <Avatar style={{ backgroundColor: '#1890ff' }}>{(name || '?')[0].toUpperCase()}</Avatar>
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    { title: 'Calls',   dataIndex: 'calls',    render: v => <Tag color="blue">{v}</Tag> },
    { title: 'WhatsApp',dataIndex: 'whatsapp', render: v => <Tag color="green">{v}</Tag> },
    { title: 'Emails',  dataIndex: 'emails',   render: v => <Tag color="orange">{v}</Tag> },
    { title: 'Notes',   dataIndex: 'notes',    render: v => <Tag color="purple">{v}</Tag> },
    { title: 'Status Updates', dataIndex: 'status_changes', render: v => <Tag color="magenta">{v}</Tag> },
    { title: 'Leads Touched', dataIndex: 'leads_touched',
      render: v => <Badge count={v} showZero style={{ backgroundColor: '#1890ff' }} /> },
    { title: 'Enrolled', dataIndex: 'enrolled',
      render: v => <Tag color="green" icon={<CheckCircleOutlined />}>{v}</Tag> },
    { title: 'Total', dataIndex: 'total_actions', sorter: (a, b) => a.total_actions - b.total_actions,
      defaultSortOrder: 'descend',
      render: v => <Text strong style={{ color: '#1890ff', fontSize: 16 }}>{v}</Text> },
  ];

  const logColumns = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'time',
      width: 160,
      render: t => dayjs(t).format('DD MMM HH:mm'),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 140,
      render: type => {
        const m = getMeta(type);
        return <Tag color={m.color} icon={m.icon}>{m.label}</Tag>;
      },
    },
    {
      title: 'Counselor',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 150,
      render: name => (
        <Space size={4}>
          <Avatar size="small" style={{ backgroundColor: '#1890ff' }}>{(name || '?')[0]}</Avatar>
          <Text>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'Lead',
      dataIndex: 'lead_id',
      key: 'lead_id',
      width: 120,
      render: (id, r) => (
        <div>
          <div style={{ fontWeight: 600, fontSize: 12 }}>{id}</div>
          <div style={{ fontSize: 11, color: '#8c8c8c' }}>{r.lead_name}</div>
        </div>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Team Monitoring</Title>
          <Text type="secondary">Track every action — calls, WhatsApp, emails, status changes</Text>
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          // ── Tab 1: Daily View ──────────────────────────────────────────────
          {
            key: 'daily',
            label: <span><CalendarOutlined /> Daily Activity</span>,
            children: (
              <div>
                {/* Controls */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Text strong><FilterOutlined /> Date:</Text>
                    <DatePicker
                      value={selectedDate}
                      onChange={setSelectedDate}
                      format="DD MMM YYYY"
                      allowClear={false}
                    />
                    <Text strong>Counselor:</Text>
                    <Select style={{ width: 200 }} placeholder="All counselors" allowClear
                      value={selectedCounselor} onChange={setSelectedCounselor}>
                      {users.map(u => <Option key={u.id} value={u.full_name}>{u.full_name}</Option>)}
                    </Select>
                    <Button icon={<ReloadOutlined />} onClick={refetchDaily}>Refresh</Button>
                  </Space>
                </Card>

                {/* Summary cards */}
                {!dailyLoading && dailyData && (
                  <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
                    {[
                      { label: 'Total Actions', value: counselors.reduce((s, c) => s + c.total_actions, 0), color: '#1890ff' },
                      { label: 'Calls Made',    value: counselors.reduce((s, c) => s + c.calls, 0),         color: '#1890ff', icon: <PhoneOutlined /> },
                      { label: 'WhatsApp Sent', value: counselors.reduce((s, c) => s + c.whatsapp_sent, 0), color: '#25D366', icon: <WhatsAppOutlined /> },
                      { label: 'Emails Sent',   value: counselors.reduce((s, c) => s + c.emails_sent, 0),   color: '#fa8c16', icon: <MailOutlined /> },
                      { label: 'Notes Added',   value: counselors.reduce((s, c) => s + c.notes_added, 0),   color: '#722ed1', icon: <CommentOutlined /> },
                      { label: 'Status Updates',value: counselors.reduce((s, c) => s + c.status_changes, 0),color: '#eb2f96', icon: <SwapOutlined /> },
                    ].map(card => (
                      <Col key={card.label} xs={12} sm={8} md={6} lg={4}>
                        <Card size="small" hoverable>
                          <Statistic title={card.label} value={card.value}
                            prefix={card.icon}
                            valueStyle={{ color: card.color, fontSize: 20, fontWeight: 700 }} />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                )}

                {/* Bar chart */}
                {!dailyLoading && dailyBarData.length > 0 && (
                  <Card title={`Activity Breakdown — ${selectedDate?.format('DD MMM YYYY')}`}
                    style={{ marginBottom: 16 }}>
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={dailyBarData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis allowDecimals={false} />
                        <RechartsTooltip />
                        <Legend />
                        <Bar dataKey="Calls"          fill="#1890ff" />
                        <Bar dataKey="WhatsApp"       fill="#25D366" />
                        <Bar dataKey="Email"          fill="#fa8c16" />
                        <Bar dataKey="Notes"          fill="#722ed1" />
                        <Bar dataKey="Status Changes" fill="#eb2f96" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                )}

                {/* Counselor table */}
                <Card title="Per-Counselor Breakdown">
                  {dailyLoading ? <Spin /> : counselors.length === 0 ? (
                    <Empty description={`No activity recorded on ${selectedDate?.format('DD MMM YYYY')}`} />
                  ) : (
                    <Table
                      dataSource={counselors}
                      columns={dailyColumns}
                      rowKey="counselor"
                      size="small"
                      pagination={false}
                      expandable={{
                        expandedRowRender: record => (
                          <Timeline style={{ padding: '12px 0' }}
                            items={record.actions.slice(0, 20).map(a => ({
                              color: getMeta(a.type).color,
                              dot: getMeta(a.type).icon,
                              children: (
                                <div>
                                  <Tag color={getMeta(a.type).color}>{getMeta(a.type).label}</Tag>
                                  <Text>{a.description}</Text>
                                  <div style={{ fontSize: 11, color: '#8c8c8c', marginTop: 2 }}>
                                    {dayjs(a.time).format('HH:mm')} · Lead #{a.lead_id}
                                  </div>
                                </div>
                              ),
                            }))}
                          />
                        ),
                        rowExpandable: r => r.actions?.length > 0,
                      }}
                    />
                  )}
                </Card>
              </div>
            ),
          },

          // ── Tab 2: Period Summary ──────────────────────────────────────────
          {
            key: 'summary',
            label: <span><TrophyOutlined /> Leaderboard</span>,
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Text strong>Period:</Text>
                    <RangePicker
                      value={summaryRange}
                      onChange={setSummaryRange}
                      format="DD MMM YYYY"
                      presets={[
                        { label: 'Today',      value: [dayjs(), dayjs()] },
                        { label: 'This Week',  value: [dayjs().startOf('week'), dayjs()] },
                        { label: 'Last 7 Days',value: [dayjs().subtract(7, 'day'), dayjs()] },
                        { label: 'Last 30 Days',value:[dayjs().subtract(30, 'day'), dayjs()] },
                        { label: 'This Month', value: [dayjs().startOf('month'), dayjs()] },
                      ]}
                    />
                    <Button icon={<ReloadOutlined />} onClick={refetchSummary}>Refresh</Button>
                  </Space>
                </Card>

                {/* Leaderboard bar chart */}
                {!summaryLoading && allCounselors.length > 0 && (
                  <Card title="Total Actions per Counselor" style={{ marginBottom: 16 }}>
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart data={allCounselors.map(c => ({
                        name: c.counselor.split(' ')[0],
                        Calls: c.calls, WhatsApp: c.whatsapp, Emails: c.emails,
                        Notes: c.notes, 'Status Chg': c.status_changes,
                      }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis allowDecimals={false} />
                        <RechartsTooltip />
                        <Legend />
                        <Bar dataKey="Calls"       fill="#1890ff" />
                        <Bar dataKey="WhatsApp"    fill="#25D366" />
                        <Bar dataKey="Emails"      fill="#fa8c16" />
                        <Bar dataKey="Notes"       fill="#722ed1" />
                        <Bar dataKey="Status Chg"  fill="#eb2f96" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Card>
                )}

                <Card title="Counselor Leaderboard">
                  {summaryLoading ? <Spin /> : (
                    <Table
                      dataSource={allCounselors}
                      columns={summaryColumns}
                      rowKey="counselor"
                      size="small"
                      pagination={{ pageSize: 20 }}
                    />
                  )}
                </Card>
              </div>
            ),
          },

          // ── Tab 3: Activity Log ────────────────────────────────────────────
          {
            key: 'log',
            label: <span><FilterOutlined /> Activity Log</span>,
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Text strong>Counselor:</Text>
                    <Select style={{ width: 180 }} placeholder="All" allowClear
                      value={logFilters.counselor}
                      onChange={v => setLogFilters(f => ({ ...f, counselor: v }))}>
                      {users.map(u => <Option key={u.id} value={u.full_name}>{u.full_name}</Option>)}
                    </Select>

                    <Text strong>Type:</Text>
                    <Select style={{ width: 160 }} placeholder="All types" allowClear
                      value={logFilters.activity_type}
                      onChange={v => setLogFilters(f => ({ ...f, activity_type: v }))}>
                      {Object.entries(ACTIVITY_META).map(([k, v]) => (
                        <Option key={k} value={k}><Tag color={v.color}>{v.label}</Tag></Option>
                      ))}
                    </Select>

                    <Text strong>Lead ID:</Text>
                    <Input style={{ width: 130 }} placeholder="LEAD00001" allowClear
                      value={logFilters.lead_id_filter}
                      onChange={e => setLogFilters(f => ({ ...f, lead_id_filter: e.target.value }))}
                      prefix={<SearchOutlined />}
                    />

                    <Button icon={<ReloadOutlined />} onClick={refetchLog}>Refresh</Button>
                  </Space>
                </Card>

                <Card title={`Activity Log${logData ? ` — ${logData.total} entries` : ''}`}>
                  {logLoading ? <Spin /> : (
                    <Table
                      dataSource={logData?.logs || []}
                      columns={logColumns}
                      rowKey="id"
                      size="small"
                      pagination={{ pageSize: 50, showTotal: t => `${t} entries` }}
                    />
                  )}
                </Card>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
};

export default UserActivityPage;
