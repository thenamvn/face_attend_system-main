const { DataTypes } = require('sequelize');
const db = require('../config/db.config');

const Employee = db.define('employees', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  id_real: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true
  },
  full_name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  role: {
    type: DataTypes.ENUM('employee', 'lecturer'),
    allowNull: false
  },
  hourly_rate: {
    type: DataTypes.DECIMAL(10, 2),
    allowNull: false
  },
  work_schedule: {
    type: DataTypes.JSON,
    defaultValue: {
      monday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
      tuesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
      wednesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
      thursday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
      friday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
      saturday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null },
      sunday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null }
    }
  },
  standard_work_hours: {
    type: DataTypes.DECIMAL(4, 2),
    defaultValue: 8.0
  },
  schedule_type: {
    type: DataTypes.ENUM('fixed', 'flexible', 'shift'),
    defaultValue: 'fixed'
    // fixed: Giờ cố định
    // flexible: Linh hoạt (giảng viên)
    // shift: Ca làm việc
  }
  // start_time: {
  //   type: DataTypes.TIME,
  //   allowNull: true
  // }
}, {
  timestamps: true,
  tableName: 'employees'
});

const SalaryReport = db.define('salary_reports', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  id_real: {
    type: DataTypes.STRING,
    allowNull: false,
    references: {
      model: Employee,
      key: 'id_real'
    },
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  },
  month: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  year: {
    type: DataTypes.INTEGER,
    allowNull: false
  },
  total_hours: {
    type: DataTypes.DECIMAL(8, 2),
    defaultValue: 0
  },
  total_salary: {
    type: DataTypes.DECIMAL(12, 2),
    defaultValue: 0
  },
  total_days_worked: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  late_days: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  total_late_minutes: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
    // Thêm các field mới cho holiday
  holiday_hours: {
    type: DataTypes.DECIMAL(8, 2),
    defaultValue: 0
  },
  holiday_bonus: {
    type: DataTypes.DECIMAL(12, 2),
    defaultValue: 0
  },
  base_salary: {
    type: DataTypes.DECIMAL(12, 2),
    defaultValue: 0
  }
}, {
  timestamps: true,
  tableName: 'salary_reports',
  indexes: [
    {
      unique: true,
      fields: ['id_real', 'month', 'year']
    }
  ]
});

// Define associations
Employee.hasMany(SalaryReport, { foreignKey: 'id_real', sourceKey: 'id_real', onDelete: 'CASCADE', onUpdate: 'CASCADE' });
SalaryReport.belongsTo(Employee, { foreignKey: 'id_real', targetKey: 'id_real' });

module.exports = {
  Employee,
  SalaryReport
};