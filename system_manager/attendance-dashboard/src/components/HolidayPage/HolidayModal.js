import React, { useEffect, useState } from 'react';
import {
  Modal,
  Form,
  Input,
  DatePicker,
  InputNumber,
  Switch,
  Select,
  Radio,
  message,
  Row,
  Col,
  Alert,
  Card,
  Divider
} from 'antd';
import { holidayAPI } from '../../services/api';
import moment from 'moment';

const { TextArea } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;

const HolidayModal = ({ visible, holiday, onOk, onCancel }) => {
  const [form] = Form.useForm();
  const [holidayType, setHolidayType] = useState('single_day');
  const [leaveType, setLeaveType] = useState('paid_holiday');
  const [salaryPolicy, setSalaryPolicy] = useState('full_pay');
  const isEditing = !!holiday;

  useEffect(() => {
    if (visible) {
      if (holiday) {
        const formData = {
          ...holiday,
          start_date: moment(holiday.start_date),
          end_date: holiday.end_date ? moment(holiday.end_date) : null,
          date_range: holiday.type === 'period' ? [
            moment(holiday.start_date),
            moment(holiday.end_date)
          ] : null
        };
        
        setHolidayType(holiday.type || 'single_day');
        setLeaveType(holiday.leave_type || 'paid_holiday');
        setSalaryPolicy(holiday.salary_policy || 'full_pay');
        form.setFieldsValue(formData);
      } else {
        form.resetFields();
        form.setFieldsValue({
          salary_multiplier: 1.0,
          is_active: true,
          type: 'single_day',
          category: 'national',
          leave_type: 'paid_holiday',
          salary_policy: 'full_pay',
          allow_work: false,
          applies_to: 'all'
        });
        setHolidayType('single_day');
        setLeaveType('paid_holiday');
        setSalaryPolicy('full_pay');
      }
    }
  }, [visible, holiday, form]);

  const handleTypeChange = (e) => {
    setHolidayType(e.target.value);
    if (e.target.value === 'single_day') {
      form.setFieldsValue({ end_date: null, date_range: null });
    } else {
      form.setFieldsValue({ start_date: null });
    }
  };

  const handleLeaveTypeChange = (value) => {
    setLeaveType(value);
    
    // Auto-set default values based on leave type
    if (value === 'paid_holiday') {
      form.setFieldsValue({
        salary_policy: 'full_pay',
        salary_multiplier: 1.0,
        allow_work: true
      });
      setSalaryPolicy('full_pay');
    } else if (value === 'unpaid_leave') {
      form.setFieldsValue({
        salary_policy: 'no_pay',
        salary_multiplier: 0.0,
        allow_work: false
      });
      setSalaryPolicy('no_pay');
    } else if (value === 'overtime_holiday') {
      form.setFieldsValue({
        salary_policy: 'multiplier_pay',
        salary_multiplier: 2.0,
        allow_work: true
      });
      setSalaryPolicy('multiplier_pay');
    }
  };

  const handleSalaryPolicyChange = (value) => {
    setSalaryPolicy(value);
    
    // Auto-set multiplier based on policy
    if (value === 'no_pay') {
      form.setFieldsValue({ salary_multiplier: 0.0 });
    } else if (value === 'full_pay') {
      form.setFieldsValue({ salary_multiplier: 1.0 });
    } else if (value === 'multiplier_pay') {
      form.setFieldsValue({ salary_multiplier: 2.0 });
    } else if (value === 'partial_pay') {
      form.setFieldsValue({ salary_multiplier: 0.5 });
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      let submitData = { ...values };

      if (values.type === 'single_day') {
        submitData = {
          ...submitData,
          start_date: values.start_date.format('YYYY-MM-DD'),
          end_date: null
        };
        delete submitData.date_range;
      } else {
        const [startDate, endDate] = values.date_range;
        submitData = {
          ...submitData,
          start_date: startDate.format('YYYY-MM-DD'),
          end_date: endDate.format('YYYY-MM-DD')
        };
        delete submitData.date_range;
      }

      if (isEditing) {
        await holidayAPI.update(holiday.id, submitData);
        message.success('Cập nhật ngày nghỉ thành công');
      } else {
        await holidayAPI.create(submitData);
        message.success('Thêm ngày nghỉ thành công');
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

  const calculatePeriodDays = () => {
    const dateRange = form.getFieldValue('date_range');
    if (dateRange && dateRange.length === 2) {
      const [start, end] = dateRange;
      return end.diff(start, 'days') + 1;
    }
    return 0;
  };

  const getLeaveTypeDescription = () => {
    const descriptions = {
      paid_holiday: "Nghỉ lễ có lương - nhân viên được nghỉ và nhận đủ lương",
      unpaid_leave: "Nghỉ không lương - nhân viên nghỉ không được trả lương",
      overtime_holiday: "Ngày lễ làm thêm - nếu làm việc sẽ có hệ số lương cao"
    };
    return descriptions[leaveType] || "";
  };

  const getSalaryPolicyDescription = () => {
    const descriptions = {
      full_pay: "Trả đủ lương (100%)",
      no_pay: "Không trả lương (0%)",
      multiplier_pay: "Trả lương theo hệ số (thường > 100%)",
      partial_pay: "Trả lương một phần (< 100%)"
    };
    return descriptions[salaryPolicy] || "";
  };

  return (
    <Modal
      title={isEditing ? 'Sửa thông tin ngày nghỉ' : 'Thêm ngày nghỉ mới'}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={800}
      okText={isEditing ? 'Cập nhật' : 'Thêm'}
      cancelText="Hủy"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          salary_multiplier: 1.0,
          is_active: true,
          type: 'single_day',
          category: 'national',
          leave_type: 'paid_holiday',
          salary_policy: 'full_pay',
          allow_work: false,
          applies_to: 'all'
        }}
      >
        {/* Basic Info */}
        <Card title="Thông tin cơ bản" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="name"
                label="Tên ngày nghỉ"
                rules={[
                  { required: true, message: 'Vui lòng nhập tên ngày nghỉ' },
                  { max: 100, message: 'Tên ngày nghỉ không được quá 100 ký tự' }
                ]}
              >
                <Input placeholder="VD: Tết Nguyên đán, Nghỉ phép cá nhân..." />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="type"
                label="Loại thời gian"
                rules={[{ required: true }]}
              >
                <Radio.Group onChange={handleTypeChange}>
                  <Radio value="single_day">Ngày đơn lẻ</Radio>
                  <Radio value="period">Kỳ nghỉ dài</Radio>
                </Radio.Group>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="category"
                label="Phân loại"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="national">Ngày lễ quốc gia</Option>
                  <Option value="company">Nghỉ công ty</Option>
                  <Option value="religious">Ngày lễ tôn giáo</Option>
                  <Option value="summer_break">Nghỉ hè</Option>
                  <Option value="winter_break">Nghỉ đông</Option>
                  <Option value="sick_leave">Nghỉ ốm</Option>
                  <Option value="annual_leave">Nghỉ phép năm</Option>
                  <Option value="maternity_leave">Nghỉ thai sản</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          {/* Date Selection */}
          {holidayType === 'single_day' ? (
            <Form.Item
              name="start_date"
              label="Ngày nghỉ"
              rules={[{ required: true, message: 'Vui lòng chọn ngày' }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                format="DD/MM/YYYY"
                placeholder="Chọn ngày"
              />
            </Form.Item>
          ) : (
            <Form.Item
              name="date_range"
              label="Kỳ nghỉ"
              rules={[{ required: true, message: 'Vui lòng chọn khoảng thời gian nghỉ' }]}
            >
              <RangePicker
                style={{ width: '100%' }}
                format="DD/MM/YYYY"
                placeholder={['Ngày bắt đầu', 'Ngày kết thúc']}
              />
            </Form.Item>
          )}

          {holidayType === 'period' && (
            <Alert
              message={`Kỳ nghỉ dài: ${calculatePeriodDays()} ngày`}
              type="info"
              style={{ marginBottom: 16 }}
            />
          )}
        </Card>

        {/* Salary Policy */}
        <Card title="Chính sách lương" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="leave_type"
                label="Loại nghỉ"
                rules={[{ required: true }]}
                help={getLeaveTypeDescription()}
              >
                <Select onChange={handleLeaveTypeChange}>
                  <Option value="paid_holiday">Nghỉ lễ có lương</Option>
                  <Option value="unpaid_leave">Nghỉ không lương</Option>
                  <Option value="overtime_holiday">Ngày lễ làm thêm</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="salary_policy"
                label="Chính sách trả lương"
                rules={[{ required: true }]}
                help={getSalaryPolicyDescription()}
              >
                <Select onChange={handleSalaryPolicyChange}>
                  <Option value="full_pay">Trả đủ lương</Option>
                  <Option value="no_pay">Không trả lương</Option>
                  <Option value="multiplier_pay">Trả theo hệ số</Option>
                  <Option value="partial_pay">Trả lương một phần</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="salary_multiplier"
                label="Hệ số lương"
                rules={[
                  { required: true, message: 'Vui lòng nhập hệ số lương' },
                  { type: 'number', min: 0.0, max: 9.99, message: 'Hệ số lương từ 0.0 đến 9.99' }
                ]}
                help={
                  salaryPolicy === 'no_pay' ? "0.0 = Không lương" :
                  salaryPolicy === 'full_pay' ? "1.0 = Lương bình thường" :
                  salaryPolicy === 'multiplier_pay' ? "2.0+ = Gấp đôi lương" :
                  "0.5 = Một nửa lương"
                }
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0.0}
                  max={9.99}
                  step={0.1}
                  placeholder="1.0"
                  formatter={value => `${value}x`}
                  parser={value => value.replace('x', '')}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="allow_work"
                label="Cho phép làm việc"
                valuePropName="checked"
                help="Nhân viên có thể làm việc trong ngày này không?"
              >
                <Switch 
                  checkedChildren="Có" 
                  unCheckedChildren="Không"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="applies_to"
                label="Áp dụng cho"
                rules={[{ required: true }]}
              >
                <Select>
                  <Option value="all">Tất cả</Option>
                  <Option value="employee_only">Chỉ nhân viên</Option>
                  <Option value="lecturer_only">Chỉ giảng viên</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Additional Settings */}
        <Card title="Cài đặt khác" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="Trạng thái"
                valuePropName="checked"
              >
                <Switch checkedChildren="Kích hoạt" unCheckedChildren="Vô hiệu hóa" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="Mô tả"
            rules={[{ max: 500, message: 'Mô tả không được quá 500 ký tự' }]}
          >
            <TextArea
              rows={3}
              placeholder="Mô tả chi tiết về ngày nghỉ và chính sách áp dụng..."
            />
          </Form.Item>
        </Card>

        {/* Help Info */}
        <Alert
          message="Hướng dẫn sử dụng"
          description={
            <div>
              <strong>Các loại nghỉ phổ biến:</strong>
              <ul style={{ marginTop: 8, paddingLeft: 16 }}>
                <li><strong>Nghỉ lễ có lương:</strong> Tết, Quốc khánh - nghỉ nhưng vẫn có lương</li>
                <li><strong>Nghỉ không lương:</strong> Nghỉ phép cá nhân, nghỉ việc riêng</li>
                <li><strong>Ngày lễ làm thêm:</strong> Làm việc ngày lễ được hệ số lương cao (x2, x3)</li>
                <li><strong>Nghỉ ốm:</strong> Có giấy bác sĩ được trả 50-100% lương</li>
              </ul>
            </div>
          }
          type="info"
          showIcon
        />
      </Form>
    </Modal>
  );
};

export default HolidayModal;