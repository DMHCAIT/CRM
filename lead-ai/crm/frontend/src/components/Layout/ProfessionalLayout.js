import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Users,
  Hospital,
  BookOpen,
  BarChart3,
  ChevronLeft,
  TrendingUp,
  GitBranch,
  UserPlus,
  Activity,
  Search,
  Shield,
} from 'lucide-react';
import SmartNotifications from '../../features/notifications/SmartNotifications';
import { isFeatureEnabled } from '../../config/featureFlags';

const ProfessionalLayout = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Show all menu items without any authentication/authorization
  const menuItems = [
    { key: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { key: '/leads', icon: Users, label: 'Leads' },
    { key: '/pipeline', icon: GitBranch, label: 'Pipeline' },
    { key: '/lead-analysis', icon: TrendingUp, label: 'Lead Analysis' },
    { key: '/hospitals', icon: Hospital, label: 'Hospitals' },
    { key: '/courses', icon: BookOpen, label: 'Courses' },
    { key: '/users', icon: UserPlus, label: 'Team' },
    { key: '/user-activity', icon: Activity, label: 'User Activity' },
    { key: '/analytics', icon: BarChart3, label: 'Analytics' },
    { key: '/audit-logs', icon: Shield, label: 'Audit Logs' },
  ];

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-secondary)' }}>
      {/* Sidebar */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 64 : 240 }}
        style={{
          background: 'var(--bg-primary)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Logo */}
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          padding: collapsed ? '0 16px' : '0 24px',
          borderBottom: '1px solid var(--border)',
          gap: 12
        }}>
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, var(--accent), #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18,
            flexShrink: 0
          }}>
            🏥
          </div>
          {!collapsed && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ 
                fontSize: 'var(--text-lg)', 
                fontWeight: 600,
                color: 'var(--text-primary)'
              }}
            >
              Med CRM
            </motion.span>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '16px 8px', overflowY: 'auto' }}>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.key;
            
            return (
              <motion.button
                key={item.key}
                onClick={() => navigate(item.key)}
                whileHover={{ x: 2 }}
                whileTap={{ scale: 0.98 }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: collapsed ? '12px' : '12px 16px',
                  marginBottom: 4,
                  borderRadius: 8,
                  border: 'none',
                  background: isActive ? 'var(--bg-tertiary)' : 'transparent',
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: 'var(--text-sm)',
                  fontWeight: isActive ? 500 : 400,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                }}
              >
                <Icon size={20} />
                {!collapsed && <span>{item.label}</span>}
              </motion.button>
            );
          })}
        </nav>

        {/* Collapse Toggle */}
        <div style={{ padding: 8, borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              width: '100%',
              padding: 12,
              borderRadius: 8,
              border: 'none',
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <motion.div
              animate={{ rotate: collapsed ? 180 : 0 }}
              transition={{ duration: 0.2 }}
            >
              <ChevronLeft size={20} />
            </motion.div>
          </button>
        </div>
      </motion.aside>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Header */}
        <header style={{
          height: 64,
          background: 'var(--bg-primary)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
        }}>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-primary)' }}>
            {menuItems.find(item => item.key === location.pathname)?.label || 'Dashboard'}
          </h1>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* Search */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 16px',
              background: 'var(--bg-secondary)',
              borderRadius: 8,
              width: 320,
            }}>
              <Search size={16} style={{ color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                placeholder="Search..."
                style={{
                  border: 'none',
                  background: 'transparent',
                  outline: 'none',
                  fontSize: 'var(--text-sm)',
                  color: 'var(--text-primary)',
                  width: '100%',
                }}
              />
            </div>

            {/* Smart Notifications */}
            {isFeatureEnabled('SMART_NOTIFICATIONS') && <SmartNotifications />}

            {/* User */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              paddingLeft: 16,
              borderLeft: '1px solid var(--border)',
            }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-primary)' }}>
                  Admin User
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>
                  admin@medcrm.com
                </div>
              </div>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: 8,
                background: 'linear-gradient(135deg, var(--accent), #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
              }}>
                AU
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main style={{ 
          flex: 1, 
          overflow: 'auto', 
          padding: 24,
        }}>
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
};

export default ProfessionalLayout;
