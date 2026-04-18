import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Table, 
  Tag, 
  Progress, 
  Alert,
  Button,
  Space,
  Descriptions,
  Tabs,
  Empty
} from 'antd';
import {
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  DatabaseOutlined,
  TeamOutlined,
  MailOutlined,
  WhatsAppOutlined
} from '@ant-design/icons';
import api from '../api/api';

const { TabPane } = Tabs;

/**
 * Performance Monitoring Dashboard
 * Real-time system health and background task monitoring
 */
const PerformanceMonitoring = () => {
  const [loading, setLoading] = useState(false);
  const [activeTasks, setActiveTasks] = useState(null);
  const [taskStats, setTaskStats] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(null);

  useEffect(() => {
    fetchAllStats();
    
    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchAllStats, 10000);
    setRefreshInterval(interval);
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const fetchAllStats = async () => {
    try {
      const [tasksRes, statsRes, cacheRes] = await Promise.all([
        api.get('/api/tasks/active').catch(() => ({ data: null })),
        api.get('/api/tasks/stats').catch(() => ({ data: null })),
        api.get('/api/cache/stats').catch(() => ({ data: null }))
      ]);
      
      setActiveTasks(tasksRes.data);
      setTaskStats(statsRes.data);
      setCacheStats(cacheRes.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    fetchAllStats().finally(() => setLoading(false));
  };

  const handleCancelTask = async (taskId) => {
    try {
      await api.post(`/api/tasks/${taskId}/cancel`);
      message.success('Task cancelled successfully');
      fetchAllStats();
    } catch (error) {
      message.error('Failed to cancel task');
    }
  };

  // Parse active tasks
  const activeTasksList = React.useMemo(() => {
    if (!activeTasks || !activeTasks.active) return [];
    
    const tasks = [];
    Object.entries(activeTasks.active).forEach(([worker, workerTasks]) => {
      workerTasks.forEach(task => {
        tasks.push({
          ...task,
          worker: worker
        });
      });
    });
    return tasks;
  }, [activeTasks]);

  // Task table columns
  const taskColumns = [
    {
      title: 'Task ID',
      dataIndex: 'id',
      key: 'id',
      render: (id) => <code style={{ fontSize: 11 }}>{id?.substring(0, 8)}...</code>
    },
    {
      title: 'Task Name',
      dataIndex: 'name',
      key: 'name',
      render: (name) => {
        const shortName = name?.split('.').pop() || name;
        return <Tag color="blue">{shortName}</Tag>;
      }
    },
    {
      title: 'Worker',
      dataIndex: 'worker',
      key: 'worker',
      render: (worker) => worker?.split('@')[0]
    },
    {
      title: 'Args',
      dataIndex: 'args',
      key: 'args',
      render: (args) => JSON.stringify(args || []).substring(0, 50) + '...'
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Button 
          size="small" 
          danger
          onClick={() => handleCancelTask(record.id)}
        >
          Cancel
        </Button>
      )
    }
  ];

  // Cache stats summary
  const cacheMetrics = React.useMemo(() => {
    if (!cacheStats || !cacheStats.caches) return [];
    
    return Object.entries(cacheStats.caches).map(([name, stats]) => ({
      name,
      hits: stats.hits || 0,
      misses: stats.misses || 0,
      size: stats.size || 0,
      hitRate: stats.hits ? ((stats.hits / (stats.hits + stats.misses)) * 100).toFixed(1) : 0
    }));
  }, [cacheStats]);

  // Worker stats
  const workerStats = React.useMemo(() => {
    if (!taskStats || !taskStats.stats) return [];
    
    return Object.entries(taskStats.stats).map(([worker, stats]) => {
      const totalKeys = Object.keys(stats.total || {});
      const completedCount = totalKeys.reduce((sum, key) => sum + (stats.total[key] || 0), 0);
      
      return {
        worker: worker.split('@')[0],
        pool: stats.pool?.['max-concurrency'] || 0,
        completed: completedCount || 0
      };
    });
  }, [taskStats]);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>⚡ Performance Monitoring</h1>
        <Button 
          icon={<SyncOutlined spin={loading} />}
          onClick={handleRefresh}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      {/* Summary Statistics */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Active Tasks"
              value={activeTasksList.length}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Workers Online"
              value={workerStats.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Cache Hit Rate"
              value={cacheMetrics.length > 0 
                ? (cacheMetrics.reduce((sum, c) => sum + parseFloat(c.hitRate), 0) / cacheMetrics.length).toFixed(1)
                : 0
              }
              suffix="%"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="System Status"
              value="Healthy"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Detailed Tabs */}
      <Card>
        <Tabs defaultActiveKey="tasks">
          <TabPane tab={`Active Tasks (${activeTasksList.length})`} key="tasks">
            {activeTasksList.length > 0 ? (
              <Table
                columns={taskColumns}
                dataSource={activeTasksList}
                rowKey="id"
                pagination={{ pageSize: 10 }}
                size="small"
              />
            ) : (
              <Empty description="No active tasks" />
            )}
          </TabPane>

          <TabPane tab="Workers" key="workers">
            <Row gutter={[16, 16]}>
              {workerStats.map(worker => (
                <Col xs={24} md={12} key={worker.worker}>
                  <Card size="small">
                    <Descriptions title={worker.worker} column={1} size="small">
                      <Descriptions.Item label="Max Concurrency">
                        {worker.pool}
                      </Descriptions.Item>
                      <Descriptions.Item label="Tasks Completed">
                        <Tag color="green">{worker.completed}</Tag>
                      </Descriptions.Item>
                      <Descriptions.Item label="Status">
                        <Tag color="success" icon={<CheckCircleOutlined />}>
                          Online
                        </Tag>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
              ))}
              
              {workerStats.length === 0 && (
                <Col span={24}>
                  <Alert
                    message="No Workers Detected"
                    description="Celery workers are not running. Start workers with: celery -A celery_config worker -l info"
                    type="warning"
                    showIcon
                  />
                </Col>
              )}
            </Row>
          </TabPane>

          <TabPane tab="Cache Performance" key="cache">
            <Row gutter={[16, 16]}>
              {cacheMetrics.map(cache => (
                <Col xs={24} md={12} key={cache.name}>
                  <Card 
                    size="small" 
                    title={
                      <Space>
                        <DatabaseOutlined />
                        {cache.name.replace('_', ' ').toUpperCase()}
                      </Space>
                    }
                  >
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ marginBottom: 8 }}>
                        Hit Rate: <strong>{cache.hitRate}%</strong>
                      </div>
                      <Progress 
                        percent={parseFloat(cache.hitRate)} 
                        status={parseFloat(cache.hitRate) > 70 ? 'success' : 'normal'}
                        strokeColor={{
                          '0%': '#108ee9',
                          '100%': '#87d068',
                        }}
                      />
                    </div>
                    
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic
                          title="Hits"
                          value={cache.hits}
                          valueStyle={{ fontSize: 16, color: '#52c41a' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Misses"
                          value={cache.misses}
                          valueStyle={{ fontSize: 16, color: '#ff4d4f' }}
                        />
                      </Col>
                      <Col span={8}>
                        <Statistic
                          title="Size"
                          value={cache.size}
                          valueStyle={{ fontSize: 16 }}
                        />
                      </Col>
                    </Row>
                  </Card>
                </Col>
              ))}
            </Row>
          </TabPane>

          <TabPane tab="Scheduled Jobs" key="scheduled">
            <Alert
              message="Scheduled Jobs Running"
              description={
                <div>
                  <p>The following jobs run automatically via Celery Beat:</p>
                  <ul>
                    <li>📊 Daily Lead Scoring - Every day at 2 AM</li>
                    <li>🔄 Auto-Assign Leads - Every 2 hours (9 AM - 5 PM)</li>
                    <li>⏰ Overdue Follow-up Alerts - Every hour</li>
                    <li>📈 Daily Performance Report - Every day at 8 AM</li>
                    <li>📊 Weekly Summary - Every Monday at 9 AM</li>
                    <li>🔄 Google Sheets Sync - Every 30 minutes</li>
                    <li>🗑️ Cleanup Old Activities - Every day at 3 AM</li>
                    <li>🔥 Re-engage Stale Leads - Every day at 10 AM</li>
                    <li>📱 Follow-up Reminders - Every 2 hours (8 AM - 6 PM)</li>
                    <li>💾 Cache Warm-up - Every day at 1 AM</li>
                  </ul>
                </div>
              }
              type="info"
              showIcon
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* System Information */}
      <Card title="System Information" style={{ marginTop: 24 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="Last Updated">
            {new Date().toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="Auto-Refresh">
            Every 10 seconds
          </Descriptions.Item>
          <Descriptions.Item label="Message Broker">
            Redis
          </Descriptions.Item>
          <Descriptions.Item label="Task Queues">
            4 (bulk, ai, scheduled, messages)
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default PerformanceMonitoring;
