import React, { useState, useEffect } from 'react';
import { Modal, Form, TimePicker, Switch, InputNumber, Select, message, Row, Col, Card, Spin } from 'antd';
import { employeeAPI } from '../../services/api';
import moment from 'moment';

const { Option } = Select;

const WorkScheduleModal = ({ visible, employee, onCancel, onOk }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const dayNames = {
    monday: 'Thứ 2',
    tuesday: 'Thứ 3', 
    wednesday: 'Thứ 4',
    thursday: 'Thứ 5',
    friday: 'Thứ 6',
    saturday: 'Thứ 7',
    sunday: 'Chủ nhật'
  };

  useEffect(() => {
    if (visible && employee) {
      loadWorkSchedule();
    }
  }, [visible, employee]);

  const loadWorkSchedule = async () => {
    try {
      setLoading(true);
      const response = await employeeAPI.getWorkSchedule(employee.id_real);
      const data = response.data.data;
      
      // Format schedule data for form
      const formData = {
        schedule_type: data.schedule_type || 'fixed',
        standard_work_hours: data.standard_work_hours || 8.0
      };
      
      // Convert time strings to moment objects
      Object.keys(dayNames).forEach(day => {
        const daySchedule = data.work_schedule?.[day] || {
          active: day === 'saturday' || day === 'sunday' ? false : true,
          start: '08:00:00',
          end: '17:00:00',
          lunch_start: '12:00:00',
          lunch_end: '13:00:00'
        };
        
        formData[`${day}_active`] = daySchedule.active;
        if (daySchedule.active && daySchedule.start) {
          formData[`${day}_start`] = moment(daySchedule.start, 'HH:mm:ss');
          formData[`${day}_end`] = moment(daySchedule.end, 'HH:mm:ss');
          formData[`${day}_lunch_start`] = moment(daySchedule.lunch_start, 'HH:mm:ss');
          formData[`${day}_lunch_end`] = moment(daySchedule.lunch_end, 'HH:mm:ss');
        }
      });
      
      form.setFieldsValue(formData);
    } catch (error) {
      message.error('Không thể tải lịch làm việc');
      console.error('Load schedule error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      // Build work schedule object
      const work_schedule = {};
      Object.keys(dayNames).forEach(day => {
        work_schedule[day] = {
          active: values[`${day}_active`] || false,
          start: values[`${day}_active`] && values[`${day}_start`] ? values[`${day}_start`].format('HH:mm:ss') : null,
          end: values[`${day}_active`] && values[`${day}_end`] ? values[`${day}_end`].format('HH:mm:ss') : null,
          lunch_start: values[`${day}_active`] && values[`${day}_lunch_start`] ? values[`${day}_lunch_start`].format('HH:mm:ss') : null,
          lunch_end: values[`${day}_active`] && values[`${day}_lunch_end`] ? values[`${day}_lunch_end`].format('HH:mm:ss') : null
        };
      });

      const submitData = {
        work_schedule,
        standard_work_hours: values.standard_work_hours,
        schedule_type: values.schedule_type
      };

      await employeeAPI.updateWorkSchedule(employee.id_real, submitData);
      message.success('Cập nhật lịch làm việc thành công');
      onOk();
      
    } catch (error) {
      if (error.response?.data?.message) {
        message.error(error.response.data.message);
      } else {
        message.error('Có lỗi xảy ra khi cập nhật lịch làm việc');
      }
    }
  };

  const handleQuickSet = (type) => {
    const values = {};
    
    if (type === 'weekdays') {
      // Set Monday to Friday active, weekend inactive
      Object.keys(dayNames).forEach(day => {
        const isWeekend = day === 'saturday' || day === 'sunday';
        values[`${day}_active`] = !isWeekend;
        if (!isWeekend) {
          values[`${day}_start`] = moment('08:00:00', 'HH:mm:ss');
          values[`${day}_end`] = moment('17:00:00', 'HH:mm:ss');
          values[`${day}_lunch_start`] = moment('12:00:00', 'HH:mm:ss');
          values[`${day}_lunch_end`] = moment('13:00:00', 'HH:mm:ss');
        }
      });
    } else if (type === 'alldays') {
      // Set all days active
      Object.keys(dayNames).forEach(day => {
        values[`${day}_active`] = true;
        values[`${day}_start`] = moment('08:00:00', 'HH:mm:ss');
        values[`${day}_end`] = moment('17:00:00', 'HH:mm:ss');
        values[`${day}_lunch_start`] = moment('12:00:00', 'HH:mm:ss');
        values[`${day}_lunch_end`] = moment('13:00:00', 'HH:mm:ss');
      });
    }
    
    form.setFieldsValue(values);
  };

  return (
    <Modal
      title={`Lịch làm việc - ${employee?.full_name || 'Nhân viên'}`}
      open={visible}
      onOk={handleSubmit}
      onCancel={onCancel}
      width={900}
      okText="Cập nhật"
      cancelText="Hủy"
      style={{ top: 20 }}
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="schedule_type"
                label="Loại lịch làm việc"
                rules={[{ required: true, message: 'Vui lòng chọn loại lịch' }]}
              >
                <Select placeholder="Chọn loại lịch">
                  <Option value="fixed">Cố định</Option>
                  <Option value="flexible">Linh hoạt</Option>
                  <Option value="shift">Ca làm việc</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="standard_work_hours"
                label="Số giờ tiêu chuẩn/ngày"
                rules={[{ required: true, message: 'Vui lòng nhập số giờ' }]}
              >
                <InputNumber
                  min={1}
                  max={12}
                  step={0.5}
                  style={{ width: '100%' }}
                  placeholder="8"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="Thiết lập nhanh">
                <Select placeholder="Chọn mẫu" onChange={handleQuickSet}>
                  <Option value="weekdays">Thứ 2 - 6</Option>
                  <Option value="alldays">Tất cả các ngày</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {Object.keys(dayNames).map(day => (
              <Card key={day} size="small" style={{ marginBottom: 8 }}>
                <Row gutter={8} align="middle">
                  <Col span={3}>
                    <Form.Item
                      name={`${day}_active`}
                      valuePropName="checked"
                      style={{ marginBottom: 0 }}
                    >
                      <Switch size="small" />
                    </Form.Item>
                    <div style={{ fontSize: '12px', fontWeight: 'bold' }}>
                      {dayNames[day]}
                    </div>
                  </Col>
                  
                  <Form.Item noStyle shouldUpdate={(prev, curr) => prev[`${day}_active`] !== curr[`${day}_active`]}>
                    {({ getFieldValue }) => {
                      const isActive = getFieldValue(`${day}_active`);
                      return isActive ? (
                        <>
                          <Col span={4}>
                            <Form.Item
                              name={`${day}_start`}
                              label="Bắt đầu"
                              rules={[{ required: true, message: 'Chọn giờ' }]}
                              style={{ marginBottom: 0 }}
                            >
                              <TimePicker 
                                format="HH:mm" 
                                style={{ width: '100%' }}
                                size="small"
                              />
                            </Form.Item>
                          </Col>
                          <Col span={4}>
                            <Form.Item
                              name={`${day}_end`}
                              label="Kết thúc"
                              rules={[{ required: true, message: 'Chọn giờ' }]}
                              style={{ marginBottom: 0 }}
                            >
                              <TimePicker 
                                format="HH:mm" 
                                style={{ width: '100%' }}
                                size="small"
                              />
                            </Form.Item>
                          </Col>
                          <Col span={1}>
                            <div style={{ textAlign: 'center', fontSize: '12px', color: '#999' }}>
                              Nghỉ trưa
                            </div>
                          </Col>
                          <Col span={4}>
                            <Form.Item
                              name={`${day}_lunch_start`}
                              label="Từ"
                              rules={[{ required: true, message: 'Chọn giờ' }]}
                              style={{ marginBottom: 0 }}
                            >
                              <TimePicker 
                                format="HH:mm" 
                                style={{ width: '100%' }}
                                size="small"
                              />
                            </Form.Item>
                          </Col>
                          <Col span={4}>
                            <Form.Item
                              name={`${day}_lunch_end`}
                              label="Đến"
                              rules={[{ required: true, message: 'Chọn giờ' }]}
                              style={{ marginBottom: 0 }}
                            >
                              <TimePicker 
                                format="HH:mm" 
                                style={{ width: '100%' }}
                                size="small"
                              />
                            </Form.Item>
                          </Col>
                        </>
                      ) : (
                        <Col span={21}>
                          <div style={{ 
                            color: '#999', 
                            fontStyle: 'italic',
                            padding: '8px 0',
                            textAlign: 'center'
                          }}>
                            Ngày nghỉ
                          </div>
                        </Col>
                      );
                    }}
                  </Form.Item>
                </Row>
              </Card>
            ))}
          </div>
        </Form>
      </Spin>
    </Modal>
  );
};

export default WorkScheduleModal;