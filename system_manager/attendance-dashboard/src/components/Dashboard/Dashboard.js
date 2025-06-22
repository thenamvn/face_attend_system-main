// src/components/Dashboard/Dashboard.js
import React, { useState, useEffect } from 'react';
import { 
  Row, 
  Col, 
  Card, 
  Statistic, 
  Table, 
  Typography, 
  DatePicker,
  Spin,
  Alert 
} from 'antd';
import {
  UserOutlined,
  ClockCircleOutlined,
  DollarOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { attendanceAPI, reportAPI, employeeAPI } from '../../services/api';
import moment from 'moment';

const { Title } = Typography;

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalEmployees: 0,
    todayAttendance: 0,
    lateEmployees: 0,
    averageWorkHours: 0
  });
  const [todayReport, setTodayReport] = useState([]);
  const [selectedDate, setSelectedDate] = useState(moment());

  useEffect(() => {
    loadDashboardData();
  }, [selectedDate]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const today = selectedDate.format('YYYY-MM-DD');
      
      // Load basic stats
      const [employeesRes, dailyReportRes] = await Promise.all([
        employeeAPI.getAll(),
        reportAPI.getDailyReport(today)
      ]);

      const employees = employeesRes.data.data;
      const dailyData = dailyReportRes.data.data;

      // Calculate stats
      const totalEmployees = employees.length;
      const todayAttendance = dailyData.length;
      const lateEmployees = dailyData.filter(emp => emp.late_minutes > 0).length;
      const averageWorkHours = dailyData.length > 0 
        ? (dailyData.reduce((sum, emp) => sum + emp.work_hours, 0) / dailyData.length).toFixed(1)
        : 0;

      setStats({
        totalEmployees,
        todayAttendance,
        lateEmployees,
        averageWorkHours
      });

      setTodayReport(dailyData);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Mã NV',
      dataIndex: 'id_real',
      key: 'id_real',
    },
    {
      title: 'Họ và tên',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Chức vụ',
      dataIndex: 'role',
      key: 'role',
      render: (role) => role === 'employee' ? 'Nhân viên' : 'Giảng viên'
    },
    {
      title: 'Giờ vào',
      dataIndex: 'first_time',
      key: 'first_time',
    },
    {
      title: 'Giờ ra',
      dataIndex: 'last_time',
      key: 'last_time',
    },
    {
      title: 'Tổng giờ',
      dataIndex: 'work_hours',
      key: 'work_hours',
      render: (hours) => `${hours}h`
    },
    {
      title: 'Muộn (phút)',
      dataIndex: 'late_minutes',
      key: 'late_minutes',
      render: (minutes) => (
        <span style={{ color: minutes > 0 ? '#ff4d4f' : '#52c41a' }}>
          {minutes}
        </span>
      )
    },
    {
      title: 'Lương ngày',
      dataIndex: 'daily_salary',
      key: 'daily_salary',
      render: (salary) => `${salary?.toLocaleString()} VNĐ`
    }
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Title level={2}>Dashboard</Title>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Tổng nhân viên"
              value={stats.totalEmployees}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Điểm danh hôm nay"
              value={stats.todayAttendance}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Số người muộn"
              value={stats.lateEmployees}
              prefix={<WarningOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="TB giờ làm việc"
              value={stats.averageWorkHours}
              suffix="h"
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Card 
        title="Báo cáo điểm danh"
        extra={
          <DatePicker
            value={selectedDate}
            onChange={setSelectedDate}
            format="DD/MM/YYYY"
          />
        }
      >
        {todayReport.length === 0 ? (
          <Alert
            message="Không có dữ liệu điểm danh"
            description="Chưa có ai điểm danh trong ngày được chọn."
            type="info"
            showIcon
          />
        ) : (
          <Table
            columns={columns}
            dataSource={todayReport}
            rowKey="id_real"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 800 }}
          />
        )}
      </Card>
    </div>
  );
};

export default Dashboard;