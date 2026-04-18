import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Input, List, Tag, Space, Typography, Empty, Spin } from 'antd';
import { 
  SearchOutlined,
  UserOutlined,
  TeamOutlined,
  BookOutlined,
  GlobalOutlined,
  RightOutlined
} from '@ant-design/icons';
import api from '../api';
import debounce from 'lodash/debounce';

const { Text } = Typography;

/**
 * Global Search Component
 * Search across leads, courses, hospitals, and users
 * Debounced API calls with instant results
 * 
 * Props:
 * - onSelect: function - Callback when result is selected
 * - autoFocus: boolean - Auto-focus search input
 * - placeholder: string - Custom placeholder
 */
const GlobalSearch = ({ onSelect, autoFocus = false, placeholder = "Search leads, courses, hospitals, users..." }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Debounced search function
  const debouncedSearch = useRef(
    debounce(async (searchQuery) => {
      if (!searchQuery || searchQuery.length < 2) {
        setResults({});
        setLoading(false);
        return;
      }

      setLoading(true);
      
      try {
        // Search across all entities in parallel
        const [leadsRes, coursesRes, hospitalsRes, usersRes] = await Promise.all([
          api.get('/api/leads', { params: { search: searchQuery, limit: 5 } }).catch(() => ({ data: [] })),
          api.get('/api/courses', { params: { search: searchQuery, limit: 5 } }).catch(() => ({ data: [] })),
          api.get('/api/hospitals', { params: { search: searchQuery, limit: 5 } }).catch(() => ({ data: [] })),
          api.get('/api/users', { params: { search: searchQuery, limit: 5 } }).catch(() => ({ data: [] }))
        ]);

        setResults({
          leads: leadsRes.data?.leads || leadsRes.data || [],
          courses: coursesRes.data || [],
          hospitals: hospitalsRes.data || [],
          users: usersRes.data || []
        });
      } catch (error) {
        console.error('Search failed:', error);
        setResults({});
      } finally {
        setLoading(false);
      }
    }, 300)
  ).current;

  useEffect(() => {
    debouncedSearch(query);
    
    return () => {
      debouncedSearch.cancel();
    };
  }, [query]);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      setTimeout(() => inputRef.current.focus(), 100);
    }
  }, [autoFocus]);

  const handleSelect = (type, item) => {
    // Navigate to appropriate page
    switch (type) {
      case 'lead':
        navigate(`/leads?id=${item.lead_id}`);
        break;
      case 'course':
        navigate(`/courses?id=${item.id}`);
        break;
      case 'hospital':
        navigate(`/hospitals?id=${item.id}`);
        break;
      case 'user':
        navigate(`/users?id=${item.id}`);
        break;
      default:
        break;
    }
    
    // Clear search
    setQuery('');
    setResults({});
    
    // Callback
    if (onSelect) {
      onSelect({ type, item });
    }
  };

  const totalResults = 
    (results.leads?.length || 0) +
    (results.courses?.length || 0) +
    (results.hospitals?.length || 0) +
    (results.users?.length || 0);

  const renderLeadItem = (lead) => (
    <List.Item
      key={lead.lead_id}
      onClick={() => handleSelect('lead', lead)}
      style={{ cursor: 'pointer', padding: '12px 16px' }}
      className="global-search-item"
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <TeamOutlined style={{ fontSize: 18, color: '#1890ff' }} />
          <div>
            <Text strong>{lead.name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {lead.email} • {lead.preferred_country}
              {lead.ai_score && (
                <> • Score: <strong>{lead.ai_score}</strong></>
              )}
            </Text>
          </div>
        </Space>
        <Space>
          {lead.status && <Tag color="blue">{lead.status}</Tag>}
          <RightOutlined style={{ fontSize: 12, color: '#bfbfbf' }} />
        </Space>
      </Space>
    </List.Item>
  );

  const renderCourseItem = (course) => (
    <List.Item
      key={course.id}
      onClick={() => handleSelect('course', course)}
      style={{ cursor: 'pointer', padding: '12px 16px' }}
      className="global-search-item"
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <BookOutlined style={{ fontSize: 18, color: '#52c41a' }} />
          <div>
            <Text strong>{course.name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {course.country} • {course.duration}
            </Text>
          </div>
        </Space>
        <Space>
          <Tag color="green">${course.tuition_fee?.toLocaleString()}</Tag>
          <RightOutlined style={{ fontSize: 12, color: '#bfbfbf' }} />
        </Space>
      </Space>
    </List.Item>
  );

  const renderHospitalItem = (hospital) => (
    <List.Item
      key={hospital.id}
      onClick={() => handleSelect('hospital', hospital)}
      style={{ cursor: 'pointer', padding: '12px 16px' }}
      className="global-search-item"
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <GlobalOutlined style={{ fontSize: 18, color: '#fa8c16' }} />
          <div>
            <Text strong>{hospital.name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {hospital.country} • {hospital.type}
            </Text>
          </div>
        </Space>
        <RightOutlined style={{ fontSize: 12, color: '#bfbfbf' }} />
      </Space>
    </List.Item>
  );

  const renderUserItem = (user) => (
    <List.Item
      key={user.id}
      onClick={() => handleSelect('user', user)}
      style={{ cursor: 'pointer', padding: '12px 16px' }}
      className="global-search-item"
    >
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <UserOutlined style={{ fontSize: 18, color: '#722ed1' }} />
          <div>
            <Text strong>{user.name}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {user.email} • {user.role}
            </Text>
          </div>
        </Space>
        <Space>
          <Tag color="purple">{user.role}</Tag>
          <RightOutlined style={{ fontSize: 12, color: '#bfbfbf' }} />
        </Space>
      </Space>
    </List.Item>
  );

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <Input
        ref={inputRef}
        size="large"
        placeholder={placeholder}
        prefix={<SearchOutlined />}
        suffix={loading && <Spin size="small" />}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setTimeout(() => setFocused(false), 200)}
        style={{ width: '100%' }}
      />

      {/* Search Results Dropdown */}
      {focused && query.length >= 2 && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            background: 'white',
            borderRadius: 4,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            maxHeight: '400px',
            overflowY: 'auto',
            zIndex: 1000
          }}
        >
          {loading && (
            <div style={{ padding: 40, textAlign: 'center' }}>
              <Spin />
            </div>
          )}

          {!loading && totalResults === 0 && (
            <div style={{ padding: 40 }}>
              <Empty 
                description={`No results for "${query}"`}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          )}

          {!loading && totalResults > 0 && (
            <div>
              {/* Leads */}
              {results.leads && results.leads.length > 0 && (
                <div>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: '#fafafa', 
                    fontWeight: 'bold',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    color: '#8c8c8c'
                  }}>
                    Leads ({results.leads.length})
                  </div>
                  <List
                    dataSource={results.leads}
                    renderItem={renderLeadItem}
                    split={false}
                  />
                </div>
              )}

              {/* Courses */}
              {results.courses && results.courses.length > 0 && (
                <div>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: '#fafafa', 
                    fontWeight: 'bold',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    color: '#8c8c8c'
                  }}>
                    Courses ({results.courses.length})
                  </div>
                  <List
                    dataSource={results.courses}
                    renderItem={renderCourseItem}
                    split={false}
                  />
                </div>
              )}

              {/* Hospitals */}
              {results.hospitals && results.hospitals.length > 0 && (
                <div>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: '#fafafa', 
                    fontWeight: 'bold',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    color: '#8c8c8c'
                  }}>
                    Hospitals ({results.hospitals.length})
                  </div>
                  <List
                    dataSource={results.hospitals}
                    renderItem={renderHospitalItem}
                    split={false}
                  />
                </div>
              )}

              {/* Users */}
              {results.users && results.users.length > 0 && (
                <div>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: '#fafafa', 
                    fontWeight: 'bold',
                    fontSize: 11,
                    textTransform: 'uppercase',
                    color: '#8c8c8c'
                  }}>
                    Users ({results.users.length})
                  </div>
                  <List
                    dataSource={results.users}
                    renderItem={renderUserItem}
                    split={false}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Custom CSS for hover effect */}
      <style>{`
        .global-search-item:hover {
          background: #f5f5f5;
        }
      `}</style>
    </div>
  );
};

export default GlobalSearch;
