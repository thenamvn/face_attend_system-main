// src/components/Employees/EmployeeModal.js
import React, { useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  TimePicker,
  message
} from 'antd';
import { employeeAPI } from '../../services/api';
import moment from 'moment';

const { Option } = Select;

const EmployeeModal = ({ visible, employee, onOk, onCancel }) => {
  const [form] = Form.useForm();
  const isEditing = !!employee;

  useEffect(() => {
    if (visible) {
      if (employee) {
        form.setFieldsValue({
          ...employee,
          start_time: employee.start_time ? moment(employee.start_time, 'HH:mm:ss') : moment('08:00:00', 'HH:mm:ss')
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          start_time: moment('08:00:00', 'HH:mm:ss')
        });
      }
    }
  }, [visible, employee, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      const submitData = {
        ...values,
        // start_time: values.start_time.format('HH:mm:ss')
      };

      if (isEditing) {
        await employeeAPI.update(employee.id_real, submitData);
        message.success('Cập nhật nhân viên thành công');
      } else {
        await employeeAPI.create(submitData);
        message.success('Thêm nhân viên thành công');
      }
      
      onOk();
    } catch (error) {
      if (error.response?.data?.message) {
        message.error(error.response.data.message);
      } else {
        message.error('Có lỗi xảy ra');
      }
    }
  };

  return (
    <Modal
      title={isEditing ? 'Sửa thông tin nhân viên' : 'Thêm nhân viên mới'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={600}
      okText={isEditing ? 'Cập nhật' : 'Thêm'}
      cancelText="Hủy"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          role: 'employee',
          hourly_rate: 50000
          // start_time: moment('08:00:00', 'HH:mm:ss')
        }}
      >
        <Form.Item
          name="id_real"
          label="Mã nhân viên"
          rules={[
            { required: true, message: 'Vui lòng nhập mã nhân viên' },
            { pattern: /^[A-Z0-9]+$/, message: 'Mã nhân viên chỉ chứa chữ in hoa và số' }
          ]}
        >
          <Input placeholder="VD: EMP001" disabled={isEditing} />
        </Form.Item>

        <Form.Item
          name="full_name"
          label="Họ và tên"
          rules={[{ required: true, message: 'Vui lòng nhập họ và tên' }]}
        >
          <Input placeholder="Nguyễn Văn A" />
        </Form.Item>

        <Form.Item
          name="role"
          label="Chức vụ"
          rules={[{ required: true, message: 'Vui lòng chọn chức vụ' }]}
        >
          <Select placeholder="Chọn chức vụ">
            <Option value="employee">Nhân viên</Option>
            <Option value="lecturer">Giảng viên</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="hourly_rate"
          label="Lương theo giờ (VNĐ)"
          rules={[
            { required: true, message: 'Vui lòng nhập lương theo giờ' },
            { type: 'number', min: 1000, message: 'Lương phải lớn hơn 1,000 VNĐ' }
          ]}
        >
          <InputNumber
            style={{ width: '100%' }}
            placeholder="50000"
            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={value => value.replace(/\$\s?|(,*)/g, '')}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default EmployeeModal;