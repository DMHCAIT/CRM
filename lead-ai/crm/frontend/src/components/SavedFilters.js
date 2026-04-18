import React, { useState, useEffect } from 'react';
import { 
  Dropdown, 
  Button, 
  Menu, 
  Modal, 
  Input, 
  Form, 
  message, 
  Tag, 
  Space,
  Tooltip,
  Switch
} from 'antd';
import { 
  FilterOutlined, 
  StarOutlined, 
  PlusOutlined, 
  DeleteOutlined,
  TeamOutlined,
  UserOutlined
} from '@ant-design/icons';

/**
 * Saved Filters Component
 * Save and quickly switch between filter combinations
 * Supports personal and team-shared filter views
 * 
 * Props:
 * - currentFilters: object - Current filter state
 * - onApplyFilter: function - Callback when filter is applied
 * - userId: string - Current user ID
 * - teamId: string - Current team/hospital ID
 */
const SavedFilters = ({ currentFilters, onApplyFilter, userId, teamId }) => {
  const [savedFilters, setSavedFilters] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  // Load saved filters from localStorage
  useEffect(() => {
    loadSavedFilters();
  }, [userId]);

  const loadSavedFilters = () => {
    try {
      const personalKey = `saved_filters_${userId}`;
      const teamKey = `saved_filters_team_${teamId}`;
      
      const personal = JSON.parse(localStorage.getItem(personalKey) || '[]');
      const team = JSON.parse(localStorage.getItem(teamKey) || '[]');
      
      const allFilters = [
        ...personal.map(f => ({ ...f, scope: 'personal' })),
        ...team.map(f => ({ ...f, scope: 'team' }))
      ];
      
      setSavedFilters(allFilters);
    } catch (error) {
      console.error('Failed to load saved filters:', error);
    }
  };

  const saveFilter = async (values) => {
    try {
      const newFilter = {
        id: Date.now().toString(),
        name: values.name,
        description: values.description,
        filters: currentFilters,
        scope: values.shared ? 'team' : 'personal',
        createdAt: new Date().toISOString(),
        createdBy: userId,
        usageCount: 0
      };
      
      const storageKey = values.shared 
        ? `saved_filters_team_${teamId}` 
        : `saved_filters_${userId}`;
      
      const existing = JSON.parse(localStorage.getItem(storageKey) || '[]');
      const updated = [...existing, newFilter];
      
      localStorage.setItem(storageKey, JSON.stringify(updated));
      
      setModalVisible(false);
      form.resetFields();
      loadSavedFilters();
      
      message.success(`Filter "${values.name}" saved successfully`);
    } catch (error) {
      console.error('Failed to save filter:', error);
      message.error('Failed to save filter');
    }
  };

  const applyFilter = (filter) => {
    try {
      // Increment usage count
      const storageKey = filter.scope === 'team' 
        ? `saved_filters_team_${teamId}` 
        : `saved_filters_${userId}`;
      
      const existing = JSON.parse(localStorage.getItem(storageKey) || '[]');
      const updated = existing.map(f => 
        f.id === filter.id 
          ? { ...f, usageCount: (f.usageCount || 0) + 1 }
          : f
      );
      
      localStorage.setItem(storageKey, JSON.stringify(updated));
      
      // Apply the filter
      if (onApplyFilter) {
        onApplyFilter(filter.filters);
      }
      
      message.success(`Applied filter: ${filter.name}`);
      loadSavedFilters();
    } catch (error) {
      console.error('Failed to apply filter:', error);
      message.error('Failed to apply filter');
    }
  };

  const deleteFilter = (filter, e) => {
    e.stopPropagation();
    
    Modal.confirm({
      title: 'Delete Filter',
      content: `Are you sure you want to delete "${filter.name}"?`,
      onOk: () => {
        try {
          const storageKey = filter.scope === 'team' 
            ? `saved_filters_team_${teamId}` 
            : `saved_filters_${userId}`;
          
          const existing = JSON.parse(localStorage.getItem(storageKey) || '[]');
          const updated = existing.filter(f => f.id !== filter.id);
          
          localStorage.setItem(storageKey, JSON.stringify(updated));
          
          loadSavedFilters();
          message.success('Filter deleted');
        } catch (error) {
          console.error('Failed to delete filter:', error);
          message.error('Failed to delete filter');
        }
      }
    });
  };

  // Get filter summary text
  const getFilterSummary = (filters) => {
    const parts = [];
    
    if (filters.status) parts.push(`Status: ${filters.status}`);
    if (filters.country) parts.push(`Country: ${filters.country}`);
    if (filters.course) parts.push(`Course: ${filters.course}`);
    if (filters.minScore !== undefined) parts.push(`Score ≥ ${filters.minScore}`);
    if (filters.assigned_to) parts.push(`Assigned: ${filters.assigned_to}`);
    if (filters.search) parts.push(`Search: "${filters.search}"`);
    
    return parts.length > 0 ? parts.join(' | ') : 'No filters';
  };

  // Build dropdown menu
  const buildMenu = () => {
    const menuItems = [];
    
    // Quick filters (system default)
    const quickFilters = [
      { 
        id: 'hot-leads', 
        name: '🔥 Hot Leads', 
        filters: { status: 'hot', minScore: 80 },
        scope: 'system'
      },
      { 
        id: 'today-followups', 
        name: '📅 Today\'s Follow-ups', 
        filters: { followUpToday: true },
        scope: 'system'
      },
      { 
        id: 'overdue', 
        name: '⏰ Overdue Follow-ups', 
        filters: { followUpOverdue: true },
        scope: 'system'
      },
      { 
        id: 'unassigned', 
        name: '👤 Unassigned Leads', 
        filters: { assigned_to: null },
        scope: 'system'
      },
      { 
        id: 'my-leads', 
        name: '📋 My Leads', 
        filters: { assigned_to: userId },
        scope: 'system'
      }
    ];
    
    menuItems.push({
      key: 'quick-header',
      label: <div style={{ fontWeight: 'bold', color: '#8c8c8c', fontSize: 11, textTransform: 'uppercase' }}>Quick Filters</div>,
      disabled: true
    });
    
    quickFilters.forEach(filter => {
      menuItems.push({
        key: filter.id,
        label: filter.name,
        onClick: () => applyFilter(filter)
      });
    });
    
    // Personal filters
    const personalFilters = savedFilters.filter(f => f.scope === 'personal');
    if (personalFilters.length > 0) {
      menuItems.push({ type: 'divider' });
      menuItems.push({
        key: 'personal-header',
        label: (
          <div style={{ fontWeight: 'bold', color: '#8c8c8c', fontSize: 11, textTransform: 'uppercase' }}>
            <UserOutlined /> My Filters
          </div>
        ),
        disabled: true
      });
      
      personalFilters
        .sort((a, b) => (b.usageCount || 0) - (a.usageCount || 0))
        .forEach(filter => {
          menuItems.push({
            key: `personal-${filter.id}`,
            label: (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div>{filter.name}</div>
                  <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                    {getFilterSummary(filter.filters)}
                  </div>
                </div>
                <DeleteOutlined 
                  style={{ color: '#ff4d4f', marginLeft: 8 }}
                  onClick={(e) => deleteFilter(filter, e)}
                />
              </div>
            ),
            onClick: () => applyFilter(filter)
          });
        });
    }
    
    // Team filters
    const teamFilters = savedFilters.filter(f => f.scope === 'team');
    if (teamFilters.length > 0) {
      menuItems.push({ type: 'divider' });
      menuItems.push({
        key: 'team-header',
        label: (
          <div style={{ fontWeight: 'bold', color: '#8c8c8c', fontSize: 11, textTransform: 'uppercase' }}>
            <TeamOutlined /> Team Filters
          </div>
        ),
        disabled: true
      });
      
      teamFilters
        .sort((a, b) => (b.usageCount || 0) - (a.usageCount || 0))
        .forEach(filter => {
          menuItems.push({
            key: `team-${filter.id}`,
            label: (
              <div>
                <div>{filter.name}</div>
                <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                  {getFilterSummary(filter.filters)}
                </div>
              </div>
            ),
            onClick: () => applyFilter(filter)
          });
        });
    }
    
    // Save current filter option
    menuItems.push({ type: 'divider' });
    menuItems.push({
      key: 'save-current',
      icon: <PlusOutlined />,
      label: <span style={{ color: '#1890ff' }}>Save Current Filter</span>,
      onClick: () => setModalVisible(true)
    });
    
    return menuItems;
  };

  return (
    <>
      <Dropdown
        menu={{ items: buildMenu() }}
        trigger={['click']}
      >
        <Button icon={<StarOutlined />}>
          Saved Filters
          {savedFilters.length > 0 && (
            <Tag style={{ marginLeft: 8 }}>{savedFilters.length}</Tag>
          )}
        </Button>
      </Dropdown>

      {/* Save Filter Modal */}
      <Modal
        title="Save Current Filter"
        open={modalVisible}
        onOk={() => form.submit()}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={saveFilter}
          initialValues={{ shared: false }}
        >
          <Form.Item
            name="name"
            label="Filter Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="e.g., High Priority Hot Leads" />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="Description (Optional)"
          >
            <Input.TextArea 
              rows={2} 
              placeholder="Brief description of this filter..."
            />
          </Form.Item>
          
          <Form.Item
            name="shared"
            label="Share with Team"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          
          <div style={{ 
            padding: 12, 
            background: '#f5f5f5', 
            borderRadius: 4,
            marginTop: 8
          }}>
            <div style={{ fontSize: 11, color: '#8c8c8c', marginBottom: 4 }}>
              Current Filter:
            </div>
            <div style={{ fontSize: 12 }}>
              {getFilterSummary(currentFilters)}
            </div>
          </div>
        </Form>
      </Modal>
    </>
  );
};

export default SavedFilters;
