import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Table, 
  Progress, 
  Tag,
  Select,
  DatePicker,
  Space,
  Button,
  Tabs,
  Empty,
  Tooltip,
  Badge,
  Alert
} from 'antd';
import {
  TrophyOutlined,
  RiseOutlined,
  FallOutlined,
  FireOutlined,
  ThunderboltOutlined,
  TeamOutlined,
  DollarOutlined,
  BarChartOutlined,
  LineChartOutlined,
  PieChartOutlined,
  FunnelPlotOutlined,
  WarningOutlined,
  CheckCircleOutlined
} from '@ant-design/icons';
import api from '../api/api';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { TabPane } = Tabs;
const { Option } = Select;

/**
 * Advanced Analytics Dashboard
 * Comprehensive analytics with lead attribution, funnels, leaderboards, predictions
 */
const AdvancedAnalytics = () => {
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(30, 'days'),
    dayjs()
  ]);
  
  // Analytics data
  const [leadSources, setLeadSources] = useState(null);
  const [conversionFunnel, setConversionFunnel] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [dataQuality, setDataQuality] = useState(null);
  
  // Filters
  const [selectedMetric, setSelectedMetric] = useState('enrollments');

  useEffect(() => {
    fetchAllAnalytics();
  }, [dateRange]);

  const fetchAllAnalytics = async () => {
    setLoading(true);
    
    try {
      const [start, end] = dateRange;
      const params = {
        start_date: start.format('YYYY-MM-DD'),
        end_date: end.format('YYYY-MM-DD')
      };
      
      const [sourcesRes, funnelRes, leaderboardRes, forecastRes, qualityRes] = await Promise.all([
        api.get('/api/analytics/lead-sources', { params }).catch(() => ({ data: null })),
        api.get('/api/analytics/conversion-funnel', { params }).catch(() => ({ data: null })),
        api.get('/api/analytics/leaderboard', { params: { ...params, metric: selectedMetric } }).catch(() => ({ data: [] })),
        api.get('/api/analytics/forecast', { params: { forecast_days: 30 } }).catch(() => ({ data: null })),
        api.get('/api/analytics/data-quality').catch(() => ({ data: null }))
      ]);
      
      setLeadSources(sourcesRes.data);
      setConversionFunnel(funnelRes.data);
      setLeaderboard(leaderboardRes.data);
      setForecast(forecastRes.data);
      setDataQuality(qualityRes.data);
    } catch (error) {
      console.error('Failed to fetch analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (dates) => {
    if (dates) {
      setDateRange(dates);
    }
  };

  const handleMetricChange = (value) => {
    setSelectedMetric(value);
    fetchAllAnalytics();
  };

  // Lead Source Table Columns
  const sourceColumns = [
    {
      title: 'Source',
      dataIndex: 'source',
      key: 'source',
      render: (source) => (
        <strong>{source}</strong>
      )
    },
    {
      title: 'Total Leads',
      dataIndex: 'total_leads',
      key: 'total_leads',
      sorter: (a, b) => a.total_leads - b.total_leads,
      render: (val) => <Tag color="blue">{val}</Tag>
    },
    {
      title: 'Contacted',
      dataIndex: 'contacted',
      key: 'contacted',
      render: (val) => val
    },
    {
      title: 'Qualified',
      dataIndex: 'qualified',
      key: 'qualified',
      render: (val) => val
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
      sorter: (a, b) => a.conversion_rate - b.conversion_rate,
      render: (rate) => (
        <Progress 
          percent={rate} 
          size="small" 
          status={rate >= 15 ? 'success' : rate >= 10 ? 'normal' : 'exception'}
        />
      )
    },
    {
      title: 'Avg Score',
      dataIndex: 'avg_score',
      key: 'avg_score',
      render: (score) => (
        <Tooltip title={`Average AI Score`}>
          {score.toFixed(1)}
        </Tooltip>
      )
    }
  ];

  // Leaderboard Columns
  const leaderboardColumns = [
    {
      title: 'Rank',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank) => {
        if (rank === 1) return <Badge count={<TrophyOutlined style={{ color: '#FFD700' }} />} />;
        if (rank === 2) return <Badge count={<TrophyOutlined style={{ color: '#C0C0C0' }} />} />;
        if (rank === 3) return <Badge count={<TrophyOutlined style={{ color: '#CD7F32' }} />} />;
        return <span style={{ fontWeight: 'bold' }}>#{rank}</span>;
      }
    },
    {
      title: 'Counselor',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <div>
          <div><strong>{name}</strong></div>
          <div style={{ fontSize: 12, color: '#666' }}>{record.role}</div>
        </div>
      )
    },
    {
      title: 'Enrollments',
      dataIndex: 'enrollments',
      key: 'enrollments',
      sorter: (a, b) => a.enrollments - b.enrollments,
      render: (val) => <Tag color="success" icon={<CheckCircleOutlined />}>{val}</Tag>
    },
    {
      title: 'Conversion Rate',
      dataIndex: 'conversion_rate',
      key: 'conversion_rate',
      render: (rate) => `${rate}%`
    },
    {
      title: 'Activities',
      key: 'activities',
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <span>📞 {record.calls_made} calls</span>
          <span>✉️ {record.emails_sent} emails</span>
          <span>💬 {record.whatsapp_sent} WhatsApp</span>
        </Space>
      )
    },
    {
      title: 'Avg Response Time',
      dataIndex: 'avg_response_time_hours',
      key: 'avg_response_time_hours',
      render: (hours) => (
        <Tag color={hours < 24 ? 'green' : hours < 48 ? 'orange' : 'red'}>
          {hours.toFixed(1)}h
        </Tag>
      )
    },
    {
      title: 'Performance Score',
      dataIndex: 'performance_score',
      key: 'performance_score',
      sorter: (a, b) => a.performance_score - b.performance_score,
      render: (score) => (
        <Progress 
          type="circle" 
          percent={Math.min(100, score / 10)} 
          width={50}
          format={() => score.toFixed(0)}
        />
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1><BarChartOutlined /> Advanced Analytics</h1>
        
        <Space>
          <RangePicker
            value={dateRange}
            onChange={handleDateChange}
            format="MMM DD, YYYY"
          />
          <Button type="primary" onClick={fetchAllAnalytics} loading={loading}>
            Refresh Data
          </Button>
        </Space>
      </div>

      {/* Data Quality Alert */}
      {dataQuality && dataQuality.quality_score < 70 && (
        <Alert
          message="Data Quality Warning"
          description={
            <div>
              <p>Quality Score: <strong>{dataQuality.quality_score.toFixed(1)}/100</strong></p>
              <ul>
                {dataQuality.recommendations.map((rec, idx) => (
                  <li key={idx}>{rec}</li>
                ))}
              </ul>
            </div>
          }
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          closable
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Key Metrics Summary */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Leads"
              value={leadSources?.total_leads || 0}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            {leadSources?.top_source && (
              <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                Top: {leadSources.top_source}
              </div>
            )}
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Conversion Rate"
              value={conversionFunnel?.conversion_rates?.overall || 0}
              suffix="%"
              prefix={<FunnelPlotOutlined />}
              valueStyle={{ 
                color: (conversionFunnel?.conversion_rates?.overall || 0) >= 15 ? '#52c41a' : '#faad14' 
              }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              {conversionFunnel?.funnel_stages?.enrolled || 0} enrollments
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Forecasted (30d)"
              value={forecast?.forecast_with_pipeline || 0}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
              Confidence: {forecast?.confidence || 'N/A'}
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Data Quality"
              value={dataQuality?.quality_score || 0}
              suffix="/100"
              prefix={dataQuality && dataQuality.quality_score >= 70 ? <CheckCircleOutlined /> : <WarningOutlined />}
              valueStyle={{ 
                color: dataQuality && dataQuality.quality_score >= 80 ? '#52c41a' : 
                       dataQuality && dataQuality.quality_score >= 60 ? '#faad14' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Analytics Tabs */}
      <Card>
        <Tabs defaultActiveKey="sources">
          
          {/* Lead Sources Tab */}
          <TabPane tab={<span><PieChartOutlined /> Lead Sources</span>} key="sources">
            <div style={{ marginBottom: 16 }}>
              <h3>Lead Source Attribution</h3>
              <p style={{ color: '#666' }}>
                Analyze which sources bring the highest quality leads and best conversion rates
              </p>
            </div>
            
            {leadSources && leadSources.sources && leadSources.sources.length > 0 ? (
              <Table
                columns={sourceColumns}
                dataSource={leadSources.sources}
                rowKey="source"
                pagination={{ pageSize: 10 }}
                size="small"
              />
            ) : (
              <Empty description="No lead source data available" />
            )}
          </TabPane>

          {/* Conversion Funnel Tab */}
          <TabPane tab={<span><FunnelPlotOutlined /> Conversion Funnel</span>} key="funnel">
            <div style={{ marginBottom: 16 }}>
              <h3>Conversion Funnel Analysis</h3>
              <p style={{ color: '#666' }}>
                Track lead progression through pipeline stages and identify drop-off points
              </p>
            </div>
            
            {conversionFunnel ? (
              <div>
                {/* Funnel Visualization */}
                <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
                  <Col xs={24} md={6}>
                    <Card size="small">
                      <Statistic
                        title="New Leads"
                        value={conversionFunnel.funnel_stages?.new || 0}
                        valueStyle={{ color: '#1890ff' }}
                      />
                      <Progress 
                        percent={100} 
                        showInfo={false}
                        strokeColor="#1890ff"
                      />
                    </Card>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <Card size="small">
                      <Statistic
                        title="Contacted"
                        value={conversionFunnel.funnel_stages?.contacted || 0}
                        valueStyle={{ color: '#52c41a' }}
                      />
                      <Progress 
                        percent={conversionFunnel.conversion_rates?.new_to_contacted || 0} 
                        strokeColor="#52c41a"
                      />
                      <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                        Drop-off: {conversionFunnel.dropoff?.new_to_contacted || 0}
                      </div>
                    </Card>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <Card size="small">
                      <Statistic
                        title="Qualified"
                        value={conversionFunnel.funnel_stages?.qualified || 0}
                        valueStyle={{ color: '#faad14' }}
                      />
                      <Progress 
                        percent={conversionFunnel.conversion_rates?.contacted_to_qualified || 0}
                        strokeColor="#faad14"
                      />
                      <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                        Drop-off: {conversionFunnel.dropoff?.contacted_to_qualified || 0}
                      </div>
                    </Card>
                  </Col>
                  
                  <Col xs={24} md={6}>
                    <Card size="small">
                      <Statistic
                        title="Enrolled"
                        value={conversionFunnel.funnel_stages?.enrolled || 0}
                        valueStyle={{ color: '#eb2f96' }}
                      />
                      <Progress 
                        percent={conversionFunnel.conversion_rates?.qualified_to_enrolled || 0}
                        strokeColor="#eb2f96"
                      />
                      <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>
                        Drop-off: {conversionFunnel.dropoff?.qualified_to_enrolled || 0}
                      </div>
                    </Card>
                  </Col>
                </Row>

                {/* Stage Duration Stats */}
                <Card size="small" title="Average Time in Each Stage">
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="New → Contacted"
                        value={conversionFunnel.avg_durations_hours?.new_to_contact || 0}
                        suffix="hours"
                        valueStyle={{ fontSize: 18 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="Contacted → Qualified"
                        value={conversionFunnel.avg_durations_hours?.contact_to_qualified || 0}
                        suffix="hours"
                        valueStyle={{ fontSize: 18 }}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="Qualified → Enrolled"
                        value={conversionFunnel.avg_durations_hours?.qualified_to_enrolled || 0}
                        suffix="hours"
                        valueStyle={{ fontSize: 18 }}
                      />
                    </Col>
                  </Row>
                </Card>
              </div>
            ) : (
              <Empty description="No funnel data available" />
            )}
          </TabPane>

          {/* Leaderboard Tab */}
          <TabPane tab={<span><TrophyOutlined /> Leaderboard</span>} key="leaderboard">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3>Counselor Performance Leaderboard</h3>
                <p style={{ color: '#666' }}>
                  Rankings based on enrollments, conversion rates, and overall performance
                </p>
              </div>
              
              <Select
                value={selectedMetric}
                onChange={handleMetricChange}
                style={{ width: 200 }}
              >
                <Option value="enrollments">Enrollments</Option>
                <Option value="conversion_rate">Conversion Rate</Option>
                <Option value="activity">Total Activity</Option>
                <Option value="response_time">Response Time</Option>
              </Select>
            </div>
            
            {leaderboard && leaderboard.length > 0 ? (
              <Table
                columns={leaderboardColumns}
                dataSource={leaderboard}
                rowKey="counselor_id"
                pagination={{ pageSize: 10 }}
              />
            ) : (
              <Empty description="No leaderboard data available" />
            )}
          </TabPane>

          {/* Forecast Tab */}
          <TabPane tab={<span><RiseOutlined /> Forecast</span>} key="forecast">
            <div style={{ marginBottom: 16 }}>
              <h3>Enrollment Forecast (Next 30 Days)</h3>
              <p style={{ color: '#666' }}>
                Predictive analytics based on historical trends and current pipeline
              </p>
            </div>
            
            {forecast ? (
              <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                  <Card>
                    <Statistic
                      title="Historical Avg (Weekly)"
                      value={forecast.historical_avg_weekly}
                      suffix="enrollments"
                      prefix={<LineChartOutlined />}
                    />
                  </Card>
                </Col>
                
                <Col xs={24} md={8}>
                  <Card>
                    <Statistic
                      title="Forecasted Enrollments"
                      value={forecast.forecasted_enrollments}
                      suffix="in 30 days"
                      prefix={<RiseOutlined />}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Card>
                </Col>
                
                <Col xs={24} md={8}>
                  <Card>
                    <Statistic
                      title="With Current Pipeline"
                      value={forecast.forecast_with_pipeline}
                      suffix="potential"
                      prefix={<FireOutlined />}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
                
                <Col xs={24}>
                  <Card size="small" title="Forecast Details">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                      <div>
                        <strong>Current Pipeline:</strong> {forecast.current_pipeline} leads
                      </div>
                      <div>
                        <strong>Daily Rate:</strong> {forecast.daily_rate} enrollments/day
                      </div>
                      <div>
                        <strong>Confidence:</strong> <Tag color={forecast.confidence === 'High' ? 'green' : 'orange'}>{forecast.confidence}</Tag>
                      </div>
                    </div>
                  </Card>
                </Col>
              </Row>
            ) : (
              <Empty description="No forecast data available" />
            )}
          </TabPane>

          {/* Data Quality Tab */}
          <TabPane tab={<span><WarningOutlined /> Data Quality</span>} key="quality">
            <div style={{ marginBottom: 16 }}>
              <h3>Data Quality Report</h3>
              <p style={{ color: '#666' }}>
                Monitor data completeness and identify issues
              </p>
            </div>
            
            {dataQuality ? (
              <div>
                <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
                  <Col xs={24} md={12}>
                    <Card>
                      <Statistic
                        title="Overall Quality Score"
                        value={dataQuality.quality_score}
                        suffix="/100"
                        prefix={dataQuality.quality_score >= 70 ? <CheckCircleOutlined /> : <WarningOutlined />}
                        valueStyle={{ 
                          color: dataQuality.quality_score >= 80 ? '#52c41a' : 
                                 dataQuality.quality_score >= 60 ? '#faad14' : '#ff4d4f'
                        }}
                      />
                      <Progress 
                        percent={dataQuality.quality_score} 
                        status={dataQuality.quality_score >= 70 ? 'success' : 'exception'}
                        style={{ marginTop: 16 }}
                      />
                    </Card>
                  </Col>
                  
                  <Col xs={24} md={12}>
                    <Card title="Issues Found">
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <div>Missing Email: <Tag color="red">{dataQuality.issues?.missing_email || 0}</Tag></div>
                        <div>Missing Phone: <Tag color="red">{dataQuality.issues?.missing_phone || 0}</Tag></div>
                        <div>Duplicates: <Tag color="orange">{dataQuality.issues?.duplicates || 0}</Tag></div>
                        <div>Incomplete: <Tag color="orange">{dataQuality.issues?.incomplete_profiles || 0}</Tag></div>
                        <div>Stale Leads: <Tag color="default">{dataQuality.issues?.stale_leads || 0}</Tag></div>
                      </div>
                    </Card>
                  </Col>
                </Row>

                <Card title="Recommendations">
                  <ul>
                    {dataQuality.recommendations?.map((rec, idx) => (
                      <li key={idx} style={{ marginBottom: 8 }}>{rec}</li>
                    ))}
                  </ul>
                </Card>
              </div>
            ) : (
              <Empty description="No data quality information available" />
            )}
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default AdvancedAnalytics;
