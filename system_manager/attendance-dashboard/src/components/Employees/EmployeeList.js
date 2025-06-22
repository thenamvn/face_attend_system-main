// src/components/Employees/EmployeeList.js
import React, { useState, useEffect } from "react";
import {
  Table,
  Button,
  Space,
  Modal,
  message,
  Tag,
  Input,
  Row,
  Col,
  Card,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined,
  UploadOutlined,
  SearchOutlined,
  CalendarOutlined, // Thêm icon mới
} from "@ant-design/icons";
import { employeeAPI } from "../../services/api";
import EmployeeModal from "./EmployeeModal";
import ImportModal from './ImportModal';
import WorkScheduleModal from './WorkScheduleModal'; // Import WorkScheduleModal

const EmployeeList = () => {
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [searchText, setSearchText] = useState("");
  const [importModalVisible, setImportModalVisible] = useState(false);

    // Thêm state cho WorkScheduleModal
  const [scheduleModalVisible, setScheduleModalVisible] = useState(false);
  const [scheduleEmployee, setScheduleEmployee] = useState(null);

  useEffect(() => {
    loadEmployees();
  }, []);

  const handleExportCSV = async () => {
    try {
      const response = await employeeAPI.exportCSV();
      
      // Add BOM for UTF-8
      const BOM = '\uFEFF';
      const csvData = BOM + response.data;
      
      const blob = new Blob([csvData], { 
        type: 'text/csv;charset=utf-8;' 
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'danh_sach_nhan_vien.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      message.success('Xuất file thành công');
    } catch (error) {
      console.error('Export CSV error:', error);
      message.error('Không thể xuất file CSV');
    }
  };

  const handleImportSuccess = () => {
    setImportModalVisible(false);
    loadEmployees(); // Reload employee list
  };

  const loadEmployees = async () => {
    try {
      setLoading(true);
      const response = await employeeAPI.getAll();
      setEmployees(response.data.data);
    } catch (error) {
      message.error("Không thể tải danh sách nhân viên");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingEmployee(null);
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingEmployee(record);
    setModalVisible(true);
  };

  const handleDelete = (record) => {
    console.log("Deleting employee:", record);

    // Test với confirm đơn giản
    if (
      window.confirm(`Bạn có chắc chắn muốn xóa nhân viên ${record.full_name}?`)
    ) {
      console.log("User confirmed delete");

      employeeAPI
        .delete(record.id_real)
        .then(() => {
          message.success("Xóa nhân viên thành công");
          loadEmployees();
        })
        .catch((error) => {
          console.error("Delete error:", error);
          message.error("Không thể xóa nhân viên");
        });
    }
  };

  const handleModalOk = () => {
    setModalVisible(false);
    loadEmployees();
  };
  // Thêm handler cho lịch làm việc
  const handleSchedule = (record) => {
    setScheduleEmployee(record);
    setScheduleModalVisible(true);
  };

  const handleScheduleModalOk = () => {
    setScheduleModalVisible(false);
    setScheduleEmployee(null);
    // Có thể reload employees nếu cần
    loadEmployees();
  };

  const filteredEmployees = employees.filter(
    (emp) =>
      emp.full_name.toLowerCase().includes(searchText.toLowerCase()) ||
      emp.id_real.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns = [
    {
      title: "Mã NV",
      dataIndex: "id_real",
      key: "id_real",
      width: 100,
    },
    {
      title: "Họ và tên",
      dataIndex: "full_name",
      key: "full_name",
    },
    {
      title: "Chức vụ",
      dataIndex: "role",
      key: "role",
      render: (role) => (
        <Tag color={role === "employee" ? "blue" : "green"}>
          {role === "employee" ? "Nhân viên" : "Giảng viên"}
        </Tag>
      ),
    },
    {
      title: "Lương/giờ",
      dataIndex: "hourly_rate",
      key: "hourly_rate",
      render: (rate) => `${Number(rate).toLocaleString()} VNĐ`,
    },
    {
      title: "Lịch làm việc",
      key: "schedule_info",
      render: (_, record) => {
        const schedule = record.work_schedule;
        if (!schedule) return "Chưa thiết lập";
        
        const activeDays = Object.entries(schedule)
          .filter(([day, config]) => config.active)
          .map(([day]) => day);
        
        return `${activeDays.length} ngày/tuần`;
      }
    },
    {
      title: "Hành động",
      key: "actions",
      width: 150,
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
          <Button
            size="small"
            icon={<CalendarOutlined />}
            onClick={() => handleSchedule(record)}
          >
            Lịch
          </Button>
          <Button
            danger
            size="small"
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            Xóa
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Input
            placeholder="Tìm kiếm theo tên hoặc mã nhân viên..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ maxWidth: 400 }}
          />
        </Col>
        <Col xs={24} sm={8} md={6} lg={8}>
          <Space wrap>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExportCSV}
              disabled={employees.length === 0}
            >
              <span className="desktop-text">Xuất CSV</span>
              <span className="mobile-text">Xuất</span>
            </Button>
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
            >
              <span className="desktop-text">Import CSV</span>
              <span className="mobile-text">Import</span>
            </Button>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleCreate}
            >
              <span className="desktop-text">Thêm nhân viên</span>
              <span className="mobile-text">Thêm</span>
            </Button>
          </Space>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={filteredEmployees}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `Tổng ${total} nhân viên`,
        }}
        scroll={{ x: 800 }}
      />

      <EmployeeModal
        visible={modalVisible}
        employee={editingEmployee}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
      />
      
      <ImportModal
        visible={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        onSuccess={handleImportSuccess}
      />
      <WorkScheduleModal
        visible={scheduleModalVisible}
        employee={scheduleEmployee}
        onOk={handleScheduleModalOk}
        onCancel={() => setScheduleModalVisible(false)}
      />
    </Card>
  );
};

export default EmployeeList;
