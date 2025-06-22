// src/services/api.js
import axios from 'axios';
import { message } from 'antd';
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:9999/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Employee APIs
export const employeeAPI = {
  getAll: () => api.get('/employees'),
  create: (data) => api.post('/employees', data),
  update: (id, data) => api.put(`/employees/${id}`, data),
  delete: (id) => api.delete(`/employees/${id}`),
  getWorkSchedule: (id_real) => api.get(`/employees/${id_real}/schedule`),
  updateWorkSchedule: (id_real, data) => api.put(`/employees/${id_real}/schedule`, data),
  exportCSV: () => api.get('/employees/export/csv', {
    responseType: 'text'
  }),
  downloadTemplate: () => api.get('/employees/template/csv', {
    responseType: 'blob'
  }),
  importCSV: (file) => {
    const formData = new FormData();
    formData.append('csvFile', file);
    return api.post('/employees/import/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
};

// Attendance APIs
export const attendanceAPI = {
  getAll: () => api.get('/attendance'),
  getByDate: (date) => api.get(`/attendance/day/${date}`),
  getByPerson: (id) => api.get(`/attendance/person/${id}`),
  create: (data) => api.post('/attendance', data),
};

// Report APIs
export const reportAPI = {
  getDailyReport: (date) => api.get(`/reports/daily/${date}`),
  getMonthlyReport: (year, month) => api.get(`/reports/monthly/${year}/${month}`),
  exportMonthlyCSV: (year, month) => api.get(`/reports/monthly/${year}/${month}/csv`, {
    responseType: 'text',
  }),
};

// Face APIs
export const faceAPI = {
  getAll: () => api.get('/faces'),
  create: (data) => api.post('/faces', data),
  delete: (id) => api.delete(`/faces/${id}`),
};

// Holiday APIs
export const holidayAPI = {
  getAll: () => api.get('/holidays'),
  create: (data) => api.post('/holidays', data),
  update: (id, data) => api.put(`/holidays/${id}`, data),
  delete: (id) => api.delete(`/holidays/${id}`),
  getByYear: (year) => api.get(`/holidays/year/${year}`),
  
  // New APIs for period support
  isHoliday: (date, employeeRole) => api.get(`/holidays/check/${date}?employee_role=${employeeRole}`),
  getHolidaysInRange: (startDate, endDate, employeeRole) => 
    api.get(`/holidays/range?start_date=${startDate}&end_date=${endDate}&employee_role=${employeeRole}`)
};

// Add auth interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor - handle auth errors
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.log('API Error:', error.response);
    
    if (error.response?.status === 401) {
      const errorData = error.response.data;
      
      // Show appropriate message based on error code
      if (errorData?.code === 'TOKEN_EXPIRED') {
        message.error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
      } else if (errorData?.code === 'INVALID_TOKEN') {
        message.error('Token không hợp lệ. Vui lòng đăng nhập lại.');
      } else {
        message.error('Vui lòng đăng nhập để tiếp tục.');
      }
      
      // Clear stored auth data
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      
      // Redirect to login page
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500); // Delay để user đọc được message
      
    } else if (error.response?.status === 403) {
      message.error('Bạn không có quyền truy cập tính năng này.');
    } else if (error.response?.status >= 500) {
      message.error('Lỗi server. Vui lòng thử lại sau.');
    }
    
    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  getProfile: () => api.get('/auth/profile'),
};

export default api;