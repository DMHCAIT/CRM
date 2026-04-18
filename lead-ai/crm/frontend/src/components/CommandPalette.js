import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Modal, Input, List, Typography, Tag, Space, Empty } from 'antd';
import {
  SearchOutlined,
  PlusOutlined,
  TeamOutlined,
  LineChartOutlined,
  SettingOutlined,
  UserOutlined,
  BookOutlined,
  GlobalOutlined,
  ThunderboltOutlined,
  RightOutlined,
  ClockCircleOutlined,
  FireOutlined,
} from '@ant-design/icons';
import Fuse from 'fuse.js';

const { Text } = Typography;

/**
 * Command Palette Component
 * Fuzzy search across all actions, pages, and entities
 * Triggered by Cmd/Ctrl + K
 */
const CommandPalette = ({ visible, onClose, currentUser }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredCommands, setFilteredCommands] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  // Define all available commands
  const commands = [
    // Create actions
    { id: 'new-lead', title: 'Create New Lead', category: 'Create', icon: <PlusOutlined />, action: () => navigate('/leads?action=new'), keywords: ['add', 'create', 'new', 'lead'] },
    { id: 'new-user', title: 'Create New User', category: 'Create', icon: <UserOutlined />, action: () => navigate('/users?action=new'), keywords: ['add', 'create', 'new', 'user', 'counselor'], adminOnly: true },
    { id: 'new-course', title: 'Create New Course', category: 'Create', icon: <BookOutlined />, action: () => navigate('/courses?action=new'), keywords: ['add', 'create', 'new', 'course'] },
    { id: 'new-hospital', title: 'Create New Hospital', category: 'Create', icon: <GlobalOutlined />, action: () => navigate('/hospitals?action=new'), keywords: ['add', 'create', 'new', 'hospital'], adminOnly: true },
    
    // Navigate to pages
    { id: 'nav-dashboard', title: 'Dashboard', category: 'Navigate', icon: <LineChartOutlined />, action: () => navigate('/'), keywords: ['dashboard', 'home', 'overview'] },
    { id: 'nav-leads', title: 'Leads', category: 'Navigate', icon: <TeamOutlined />, action: () => navigate('/leads'), keywords: ['leads', 'contacts', 'prospects'] },
    { id: 'nav-pipeline', title: 'Pipeline', category: 'Navigate', icon: <ThunderboltOutlined />, action: () => navigate('/pipeline'), keywords: ['pipeline', 'kanban', 'stages'] },
    { id: 'nav-analytics', title: 'Analytics', category: 'Navigate', icon: <LineChartOutlined />, action: () => navigate('/analytics'), keywords: ['analytics', 'reports', 'charts', 'metrics'] },
    { id: 'nav-courses', title: 'Courses', category: 'Navigate', icon: <BookOutlined />, action: () => navigate('/courses'), keywords: ['courses', 'catalog', 'programs'] },
    { id: 'nav-users', title: 'Users', category: 'Navigate', icon: <UserOutlined />, action: () => navigate('/users'), keywords: ['users', 'team', 'counselors'] },
    { id: 'nav-hospitals', title: 'Hospitals', category: 'Navigate', icon: <GlobalOutlined />, action: () => navigate('/hospitals'), keywords: ['hospitals', 'partners'] },
    { id: 'nav-activity', title: 'User Activity', category: 'Navigate', icon: <ClockCircleOutlined />, action: () => navigate('/activity'), keywords: ['activity', 'monitoring', 'logs'] },
    { id: 'nav-workflows', title: 'Workflow Settings', category: 'Navigate', icon: <SettingOutlined />, action: () => navigate('/workflow-settings'), keywords: ['workflows', 'automation', 'settings'], adminOnly: true },
    
    // Bulk actions
    { id: 'bulk-assign', title: 'Bulk Auto-Assign Leads', category: 'Bulk Actions', icon: <ThunderboltOutlined />, action: () => navigate('/leads?action=bulk-assign'), keywords: ['bulk', 'assign', 'auto', 'distribute'] },
    { id: 'bulk-update', title: 'Bulk Update Leads', category: 'Bulk Actions', icon: <TeamOutlined />, action: () => navigate('/leads?action=bulk-update'), keywords: ['bulk', 'update', 'mass', 'change'] },
    { id: 'export-leads', title: 'Export Leads (CSV)', category: 'Bulk Actions', icon: <TeamOutlined />, action: () => navigate('/leads?action=export'), keywords: ['export', 'download', 'csv', 'excel'] },
    
    // Quick filters
    { id: 'filter-hot', title: 'Show Hot Leads', category: 'Quick Filters', icon: <FireOutlined />, action: () => navigate('/leads?filter=hot'), keywords: ['hot', 'priority', 'urgent', 'high'] },
    { id: 'filter-today', title: 'Today\'s Follow-ups', category: 'Quick Filters', icon: <ClockCircleOutlined />, action: () => navigate('/leads?filter=today'), keywords: ['today', 'followup', 'scheduled', 'due'] },
    { id: 'filter-overdue', title: 'Overdue Follow-ups', category: 'Quick Filters', icon: <ClockCircleOutlined />, action: () => navigate('/leads?filter=overdue'), keywords: ['overdue', 'late', 'missed'] },
    { id: 'filter-unassigned', title: 'Unassigned Leads', category: 'Quick Filters', icon: <TeamOutlined />, action: () => navigate('/leads?filter=unassigned'), keywords: ['unassigned', 'new', 'pending'] },
    
    // Settings
    { id: 'settings', title: 'Settings', category: 'Settings', icon: <SettingOutlined />, action: () => navigate('/settings'), keywords: ['settings', 'preferences', 'config'] },
    { id: 'profile', title: 'My Profile', category: 'Settings', icon: <UserOutlined />, action: () => navigate('/profile'), keywords: ['profile', 'account', 'me', 'personal'] },
  ];

  // Filter commands based on user role
  const availableCommands = commands.filter(cmd => {
    if (cmd.adminOnly && currentUser?.role !== 'Super Admin' && currentUser?.role !== 'Hospital Admin') {
      return false;
    }
    return true;
  });

  // Initialize Fuse.js for fuzzy search
  const fuse = new Fuse(availableCommands, {
    keys: ['title', 'category', 'keywords'],
    threshold: 0.3,
    includeScore: true
  });

  // Update filtered commands when search query changes
  useEffect(() => {
    if (searchQuery.trim() === '') {
      // Show recent commands or all commands grouped by category
      setFilteredCommands(availableCommands);
    } else {
      // Fuzzy search
      const results = fuse.search(searchQuery);
      setFilteredCommands(results.map(result => result.item));
    }
    setSelectedIndex(0); // Reset selection
  }, [searchQuery]);

  // Focus input when modal opens
  useEffect(() => {
    if (visible && inputRef.current) {
      setTimeout(() => inputRef.current.focus(), 100);
    }
  }, [visible]);

  // Keyboard navigation
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      executeCommand(filteredCommands[selectedIndex]);
    } else if (e.key === 'Escape') {
      handleClose();
    }
  };

  const executeCommand = (command) => {
    if (!command) return;
    
    // Execute the command action
    command.action();
    
    // Save to recent commands (localStorage)
    saveRecentCommand(command.id);
    
    // Close palette
    handleClose();
  };

  const saveRecentCommand = (commandId) => {
    try {
      const recent = JSON.parse(localStorage.getItem('recentCommands') || '[]');
      const updated = [commandId, ...recent.filter(id => id !== commandId)].slice(0, 10);
      localStorage.setItem('recentCommands', JSON.stringify(updated));
    } catch (error) {
      console.error('Failed to save recent command:', error);
    }
  };

  const handleClose = () => {
    setSearchQuery('');
    setSelectedIndex(0);
    onClose();
  };

  // Group commands by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) {
      acc[cmd.category] = [];
    }
    acc[cmd.category].push(cmd);
    return acc;
  }, {});

  const categoryOrder = ['Create', 'Navigate', 'Bulk Actions', 'Quick Filters', 'Settings'];

  return (
    <Modal
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={600}
      bodyStyle={{ padding: 0 }}
      closable={false}
      maskStyle={{ backdropFilter: 'blur(4px)' }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', maxHeight: '70vh' }}>
        {/* Search Input */}
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0' }}>
          <Input
            ref={inputRef}
            size="large"
            placeholder="Type a command or search..."
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            suffix={
              <Text type="secondary" style={{ fontSize: 12 }}>
                ↑↓ Navigate · ↵ Select · Esc Close
              </Text>
            }
          />
        </div>

        {/* Commands List */}
        <div style={{ overflowY: 'auto', maxHeight: 'calc(70vh - 80px)' }}>
          {filteredCommands.length === 0 ? (
            <div style={{ padding: 40 }}>
              <Empty 
                description="No commands found"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          ) : (
            categoryOrder.map(category => {
              const commands = groupedCommands[category];
              if (!commands || commands.length === 0) return null;

              return (
                <div key={category}>
                  <div style={{ 
                    padding: '8px 16px', 
                    background: '#fafafa', 
                    borderBottom: '1px solid #f0f0f0',
                    fontSize: 11,
                    fontWeight: 'bold',
                    textTransform: 'uppercase',
                    color: '#8c8c8c'
                  }}>
                    {category}
                  </div>
                  <List
                    dataSource={commands}
                    renderItem={(command, index) => {
                      const globalIndex = filteredCommands.indexOf(command);
                      const isSelected = globalIndex === selectedIndex;
                      
                      return (
                        <List.Item
                          style={{
                            padding: '12px 16px',
                            cursor: 'pointer',
                            background: isSelected ? '#e6f7ff' : 'transparent',
                            borderLeft: isSelected ? '3px solid #1890ff' : '3px solid transparent',
                            transition: 'all 0.2s'
                          }}
                          onClick={() => executeCommand(command)}
                          onMouseEnter={() => setSelectedIndex(globalIndex)}
                        >
                          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                            <Space>
                              <span style={{ fontSize: 18 }}>{command.icon}</span>
                              <div>
                                <Text strong>{command.title}</Text>
                              </div>
                            </Space>
                            <RightOutlined style={{ fontSize: 12, color: '#bfbfbf' }} />
                          </Space>
                        </List.Item>
                      );
                    }}
                  />
                </div>
              );
            })
          )}
        </div>

        {/* Footer hint */}
        <div style={{ 
          padding: '8px 16px', 
          borderTop: '1px solid #f0f0f0',
          background: '#fafafa',
          fontSize: 11,
          color: '#8c8c8c',
          textAlign: 'center'
        }}>
          Press <Tag style={{ fontSize: 10 }}>?</Tag> to see all keyboard shortcuts
        </div>
      </div>
    </Modal>
  );
};

export default CommandPalette;
