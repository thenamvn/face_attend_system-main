import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  message,
  Row,
  Col,
  Tag,
  Typography,
  Select,
  Switch,
  DatePicker,
  Popconfirm
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import { holidayAPI } from '../../services/api';
import HolidayModal from './HolidayModal';
import moment from 'moment';

const { Title } = Typography;
const { Option } = Select;

const HolidayPage = () => {
  const [holidays, setHolidays] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingHoliday, setEditingHoliday] = useState(null);
  const [searchText, setSearchText] = useState('');
  const [selectedYear, setSelectedYear] = useState(moment().year());

  useEffect(() => {
    loadHolidays();
  }, [selectedYear]);

  const loadHolidays = async () => {
    try {
      setLoading(true);
      const response = await holidayAPI.getByYear(selectedYear);
      setHolidays(response.data.data || []);
    } catch (error) {
      console.error('Error loading holidays:', error);
      message.error('Không thể tải danh sách ngày nghỉ lễ');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingHoliday(null);
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingHoliday(record);
    setModalVisible(true);
  };

  const handleDelete = async (record) => {
    try {
      await holidayAPI.delete(record.id);
      message.success('Xóa ngày nghỉ lễ thành công');
      loadHolidays();
    } catch (error) {
      console.error('Error deleting holiday:', error);
      message.error('Không thể xóa ngày nghỉ lễ');
    }
  };

  const handleModalOk = () => {
    setModalVisible(false);
    loadHolidays();
  };

  const handleToggleActive = async (record) => {
    try {
      await holidayAPI.update(record.id, {
        ...record,
        is_active: !record.is_active
      });
      message.success(record.is_active ? 'Đã vô hiệu hóa' : 'Đã kích hoạt');
      loadHolidays();
    } catch (error) {
      console.error('Error toggling holiday status:', error);
      message.error('Không thể cập nhật trạng thái');
    }
  };

  const filteredHolidays = holidays.filter(holiday =>
    holiday.name?.toLowerCase().includes(searchText.toLowerCase()) ||
    holiday.description?.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns = [
    {
      title: 'Ngày',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (startDate, record) => {
        if (record.type === 'period') {
          return (
            <div>
              <div>{moment(startDate).format('DD/MM/YYYY')}</div>
              <div style={{ fontSize: '12px', color: '#666' }}>
                đến {moment(record.end_date).format('DD/MM/YYYY')}
              </div>
            </div>
          );
        }
        return moment(startDate).format('DD/MM/YYYY');
      },
      sorter: (a, b) => moment(a.start_date).unix() - moment(b.start_date).unix(),
    },
    {
      title: 'Tên ngày nghỉ',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <div>
          <strong>{name}</strong>
          {record.type === 'period' && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              Kỳ nghỉ {moment(record.end_date).diff(moment(record.start_date), 'days') + 1} ngày
            </div>
          )}
        </div>
      )
    },
    {
      title: 'Loại nghỉ',
      dataIndex: 'leave_type',
      key: 'leave_type',
      width: 130,
      render: (leaveType) => {
        const colors = {
          'paid_holiday': 'green',
          'unpaid_leave': 'red',
          'overtime_holiday': 'purple'
        };
        const texts = {
          'paid_holiday': 'Có lương',
          'unpaid_leave': 'Không lương',
          'overtime_holiday': 'Làm thêm'
        };
        return <Tag color={colors[leaveType]}>{texts[leaveType]}</Tag>;
      },
    },
    {
      title: 'Chính sách lương',
      dataIndex: 'salary_policy',
      key: 'salary_policy',
      width: 130,
      render: (policy, record) => {
        const colors = {
          'full_pay': 'green',
          'no_pay': 'red', 
          'multiplier_pay': 'purple',
          'partial_pay': 'orange'
        };
        const texts = {
          'full_pay': 'Đủ lương',
          'no_pay': 'Không lương',
          'multiplier_pay': 'Theo hệ số',
          'partial_pay': 'Một phần'
        };
        return (
          <div>
            <Tag color={colors[policy]}>{texts[policy]}</Tag>
            <div style={{ fontSize: '11px', color: '#666' }}>
              x{record.salary_multiplier}
            </div>
          </div>
        );
      },
    },
    {
      title: 'Làm việc',
      dataIndex: 'allow_work',
      key: 'allow_work',
      width: 80,
      render: (allowWork) => (
        <Tag color={allowWork ? 'blue' : 'gray'}>
          {allowWork ? 'Được' : 'Không'}
        </Tag>
      ),
    },
    {
      title: 'Áp dụng cho',
      dataIndex: 'applies_to',
      key: 'applies_to',
      width: 120,
      render: (appliesTo) => {
        const colors = {
          'all': 'green',
          'employee_only': 'blue',
          'lecturer_only': 'orange'
        };
        const texts = {
          'all': 'Tất cả',
          'employee_only': 'Nhân viên',
          'lecturer_only': 'Giảng viên'
        };
        return <Tag color={colors[appliesTo]}>{texts[appliesTo]}</Tag>;
      },
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive, record) => (
        <Switch
          checked={isActive}
          onChange={() => handleToggleActive(record)}
          size="small"
        />
      ),
    },
    {
      title: 'Hành động',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="primary"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Sửa
          </Button>
          <Popconfirm
            title="Xóa ngày nghỉ"
            description="Bạn có chắc chắn muốn xóa ngày nghỉ này?"
            onConfirm={() => handleDelete(record)}
            okText="Xóa"
            cancelText="Hủy"
          >
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
            >
              Xóa
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // Generate year options (current year ± 5 years)
  const currentYear = moment().year();
  const yearOptions = [];
  for (let i = currentYear - 5; i <= currentYear + 5; i++) {
    yearOptions.push(
      <Option key={i} value={i}>{i}</Option>
    );
  }

  return (
    <div>
      {/* Header */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card>
            <Row gutter={[16, 16]} align="middle">
              <Col flex="auto">
                <Title level={2} style={{ margin: 0 }}>
                  <CalendarOutlined /> Quản lý ngày nghỉ lễ
                </Title>
                <p style={{ margin: 0, color: '#666' }}>
                  Quản lý danh sách ngày nghỉ lễ và hệ số lương
                </p>
              </Col>
              <Col>
                <Space>
                  <Select
                    value={selectedYear}
                    onChange={setSelectedYear}
                    style={{ width: 100 }}
                  >
                    {yearOptions}
                  </Select>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={handleCreate}
                  >
                    Thêm ngày lễ
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Search & Table */}
      <Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Input
              placeholder="Tìm kiếm theo tên ngày lễ hoặc mô tả..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ maxWidth: 400 }}
            />
          </Col>
          <Col>
            <Space>
              <span>Tổng: {filteredHolidays.length} ngày lễ</span>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredHolidays}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `Tổng ${total} ngày lễ`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>

      <HolidayModal
        visible={modalVisible}
        holiday={editingHoliday}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
      />
    </div>
  );
};

export default HolidayPage;