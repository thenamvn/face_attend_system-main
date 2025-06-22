const { DataTypes } = require('sequelize');
const db = require('../config/db.config');

const Holiday = db.define('holidays', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  start_date: {
    type: DataTypes.DATEONLY,
    allowNull: false
  },
  end_date: {
    type: DataTypes.DATEONLY,
    allowNull: true
  },
  type: {
    type: DataTypes.ENUM('single_day', 'period'),
    defaultValue: 'single_day'
  },
  category: {
    type: DataTypes.ENUM('national', 'company', 'religious', 'summer_break', 'winter_break', 'sick_leave', 'annual_leave', 'maternity_leave'),
    defaultValue: 'national'
  },
  // Thêm: Phân loại theo lương
  leave_type: {
    type: DataTypes.ENUM('paid_holiday', 'unpaid_leave', 'overtime_holiday'),
    defaultValue: 'paid_holiday'
    // paid_holiday: Nghỉ lễ có lương (Tết, quốc khánh...)
    // unpaid_leave: Nghỉ không lương (nghỉ phép không lương, nghỉ việc riêng...)
    // overtime_holiday: Nghỉ lễ làm thêm có hệ số (làm việc ngày lễ)
  },
  // Xử lý lương
  salary_policy: {
    type: DataTypes.ENUM('full_pay', 'no_pay', 'multiplier_pay', 'partial_pay'),
    defaultValue: 'full_pay'
    // full_pay: Trả đủ lương (nghỉ lễ, nghỉ phép có lương)
    // no_pay: Không trả lương (nghỉ không phép, nghỉ việc riêng)
    // multiplier_pay: Trả lương theo hệ số (làm việc ngày lễ)
    // partial_pay: Trả lương một phần (nghỉ ốm có giấy...)
  },
  salary_multiplier: {
    type: DataTypes.DECIMAL(3, 2),
    defaultValue: 1.0,
    allowNull: false,
    validate: {
      min: 0.0,
      max: 9.99
    }
    // 0.0 = không lương
    // 1.0 = lương bình thường  
    // 2.0 = gấp đôi lương (ngày lễ)
    // 0.5 = một nửa lương
  },
  // Cho phép làm việc trong ngày nghỉ không?
  allow_work: {
    type: DataTypes.BOOLEAN,
    defaultValue: false
    // true: Cho phép làm việc (ngày lễ quốc gia)
    // false: Không cho phép (nghỉ phép, nghỉ ốm...)
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  is_active: {
    type: DataTypes.BOOLEAN,
    defaultValue: true
  },
  applies_to: {
    type: DataTypes.ENUM('all', 'employee_only', 'lecturer_only'),
    defaultValue: 'all'
  }
}, {
  timestamps: true,
  tableName: 'holidays',
  indexes: [
    {
      fields: ['start_date', 'end_date']
    },
    {
      fields: ['type', 'leave_type']
    },
    {
      fields: ['salary_policy']
    }
  ]
});

module.exports = Holiday;