// src/components/Reports/MonthlyReport.js
import React, { useState } from 'react';
import {
  Card,
  Table,
  DatePicker,
  Button,
  Row,
  Col,
  Statistic,
  message,
  Spin,
  Alert
} from 'antd';
import { DownloadOutlined, DollarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { reportAPI } from '../../services/api';
import moment from 'moment';

const MonthlyReport = () => {
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState([]);
  const [selectedDate, setSelectedDate] = useState(moment());
  const [summary, setSummary] = useState({
    totalSalary: 0,
    totalHours: 0,
    totalEmployees: 0
  });

  const loadMonthlyReport = async () => {
    try {
      setLoading(true);
      const year = selectedDate.year();
      const month = selectedDate.month() + 1;

      const response = await reportAPI.getMonthlyReport(year, month);
      const data = response.data.data;

      setReportData(data);

      // Calculate summary
      const totalSalary = data.reduce((sum, emp) => sum + emp.total_salary, 0);
      const totalHours = data.reduce((sum, emp) => sum + emp.total_hours, 0);

      setSummary({
        totalSalary,
        totalHours,
        totalEmployees: data.length
      });

    } catch (error) {
      message.error('Không thể tải báo cáo tháng');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const year = selectedDate.year();
      const month = selectedDate.month() + 1;

      const response = await reportAPI.exportMonthlyCSV(year, month);

      // Add BOM for UTF-8
      const BOM = '\uFEFF';
      const csvData = BOM + response.data;

      const blob = new Blob([csvData], {
        type: 'text/csv;charset=utf-8;'
      });

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `salary_report_${month}_${year}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      message.success('Xuất báo cáo thành công');
    } catch (error) {
      console.error('Export CSV error:', error);
      message.error('Không thể xuất báo cáo');
    }
  };

  const columns = [
    {
      title: 'Mã NV',
      dataIndex: 'id_real',
      key: 'id_real',
      width: 100,
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
      title: 'Tổng giờ',
      dataIndex: 'total_hours',
      key: 'total_hours',
      render: (hours) => `${hours}h`,
      sorter: (a, b) => a.total_hours - b.total_hours,
    },
    {
      title: 'Số ngày làm',
      dataIndex: 'total_days_worked',
      key: 'total_days_worked',
      sorter: (a, b) => a.total_days_worked - b.total_days_worked,
    },
    {
      title: 'Ngày muộn',
      dataIndex: 'late_days',
      key: 'late_days',
      render: (days) => (
        <span style={{ color: days > 0 ? '#ff4d4f' : '#52c41a' }}>
          {days}
        </span>
      ),
      sorter: (a, b) => a.late_days - b.late_days,
    },
    {
      title: 'Phút muộn',
      dataIndex: 'total_late_minutes',
      key: 'total_late_minutes',
      render: (minutes) => (
        <span style={{ color: minutes > 0 ? '#ff4d4f' : '#52c41a' }}>
          {minutes}
        </span>
      ),
      sorter: (a, b) => a.total_late_minutes - b.total_late_minutes,
    },
    {
      title: 'Lương/giờ',
      dataIndex: 'hourly_rate',
      key: 'hourly_rate',
      render: (rate) => `${Number(rate).toLocaleString()} VNĐ`,
    },
    {
      title: 'Tổng lương',
      dataIndex: 'total_salary',
      key: 'total_salary',
      render: (salary) => (
        <strong style={{ color: '#1890ff' }}>
          {Number(salary).toLocaleString()} VNĐ
        </strong>
      ),
      sorter: (a, b) => a.total_salary - b.total_salary,
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <input
            type="month"
            value={selectedDate.format('YYYY-MM')}
            onChange={(e) => setSelectedDate(moment(e.target.value))}
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
            onClick={loadMonthlyReport}
            loading={loading}
            style={{ marginLeft: 8 }}
          >
            Tạo báo cáo
          </Button>
        </Col>
        <Col span={12} style={{ textAlign: 'right' }}>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExportCSV}
            disabled={reportData.length === 0}
          >
            Xuất CSV
          </Button>
        </Col>
      </Row>

      {reportData.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic
                title="Tổng nhân viên"
                value={summary.totalEmployees}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic
                title="Tổng giờ làm việc"
                value={summary.totalHours}
                suffix="h"
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic
                title="Tổng lương"
                value={summary.totalSalary}
                prefix={<DollarOutlined />}
                formatter={(value) => `${Number(value).toLocaleString()} VNĐ`}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card title={`Báo cáo lương tháng ${selectedDate.format('MM/YYYY')}`}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px' }}>
            <Spin size="large" />
          </div>
        ) : reportData.length === 0 ? (
          <Alert
            message="Không có dữ liệu"
            description="Chưa có dữ liệu báo cáo cho tháng được chọn. Vui lòng chọn tháng khác hoặc tạo báo cáo."
            type="info"
            showIcon
          />
        ) : (
          <Table
            columns={columns}
            dataSource={reportData}
            rowKey="id_real"
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `Tổng ${total} nhân viên`,
            }}
            scroll={{ x: 1200 }}
          />
        )}
      </Card>
    </div>
  );
};

export default MonthlyReport;