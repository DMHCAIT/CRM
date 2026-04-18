import React, { useState, useEffect } from 'react';
import { 
  Dropdown, 
  Button, 
  Menu, 
  Modal, 
  Input, 
  Select, 
  Form, 
  message, 
  Tag, 
  Space,
  Tooltip,
  Empty
} from 'antd';
import { 
  FileTextOutlined, 
  PlusOutlined, 
  ThunderboltOutlined,
  EditOutlined,
  StarOutlined
} from '@ant-design/icons';
import api from '../api';

const { TextArea } = Input;
const { Option } = Select;

/**
 * Note Templates Component
 * Quick insert pre-configured note templates with variable substitution
 * 
 * Props:
 * - leadId: string - ID of the lead for variable substitution
 * - onInsert: function - Callback when template is inserted
 * - position: 'dropdown' | 'inline' - Display mode
 */
const NoteTemplates = ({ leadId, onInsert, position = 'dropdown' }) => {
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [customModalVisible, setCustomModalVisible] = useState(false);
  const [renderModalVisible, setRenderModalVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [variables, setVariables] = useState({});
  const [renderedContent, setRenderedContent] = useState('');
  const [form] = Form.useForm();

  // Fetch templates on mount
  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/templates/notes');
      setTemplates(response.data.templates || []);
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      message.error('Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = async (template) => {
    setSelectedTemplate(template);
    
    // If template has variables, show modal to fill them
    if (template.variables && template.variables.length > 0) {
      setRenderModalVisible(true);
      
      // Pre-render with default values
      try {
        const response = await api.post(
          `/api/templates/notes/${template.id}/render`,
          { lead_id: leadId },
          { params: { lead_id: leadId } }
        );
        
        setRenderedContent(response.data.rendered_content);
        setVariables(response.data.variables_used || {});
      } catch (error) {
        console.error('Failed to render template:', error);
      }
    } else {
      // No variables, insert directly
      if (onInsert) {
        onInsert(template.content);
      }
      message.success('Template inserted');
    }
  };

  const handleRenderWithCustomVars = async () => {
    try {
      const response = await api.post(
        `/api/templates/notes/${selectedTemplate.id}/render`,
        {
          lead_id: leadId,
          variables: variables
        }
      );
      
      if (onInsert) {
        onInsert(response.data.rendered_content);
      }
      
      setRenderModalVisible(false);
      message.success('Template inserted');
    } catch (error) {
      console.error('Failed to render template:', error);
      message.error('Failed to insert template');
    }
  };

  const handleCreateCustomTemplate = async (values) => {
    try {
      await api.post('/api/templates/notes', {
        name: values.name,
        content: values.content,
        category: values.category || 'Custom'
      });
      
      message.success('Template created successfully');
      setCustomModalVisible(false);
      form.resetFields();
      fetchTemplates(); // Refresh list
    } catch (error) {
      console.error('Failed to create template:', error);
      message.error('Failed to create template');
    }
  };

  const handleVariableChange = (varName, value) => {
    setVariables(prev => ({
      ...prev,
      [varName]: value
    }));
  };

  // Group templates by category
  const groupedTemplates = templates.reduce((acc, template) => {
    const cat = template.category || 'Uncategorized';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(template);
    return acc;
  }, {});

  // Build menu for dropdown
  const buildMenu = () => {
    const menuItems = [];
    
    // Popular templates first
    const popularTemplates = templates
      .filter(t => t.usage_count > 0)
      .sort((a, b) => b.usage_count - a.usage_count)
      .slice(0, 3);
    
    if (popularTemplates.length > 0) {
      menuItems.push({
        key: 'popular-header',
        label: <div style={{ fontWeight: 'bold', color: '#8c8c8c', fontSize: 11, textTransform: 'uppercase' }}>Popular</div>,
        disabled: true
      });
      
      popularTemplates.forEach(template => {
        menuItems.push({
          key: `popular-${template.id}`,
          icon: <StarOutlined style={{ color: '#faad14' }} />,
          label: template.name,
          onClick: () => handleTemplateSelect(template)
        });
      });
      
      menuItems.push({ type: 'divider' });
    }
    
    // Group by category
    Object.keys(groupedTemplates).sort().forEach(category => {
      menuItems.push({
        key: `cat-${category}`,
        label: <div style={{ fontWeight: 'bold', color: '#8c8c8c', fontSize: 11, textTransform: 'uppercase' }}>{category}</div>,
        disabled: true
      });
      
      groupedTemplates[category].forEach(template => {
        menuItems.push({
          key: template.id,
          icon: template.is_system ? <FileTextOutlined /> : <EditOutlined />,
          label: (
            <Space>
              {template.name}
              {template.variables && template.variables.length > 0 && (
                <Tag color="blue" style={{ fontSize: 10 }}>{template.variables.length} vars</Tag>
              )}
            </Space>
          ),
          onClick: () => handleTemplateSelect(template)
        });
      });
      
      menuItems.push({ type: 'divider' });
    });
    
    // Add custom template option
    menuItems.push({
      key: 'create-custom',
      icon: <PlusOutlined />,
      label: <span style={{ color: '#1890ff' }}>Create Custom Template</span>,
      onClick: () => setCustomModalVisible(true)
    });
    
    return menuItems;
  };

  if (position === 'dropdown') {
    return (
      <>
        <Dropdown
          menu={{ items: buildMenu() }}
          trigger={['click']}
          disabled={loading}
        >
          <Button icon={<ThunderboltOutlined />} loading={loading}>
            Insert Template
          </Button>
        </Dropdown>

        {/* Variable Substitution Modal */}
        <Modal
          title={`Insert Template: ${selectedTemplate?.name}`}
          open={renderModalVisible}
          onOk={handleRenderWithCustomVars}
          onCancel={() => setRenderModalVisible(false)}
          width={600}
        >
          <div style={{ marginBottom: 16 }}>
            <strong>Preview:</strong>
            <div style={{ 
              padding: 12, 
              background: '#f5f5f5', 
              borderRadius: 4, 
              marginTop: 8,
              whiteSpace: 'pre-wrap'
            }}>
              {renderedContent}
            </div>
          </div>
          
          {selectedTemplate?.variables && selectedTemplate.variables.length > 0 && (
            <div>
              <strong>Customize Variables:</strong>
              <div style={{ marginTop: 8 }}>
                {selectedTemplate.variables.map(varName => (
                  <div key={varName} style={{ marginBottom: 8 }}>
                    <label style={{ display: 'block', marginBottom: 4, fontSize: 12, color: '#8c8c8c' }}>
                      {varName.replace(/_/g, ' ').toUpperCase()}
                    </label>
                    <Input
                      value={variables[varName] || ''}
                      onChange={(e) => handleVariableChange(varName, e.target.value)}
                      placeholder={`Enter ${varName}`}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </Modal>

        {/* Create Custom Template Modal */}
        <Modal
          title="Create Custom Template"
          open={customModalVisible}
          onOk={() => form.submit()}
          onCancel={() => {
            setCustomModalVisible(false);
            form.resetFields();
          }}
          width={600}
        >
          <Form
            form={form}
            layout="vertical"
            onFinish={handleCreateCustomTemplate}
          >
            <Form.Item
              name="name"
              label="Template Name"
              rules={[{ required: true, message: 'Please enter template name' }]}
            >
              <Input placeholder="e.g., Budget Discussion" />
            </Form.Item>
            
            <Form.Item
              name="category"
              label="Category"
            >
              <Select placeholder="Select category">
                {categories.map(cat => (
                  <Option key={cat} value={cat}>{cat}</Option>
                ))}
                <Option value="Custom">Custom</Option>
              </Select>
            </Form.Item>
            
            <Form.Item
              name="content"
              label="Template Content"
              rules={[{ required: true, message: 'Please enter template content' }]}
              extra="Use {{variable_name}} for variables, e.g., {{lead_name}}, {{course}}, {{date}}"
            >
              <TextArea 
                rows={4} 
                placeholder="Enter template content with variables..."
              />
            </Form.Item>
          </Form>
        </Modal>
      </>
    );
  }

  // Inline mode - show as list
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>Quick Templates</strong>
        <Button 
          size="small" 
          icon={<PlusOutlined />}
          onClick={() => setCustomModalVisible(true)}
        >
          Create
        </Button>
      </div>
      
      {templates.length === 0 ? (
        <Empty description="No templates available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {templates.slice(0, 6).map(template => (
            <Tooltip key={template.id} title={template.content.substring(0, 100) + '...'}>
              <Tag 
                style={{ cursor: 'pointer', padding: '4px 8px' }}
                onClick={() => handleTemplateSelect(template)}
              >
                {template.is_system && <FileTextOutlined style={{ marginRight: 4 }} />}
                {template.name}
              </Tag>
            </Tooltip>
          ))}
        </div>
      )}
    </div>
  );
};

export default NoteTemplates;
