import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import viVN from 'antd/locale/vi_VN';
import './App.css';
// import MainLayout from './components/Layout/MainLayout';
const MainLayout = React.lazy(() => import('./components/Layout/MainLayout'));
const LoginPage = React.lazy(() => import('./components/Auth/LoginPage'));
const RegisterPage = React.lazy(() => import('./components/Auth/RegisterPage'));
const EmployeeList = React.lazy(() => import('./components/Employees/EmployeeList'));
const MonthlyReport = React.lazy(() => import('./components/Reports/MonthlyReport'));
const AttendancePage = React.lazy(() => import('./components/Attendance/AttendancePage'));
const HolidayPage = React.lazy(() => import('./components/HolidayPage/HolidayPage'));
function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showRegister, setShowRegister] = useState(false);

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    
    if (token && user) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLoginSuccess = (user) => {
    setIsAuthenticated(true);
    setShowRegister(false);
  };

  const handleRegisterSuccess = () => {
    setShowRegister(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setShowRegister(false);
  };

  const switchToRegister = () => {
    setShowRegister(true);
  };

  const switchToLogin = () => {
    setShowRegister(false);
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return (
      <ConfigProvider locale={viVN}>
        {showRegister ? (
          <RegisterPage 
            onRegisterSuccess={handleRegisterSuccess}
            onSwitchToLogin={switchToLogin}
          />
        ) : (
          <LoginPage 
            onLoginSuccess={handleLoginSuccess}
            onSwitchToRegister={switchToRegister}
          />
        )}
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={viVN}>
      <Router>
        <Routes>
          <Route path="/" element={<MainLayout onLogout={handleLogout} />}>
            <Route index element={<AttendancePage />} />
            <Route path="employees" element={<EmployeeList />} />
            <Route path="/holidays" element={<HolidayPage />} />
            <Route path="reports" element={<MonthlyReport />} />
          </Route>
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;