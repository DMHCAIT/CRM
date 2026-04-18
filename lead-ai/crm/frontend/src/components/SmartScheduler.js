import React, { useState, useEffect } from 'react';
import { Card, Button, DatePicker, TimePicker, Space, Alert, Spin, Tag, Tooltip, Radio } from 'antd';
import { ClockCircleOutlined, ThunderboltOutlined, CalendarOutlined, CheckCircleOutlined } from '@ant-design/icons';
import moment from 'moment';
import api from '../api/api';

/**
 * SmartScheduler Component
 * AI-driven optimal contact time prediction with quick schedule buttons
 */
const SmartScheduler = ({ leadId, currentFollowUp, onScheduled }) => {
  const [loading, setLoading] = useState(false);
  const [suggestion, setSuggestion] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [mode, setMode] = useState('ai'); // 'ai' or 'manual'

  useEffect(() => {
    if (leadId && mode === 'ai') {
      fetchAISuggestion();
    }
  }, [leadId, mode]);

  const fetchAISuggestion = async () => {
    setLoading(true);
    try {
      const response = await api.post(`/api/scheduler/suggest-time/${leadId}`);
      setSuggestion(response.data);
      setSelectedTime(response.data.suggested_time);
    } catch (error) {
      console.error('Failed to fetch AI suggestion:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSchedule = async (hoursAhead) => {
    const scheduleTime = moment().add(hoursAhead, 'hours').toISOString();
    await scheduleFollowUp(scheduleTime, 'manual');
  };

  const handleAISchedule = async () => {
    if (suggestion && suggestion.suggested_time) {
      await scheduleFollowUp(suggestion.suggested_time, 'ai');
    }
  };

  const handleManualSchedule = async () => {
    if (selectedTime) {
      await scheduleFollowUp(selectedTime, 'manual');
    }
  };

  const scheduleFollowUp = async (time, source) => {
    setLoading(true);
    try {
      const response = await api.post(`/api/scheduler/auto-schedule/${leadId}`, null, {
        params: { trigger_event: source === 'ai' ? 'ai_scheduled' : 'manual' }
      });
      
      if (onScheduled) {
        onScheduled(response.data);
      }
    } catch (error) {
      console.error('Failed to schedule follow-up:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderAISuggestion = () => {
    if (!suggestion) return null;

    const confidenceColor = suggestion.confidence >= 0.8 ? 'green' : suggestion.confidence >= 0.6 ? 'orange' : 'default';
    const suggestedMoment = moment(suggestion.suggested_time);

    return (
      <Card 
        size="small" 
        className="mb-3"
        style={{ borderLeft: '4px solid #1890ff' }}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          {/* AI Recommendation Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <ThunderboltOutlined style={{ color: '#1890ff', fontSize: 18 }} />
              <strong>AI Recommended Time</strong>
            </Space>
            <Tag color={confidenceColor}>
              {(suggestion.confidence * 100).toFixed(0)}% Confidence
            </Tag>
          </div>

          {/* Suggested Time */}
          <div style={{ 
            padding: '12px', 
            background: '#f0f5ff', 
            borderRadius: '6px',
            border: '1px solid #adc6ff'
          }}>
            <div style={{ fontSize: 20, fontWeight: 'bold', color: '#1890ff' }}>
              {suggestedMoment.format('dddd, MMM D, YYYY')}
            </div>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff', marginTop: 4 }}>
              {suggestedMoment.format('h:mm A')}
            </div>
            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
              {suggestion.suggested_time_local}
            </div>
          </div>

          {/* Reasoning */}
          <Alert
            message="Why this time?"
            description={suggestion.reasoning}
            type="info"
            showIcon
            icon={<ClockCircleOutlined />}
            style={{ fontSize: 12 }}
          />

          {/* Alternative Times */}
          {suggestion.alternatives && suggestion.alternatives.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 8 }}>
                Alternative times:
              </div>
              <Space wrap>
                {suggestion.alternatives.map((alt, idx) => (
                  <Tooltip key={idx} title={alt.time_local}>
                    <Button 
                      size="small" 
                      onClick={() => setSelectedTime(alt.time)}
                    >
                      {alt.label}
                    </Button>
                  </Tooltip>
                ))}
              </Space>
            </div>
          )}

          {/* Schedule Button */}
          <Button 
            type="primary" 
            icon={<CheckCircleOutlined />}
            onClick={handleAISchedule}
            loading={loading}
            block
          >
            Schedule at AI Recommended Time
          </Button>
        </Space>
      </Card>
    );
  };

  const renderQuickActions = () => (
    <Card size="small" title="Quick Schedule" className="mb-3">
      <Space wrap>
        <Button 
          icon={<ThunderboltOutlined />}
          onClick={() => handleQuickSchedule(2)}
          loading={loading}
          size="small"
        >
          In 2 Hours
        </Button>
        <Button 
          icon={<CalendarOutlined />}
          onClick={() => handleQuickSchedule(24)}
          loading={loading}
          size="small"
        >
          Tomorrow 10 AM
        </Button>
        <Button 
          icon={<CalendarOutlined />}
          onClick={() => handleQuickSchedule(168)}
          loading={loading}
          size="small"
        >
          Next Week
        </Button>
      </Space>
    </Card>
  );

  const renderManualScheduler = () => (
    <Card size="small" title="Manual Schedule">
      <Space direction="vertical" style={{ width: '100%' }}>
        <DatePicker 
          showTime
          format="YYYY-MM-DD HH:mm"
          onChange={(date) => setSelectedTime(date ? date.toISOString() : null)}
          style={{ width: '100%' }}
          defaultValue={currentFollowUp ? moment(currentFollowUp) : null}
        />
        <Button 
          type="primary" 
          onClick={handleManualSchedule}
          disabled={!selectedTime}
          loading={loading}
          block
        >
          Schedule Follow-up
        </Button>
      </Space>
    </Card>
  );

  return (
    <div className="smart-scheduler">
      {/* Mode Selector */}
      <div style={{ marginBottom: 16 }}>
        <Radio.Group 
          value={mode} 
          onChange={(e) => setMode(e.target.value)}
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="ai">
            <ThunderboltOutlined /> AI Suggested
          </Radio.Button>
          <Radio.Button value="manual">
            <CalendarOutlined /> Manual
          </Radio.Button>
        </Radio.Group>
      </div>

      {/* Content */}
      {loading && !suggestion ? (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <Spin tip="Analyzing best contact time..." />
        </div>
      ) : (
        <>
          {mode === 'ai' ? (
            <>
              {renderAISuggestion()}
              {renderQuickActions()}
            </>
          ) : (
            <>
              {renderQuickActions()}
              {renderManualScheduler()}
            </>
          )}
        </>
      )}

      {/* Current Schedule Display */}
      {currentFollowUp && (
        <Alert
          message="Currently Scheduled"
          description={`Follow-up scheduled for ${moment(currentFollowUp).format('MMM D, YYYY h:mm A')}`}
          type="success"
          showIcon
          closable
          style={{ marginTop: 12 }}
        />
      )}
    </div>
  );
};

export default SmartScheduler;
