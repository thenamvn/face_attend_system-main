import React, { useState, useEffect } from 'react';
import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';
import AppHeader from './Header';
import AppSidebar from './Sidebar';

const { Content } = Layout;

const MainLayout = ({ onLogout }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setCollapsed(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <AppSidebar collapsed={collapsed} isMobile={isMobile} />
      <Layout style={{ 
        marginLeft: isMobile ? 0 : (collapsed ? 80 : 200),
        transition: 'margin-left 0.2s'
      }}>
        <AppHeader 
          collapsed={collapsed} 
          onToggle={() => setCollapsed(!collapsed)}
          onLogout={onLogout}
        />
        <Content style={{ 
          margin: '24px 16px 0',
          overflow: 'auto'
        }}>
          <div style={{
            padding: isMobile ? 16 : 24,
            minHeight: 360,
            background: '#fff',
            borderRadius: 8
          }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;