import React from 'react';
import { Layout, Button, Typography, Avatar, Space, Dropdown, message } from 'antd';
import { 
  MenuFoldOutlined, 
  MenuUnfoldOutlined, 
  UserOutlined,
  LogoutOutlined,
  SettingOutlined 
} from '@ant-design/icons';

const { Header } = Layout;
const { Title } = Typography;

const AppHeader = ({ collapsed, onToggle, onLogout }) => {
  const handleMenuClick = ({ key }) => {
    switch (key) {
      case 'logout':
        onLogout();
        message.success('Đăng xuất thành công');
        break;
      case 'profile':
        message.info('Chức năng đang phát triển');
        break;
      case 'settings':
        message.info('Chức năng đang phát triển');
        break;
      default:
        break;
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Thông tin cá nhân',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Cài đặt',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Đăng xuất',
      danger: true,
    },
  ];

  // Get user info from localStorage
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <Header style={{ 
      padding: '0 24px', 
      background: '#fff', 
      display: 'flex', 
      alignItems: 'center',
      borderBottom: '1px solid #f0f0f0',
      position: 'sticky',
      top: 0,
      zIndex: 999,
      boxShadow: '0 2px 8px #f0f1f2'
    }}>
      <Button
        type="text"
        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        onClick={onToggle}
        style={{ 
          fontSize: '16px', 
          width: 64, 
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      />
      
      <Title level={4} style={{ 
        margin: 0, 
        flex: 1,
        color: '#001529'
      }}>
        Hệ thống quản lý điểm danh
      </Title>

      <Dropdown
        menu={{ items: userMenuItems, onClick: handleMenuClick }}
        placement="bottomRight"
        trigger={['click']}
      >
        <Space style={{ cursor: 'pointer' }}>
          <Avatar 
            icon={<UserOutlined />} 
            style={{ backgroundColor: '#1890ff' }}
          />
          <span style={{ color: '#001529' }}>
            {user.name || 'User'}
          </span>
        </Space>
      </Dropdown>
    </Header>
  );
};

export default AppHeader;