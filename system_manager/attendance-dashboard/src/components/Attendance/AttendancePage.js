import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Row,
  Col,
  Statistic,
  Button,
  Input,
  Space,
  Tag,
  message,
  Spin,
  Alert
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  UserOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { attendanceAPI, reportAPI } from '../../services/api';
import moment from 'moment';

const AttendancePage = () => {
  const [loading, setLoading] = useState(false);
  const [attendanceData, setAttendanceData] = useState([]);
  const [selectedDate, setSelectedDate] = useState(moment().format('YYYY-MM-DD')); // String format
  const [searchText, setSearchText] = useState('');
  const [stats, setStats] = useState({
    total: 0,
    totalEmployees: 0,
    onTime: 0,
    late: 0,
    avgHours: 0
  });

  useEffect(() => {
    loadAttendanceData();
  }, [selectedDate]);

const loadAttendanceData = async () => {
  try {
    setLoading(true);
    const response = await reportAPI.getDailyReport(selectedDate);
    const data = response.data.data || [];
    
    setAttendanceData(data);
    
    // Fix statistics calculation
    const totalEmployees = response.data.total_employees || 0;
    const present = data.filter(item => item.first_time && item.last_time).length;
    const absent = data.filter(item => !item.first_time && item.status === 'absent').length;
    const paidLeave = data.filter(item => !item.first_time && item.status === 'paid_leave').length;
    const late = data.filter(item => item.first_time && item.late_minutes > 0).length;
    const onTime = data.filter(item => item.first_time && item.late_minutes === 0).length;
    
    const avgHours = present > 0 
      ? (data.filter(item => item.work_hours > 0)
            .reduce((sum, item) => sum + item.work_hours, 0) / present).toFixed(1)
      : 0;

    setStats({ 
      total: present, 
      totalEmployees, 
      onTime, 
      late, 
      avgHours,
      absent,
      paidLeave 
    });

  } catch (error) {
    console.error('Error loading attendance:', error);
    message.error('Không thể tải dữ liệu điểm danh');
  } finally {
    setLoading(false);
  }
};

  // Handle date input change
  const handleDateChange = (e) => {
    setSelectedDate(e.target.value);
  };

  const filteredData = attendanceData.filter(item =>
    item.name.toLowerCase().includes(searchText.toLowerCase()) ||
    item.id_real.toLowerCase().includes(searchText.toLowerCase())
  );

const columns = [
  {
    title: 'Mã NV',
    dataIndex: 'id_real',
    key: 'id_real',
    width: 100,
    fixed: 'left'
  },
  {
    title: 'Họ và tên',
    dataIndex: 'name',
    key: 'name',
    width: 200,
    fixed: 'left'
  },
  {
    title: 'Chức vụ',
    dataIndex: 'role',
    key: 'role',
    width: 120,
    render: (role) => (
      <Tag color={role === 'employee' ? 'blue' : 'green'}>
        {role === 'employee' ? 'Nhân viên' : 'Giảng viên'}
      </Tag>
    )
  },
  {
    title: 'Giờ vào',
    dataIndex: 'first_time',
    key: 'first_time',
    width: 100,
    render: (time) => (
      time ? (
        <span style={{ fontFamily: 'monospace' }}>{time}</span>
      ) : (
        <span style={{ color: '#999' }}>--:--</span>
      )
    )
  },
  {
    title: 'Giờ ra',
    dataIndex: 'last_time',
    key: 'last_time',
    width: 100,
    render: (time) => (
      time ? (
        <span style={{ fontFamily: 'monospace' }}>{time}</span>
      ) : (
        <span style={{ color: '#999' }}>--:--</span>
      )
    )
  },
  {
    title: 'Tổng giờ',
    dataIndex: 'work_hours',
    key: 'work_hours',
    width: 100,
    render: (hours) => (
      hours > 0 ? (
        <Tag color="cyan">{hours}h</Tag>
      ) : (
        <Tag color="default">0h</Tag>
      )
    ),
    sorter: (a, b) => a.work_hours - b.work_hours
  },
  {
    title: 'Trạng thái',
    key: 'status',
    width: 120,
    render: (_, record) => {
      // Fix logic: Kiểm tra có điểm danh hay không
      if (!record.first_time || !record.last_time) {
        // Chưa điểm danh
        if (record.status === 'paid_leave') {
          return (
            <Tag color="blue" icon={<ClockCircleOutlined />}>
              Nghỉ có lương
            </Tag>
          );
        } else if (record.is_holiday) {
          return (
            <Tag color="purple" icon={<ClockCircleOutlined />}>
              Ngày lễ
            </Tag>
          );
        } else {
          return (
            <Tag color="red" icon={<WarningOutlined />}>
              Vắng mặt
            </Tag>
          );
        }
      } else {
        // Đã điểm danh
        if (record.late_minutes > 0) {
          return (
            <Tag color="orange" icon={<WarningOutlined />}>
              Muộn {record.late_minutes}p
            </Tag>
          );
        } else {
          return (
            <Tag color="green" icon={<ClockCircleOutlined />}>
              Đúng giờ
            </Tag>
          );
        }
      }
    }
  },
  {
    title: 'Lương ngày',
    dataIndex: 'daily_salary',
    key: 'daily_salary',
    width: 150,
    render: (salary, record) => {
      if (salary > 0) {
        return (
          <div>
            <span style={{ color: '#1890ff', fontWeight: 'bold' }}>
              {Number(salary).toLocaleString()} VNĐ
            </span>
            {record.is_holiday && (
              <div style={{ fontSize: '11px', color: '#722ed1' }}>
                Hệ số: x{record.holiday_multiplier}
              </div>
            )}
          </div>
        );
      } else {
        return (
          <span style={{ color: '#999' }}>
            0 VNĐ
          </span>
        );
      }
    },
    sorter: (a, b) => a.daily_salary - b.daily_salary
  }
];

  return (
    <div>
      {/* Header */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Row gutter={[16, 16]} align="middle">
              <Col flex="auto">
                <h2 style={{ margin: 0 }}>Quản lý điểm danh</h2>
                <p style={{ margin: 0, color: '#666' }}>
                  Theo dõi và quản lý điểm danh nhân viên hàng ngày
                </p>
              </Col>
              <Col>
                <Space>
                  {/* HTML date input thay cho DatePicker */}
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={handleDateChange}
                    style={{
                      padding: '6px 12px',
                      border: '1px solid #d9d9d9',
                      borderRadius: '6px',
                      fontSize: '14px',
                      outline: 'none',
                      transition: 'border-color 0.3s',
                    }}
                    onFocus={(e) => e.target.style.borderColor = '#1890ff'}
                    onBlur={(e) => e.target.style.borderColor = '#d9d9d9'}
                  />
                  <Button
                    type="primary"
                    icon={<ReloadOutlined />}
                    onClick={loadAttendanceData}
                    loading={loading}
                  >
                    Làm mới
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Statistics */}
<Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="Tổng NV"
        value={stats.totalEmployees}
        prefix={<UserOutlined />}
        valueStyle={{ color: '#1890ff' }}
      />
    </Card>
  </Col>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="Có mặt"
        value={stats.total}
        prefix={<ClockCircleOutlined />}
        valueStyle={{ color: '#52c41a' }}
      />
    </Card>
  </Col>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="Đúng giờ"
        value={stats.onTime}
        prefix={<ClockCircleOutlined />}
        valueStyle={{ color: '#52c41a' }}
      />
    </Card>
  </Col>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="Đi muộn"
        value={stats.late}
        prefix={<WarningOutlined />}
        valueStyle={{ color: '#ff4d4f' }}
      />
    </Card>
  </Col>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="Vắng mặt"
        value={stats.absent}
        prefix={<WarningOutlined />}
        valueStyle={{ color: '#ff4d4f' }}
      />
    </Card>
  </Col>
  <Col xs={24} sm={12} md={4}>
    <Card>
      <Statistic
        title="TB giờ làm"
        value={stats.avgHours}
        suffix="h"
        valueStyle={{ color: '#722ed1' }}
      />
    </Card>
  </Col>
</Row>

      {/* Attendance Table */}
      <Card
        title={`Điểm danh ngày ${moment(selectedDate).format('DD/MM/YYYY')}`}
        extra={
          <Input
            placeholder="Tìm kiếm nhân viên..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 250 }}
          />
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : filteredData.length === 0 ? (
          <Alert
            message="Không có dữ liệu điểm danh"
            description={
              attendanceData.length === 0 
                ? "Chưa có ai điểm danh trong ngày được chọn."
                : "Không tìm thấy nhân viên phù hợp với từ khóa tìm kiếm."
            }
            type="info"
            showIcon
            style={{ margin: '20px 0' }}
          />
        ) : (
          <Table
            columns={columns}
            dataSource={filteredData}
            rowKey="id_real"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `Tổng ${total} nhân viên`,
            }}
            scroll={{ x: 1000 }}
            size="middle"
          />
        )}
      </Card>
    </div>
  );
};

export default AttendancePage;