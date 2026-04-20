import React, { useState } from 'react';
import { Modal, Form, Input, Select, Button, message } from 'antd';
import { UserAddOutlined } from '@ant-design/icons';
import { usersAPI } from '../api/api';

const { Option } = Select;

const CreateUserModal = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleCreate = async (values) => {
    setLoading(true);
    try {
      await usersAPI.create({
        full_name: values.full_name,
        email: values.email,
        phone: values.phone || '',
        password: values.password,
        role: values.role,
        hospital_id: values.hospital_id || null,
        reports_to: values.reports_to || null,
        is_active: true,
      });

      message.success('User created successfully!');
      form.resetFields();
      onSuccess();
      onClose();
    } catch (error) {
      console.error('Create user error:', error);
      if (error.response?.status === 400) {
        message.error(error.response?.data?.detail || 'Email already registered');
      } else if (error.response?.status === 403) {
        message.error('You do not have permission to create users');
      } else {
        message.error('Failed to create user');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={<><UserAddOutlined /> Create New User</>}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={600}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleCreate}
        requiredMark="optional"
      >
        <Form.Item
          name="full_name"
          label="Full Name"
          rules={[{ required: true, message: 'Please enter full name' }]}
        >
          <Input placeholder="John Doe" />
        </Form.Item>

        <Form.Item
          name="email"
          label="Email (Used for login)"
          rules={[
            { required: true, message: 'Please enter email' },
            { type: 'email', message: 'Please enter valid email' }
          ]}
        >
          <Input placeholder="john@example.com" />
        </Form.Item>

        <Form.Item
          name="phone"
          label="Phone"
        >
          <Input placeholder="+91 9876543210" />
        </Form.Item>

        <Form.Item
          name="password"
          label="Password"
          rules={[
            { required: true, message: 'Please enter password' },
            { min: 6, message: 'Password must be at least 6 characters' }
          ]}
        >
          <Input.Password placeholder="Minimum 6 characters" />
        </Form.Item>

        <Form.Item
          name="role"
          label="Role"
          rules={[{ required: true, message: 'Please select role' }]}
        >
          <Select placeholder="Select role">
            <Option value="Counselor">Counselor</Option>
            <Option value="Team Leader">Team Leader</Option>
            <Option value="Manager">Manager</Option>
            <Option value="Hospital Admin">Hospital Admin</Option>
            <Option value="Super Admin">Super Admin</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="hospital_id"
          label="Hospital ID (Optional for Super Admin)"
        >
          <Input type="number" placeholder="Leave empty for Super Admin" />
        </Form.Item>

        <Form.Item
          name="reports_to"
          label="Reports To (Optional)"
        >
          <Input placeholder="Manager/Team Leader email" />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
          <Button onClick={onClose} style={{ marginRight: 8 }}>
            Cancel
          </Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            Create User
          </Button>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateUserModal;
