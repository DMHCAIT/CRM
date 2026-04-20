import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
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
import GoogleSheetSync from './pages/GoogleSheetSync';
import AdvancedAnalytics from './pages/AdvancedAnalytics';
import CustomReportBuilder from './pages/CustomReportBuilder';
import AdvancedSegmentation from './pages/AdvancedSegmentation';
import PerformanceMonitoring from './pages/PerformanceMonitoring';
// import AutomationSettings from './pages/AutomationSettings'; // Phase 1 - Not yet created
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

// Protected Route Wrapper
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>Loading...</div>;
  }

  return isAuthenticated() ? children : <Navigate to="/login" replace />;
};

// App Routes Component (needs to be inside AuthProvider)
const AppRoutes = () => {
  const { isAuthenticated, login } = useAuth();

  return (
    <Router>
      <Routes>
        {/* Public Route */}
        <Route 
          path="/login" 
          element={
            isAuthenticated() ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage onLoginSuccess={login} />
            )
          } 
        />

        {/* Protected Routes */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
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
                  <Route path="/advanced-analytics" element={<AdvancedAnalytics />} />
                  <Route path="/reports" element={<CustomReportBuilder />} />
                  <Route path="/segmentation" element={<AdvancedSegmentation />} />
                  <Route path="/performance" element={<PerformanceMonitoring />} />
                  
                  {/* Automation - Phase 1 feature, not yet implemented */}
                  {/* <Route path="/automation" element={<AutomationSettings />} /> */}
                  
                  {/* Resources */}
                  <Route path="/hospitals" element={<HospitalsPage />} />
                  <Route path="/courses" element={<CoursesPageEnhanced />} />
                  
                  {/* Team management */}
                  <Route path="/users" element={<UsersPage />} />
                  <Route path="/user-activity" element={<UserActivityPage />} />
                  
                  {/* Integrations */}
                  <Route path="/sheet-sync" element={<GoogleSheetSync />} />

                  {/* Audit Logs */}
                  {isFeatureEnabled('AUDIT_LOGS') && (
                    <Route path="/audit-logs" element={<AuditLogs />} />
                  )}
                </Routes>
              </ProfessionalLayout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
};

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
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </ConfigProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
