import React from 'react';
import { Modal, Typography, Row, Col, Tag, Divider } from 'antd';
import { getKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';

const { Title, Text } = Typography;

/**
 * Keyboard Shortcuts Help Modal
 * Displays all available keyboard shortcuts grouped by category
 * 
 * Props:
 * - visible: boolean - Show/hide modal
 * - onClose: function - Callback when modal is closed
 */
const KeyboardShortcutsHelp = ({ visible, onClose }) => {
  const shortcuts = getKeyboardShortcuts();

  return (
    <Modal
      title="⌨️ Keyboard Shortcuts"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <div style={{ maxHeight: '70vh', overflowY: 'auto', padding: '8px 0' }}>
        {shortcuts.map((category, idx) => (
          <div key={idx} style={{ marginBottom: 24 }}>
            <Title level={5} style={{ marginBottom: 12, color: '#1890ff' }}>
              {category.category}
            </Title>
            
            <div>
              {category.shortcuts.map((shortcut, sidx) => (
                <Row 
                  key={sidx} 
                  style={{ 
                    padding: '8px 0',
                    borderBottom: sidx < category.shortcuts.length - 1 ? '1px solid #f0f0f0' : 'none'
                  }}
                  align="middle"
                >
                  <Col span={12}>
                    <Text>{shortcut.description}</Text>
                  </Col>
                  <Col span={12} style={{ textAlign: 'right' }}>
                    {shortcut.keys.split('+').map((key, kidx, arr) => (
                      <span key={kidx}>
                        <Tag 
                          style={{ 
                            fontFamily: 'monospace',
                            fontSize: 12,
                            padding: '2px 8px',
                            margin: 0
                          }}
                        >
                          {key.trim()}
                        </Tag>
                        {kidx < arr.length - 1 && (
                          <span style={{ margin: '0 4px', color: '#8c8c8c' }}>+</span>
                        )}
                      </span>
                    ))}
                  </Col>
                </Row>
              ))}
            </div>
            
            {idx < shortcuts.length - 1 && <Divider />}
          </div>
        ))}
      </div>
      
      <Divider />
      
      <div style={{ textAlign: 'center', color: '#8c8c8c', fontSize: 12 }}>
        <Text type="secondary">
          Press <Tag style={{ fontSize: 11 }}>?</Tag> anytime to open this help
        </Text>
      </div>
    </Modal>
  );
};

export default KeyboardShortcutsHelp;
