import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Typography, Row, Col, Space } from 'antd';
import { UserOutlined, LockOutlined, LoginOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title, Text } = Typography;

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const LoginPage = ({ onLoginSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleLogin = async (values) => {
    setLoading(true);
    try {
      // OAuth2 requires form data format
      const formData = new FormData();
      formData.append('username', values.username); // Can be email or username
      formData.append('password', values.password);

      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      const { access_token, user } = response.data;

      // Store token and user in localStorage
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('user', JSON.stringify(user));

      message.success(`Welcome back, ${user.full_name}!`);
      
      // Call parent callback
      if (onLoginSuccess) {
        onLoginSuccess(user);
      }

    } catch (error) {
      console.error('Login error:', error);
      if (error.response?.status === 401) {
        message.error('Invalid username or password');
      } else if (error.response?.status === 403) {
        message.error('Your account is inactive. Please contact administrator.');
      } else {
        message.error('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <Card 
        style={{ 
          width: '100%', 
          maxWidth: 450,
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          borderRadius: 16
        }}
        bordered={false}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Logo/Header */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <div style={{
              width: 80,
              height: 80,
              margin: '0 auto 20px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <LoginOutlined style={{ fontSize: 40, color: 'white' }} />
            </div>
            <Title level={2} style={{ margin: 0 }}>Medical Education CRM</Title>
            <Text type="secondary">Sign in to your account</Text>
          </div>

          {/* Login Form */}
          <Form
            form={form}
            name="login"
            onFinish={handleLogin}
            layout="vertical"
            size="large"
            requiredMark={false}
          >
            <Form.Item
              name="username"
              label="Username or Email"
              rules={[
                { required: true, message: 'Please enter your username or email' }
              ]}
            >
              <Input 
                prefix={<UserOutlined />}
                placeholder="Enter username or email"
                autoComplete="username"
              />
            </Form.Item>

            <Form.Item
              name="password"
              label="Password"
              rules={[
                { required: true, message: 'Please enter your password' }
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Enter password"
                autoComplete="current-password"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button
                type="primary"
                htmlType="submit"
                block
                loading={loading}
                icon={<LoginOutlined />}
                style={{ height: 48 }}
              >
                Sign In
              </Button>
            </Form.Item>
          </Form>

          {/* Default Credentials Info */}
          <Card size="small" style={{ background: '#f0f5ff', borderColor: '#adc6ff' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <strong>First Time Setup:</strong><br />
              If no admin exists, create one using the /api/auth/bootstrap-admin endpoint
            </Text>
          </Card>
        </Space>
      </Card>
    </div>
  );
};

export default LoginPage;
