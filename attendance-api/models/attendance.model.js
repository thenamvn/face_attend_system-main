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
    allowNull: false
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
  // Add unique constraint for person-day combination
  indexes: [
    {
      unique: true,
      fields: ['id_real', 'day']
    }
  ],
  timestamps: true, // Automatically add createdAt and updatedAt fields
  tableName: 'attendance' // Specify the table name if different from the model name
});

module.exports = Attendance;