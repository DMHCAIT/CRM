import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ProfessionalLayout from './components/Layout/ProfessionalLayout';
import RoleBasedDashboard from './pages/RoleBasedDashboard';
import LeadsPageEnhanced from './pages/LeadsPageEnhanced';
import LeadDetails from './pages/LeadDetails';
import HospitalsPage from './pages/HospitalsPage';
import CoursesPage from './pages/CoursesPage';
import CoursesPageEnhanced from './pages/CoursesPageEnhanced';
import AnalyticsPage from './pages/AnalyticsPage';
import UsersPage from './pages/UsersPage';
import DragDropPipeline from './features/pipeline/DragDropPipeline';
import UserActivityPage from './pages/UserActivityPage';
import LeadAnalysisPage from './pages/LeadAnalysisPage';
import AuditLogs from './features/audit/AuditLogs';
import { isFeatureEnabled } from './config/featureFlags';
import ErrorBoundary from './components/ErrorBoundary';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#3b82f6',
            borderRadius: 8,
            colorSuccess: '#10b981',
            colorWarning: '#f59e0b',
            colorError: '#ef4444',
            colorInfo: '#3b82f6',
            fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
          },
        }}
      >
        <Router>
          <ProfessionalLayout>
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              
              {/* Role-based dashboard */}
              <Route 
                path="/dashboard" 
                element={
                  isFeatureEnabled('ROLE_BASED_DASHBOARDS') ? (
                    <RoleBasedDashboard />
                  ) : (
                    <RoleBasedDashboard />
                  )
                } 
              />
              
              {/* Leads routes */}
              <Route path="/leads" element={<LeadsPageEnhanced />} />
              <Route path="/leads/:leadId" element={<LeadDetails />} />
              
              {/* Pipeline */}
              <Route path="/pipeline" element={<DragDropPipeline />} />
              
              {/* Analytics */}
              <Route path="/lead-analysis" element={<LeadAnalysisPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              
              {/* Resources */}
              <Route path="/hospitals" element={<HospitalsPage />} />
              <Route path="/courses" element={<CoursesPageEnhanced />} />
              
              {/* Team management */}
              <Route path="/users" element={<UsersPage />} />
              <Route path="/user-activity" element={<UserActivityPage />} />
              
              {/* Audit Logs */}
              {isFeatureEnabled('AUDIT_LOGS') && (
                <Route path="/audit-logs" element={<AuditLogs />} />
              )}
            </Routes>
          </ProfessionalLayout>
        </Router>
      </ConfigProvider>
    </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
