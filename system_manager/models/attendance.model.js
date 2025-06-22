const { DataTypes } = require('sequelize');
const db = require('../config/db.config');

const Attendance = db.define('attendance', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  name: {
    type: DataTypes.STRING,
    allowNull: false
  },
  id_real: {
    type: DataTypes.STRING,
    allowNull: false,
    references: {
      model: 'employees',
      key: 'id_real'
    },
    onDelete: 'CASCADE',
    onUpdate: 'CASCADE'
  },
  day: {
    type: DataTypes.DATEONLY,
    allowNull: false
  },
  first_time: {
    type: DataTypes.TIME,
    allowNull: false
  },
  last_time: {
    type: DataTypes.TIME,
    allowNull: false
  }
}, {
  indexes: [
    {
      unique: true,
      fields: ['id_real', 'day']
    }
  ],
  timestamps: true,
  tableName: 'attendance'
});

module.exports = Attendance;