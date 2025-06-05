const Attendance = require('../models/attendance.model');
const { Op } = require('sequelize');

// Mark attendance for a person
exports.markAttendance = async (req, res) => {
  try {
    // Get request body
    const { id_real, name, time } = req.body;
    
    // Validate required fields
    if (!id_real || !name || !time) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: id_real, name, time'
      });
    }
    
    // Parse the time string to a JavaScript Date object
    const attendanceTime = new Date(time);
    if (isNaN(attendanceTime.getTime())) {
      return res.status(400).json({
        success: false,
        message: 'Invalid time format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)'
      });
    }
    
    // Extract only the date part (YYYY-MM-DD)
    const today = attendanceTime.toISOString().split('T')[0];
    
    // Extract only the time part (HH:MM:SS)
    const timeString = attendanceTime.toTimeString().split(' ')[0];
    
    // Check if there's already an attendance record for this person on this day
    const existingRecord = await Attendance.findOne({
      where: {
        id_real,
        day: today
      }
    });
    
    if (!existingRecord) {
      // First attendance of the day - create new record
      const newAttendance = await Attendance.create({
        name,
        id_real,
        day: today,
        first_time: timeString,
        last_time: timeString
      });
      
      return res.status(201).json({
        success: true,
        message: 'First attendance recorded',
        data: newAttendance
      });
    } else {
      // Update last_time for existing record
      await existingRecord.update({
        last_time: timeString
      });
      
      return res.status(200).json({
        success: true,
        message: 'Attendance updated',
        data: {
          id: existingRecord.id,
          name: existingRecord.name,
          id_real: existingRecord.id_real,
          day: existingRecord.day,
          first_time: existingRecord.first_time,
          last_time: timeString
        }
      });
    }
  } catch (error) {
    console.error('Error marking attendance:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to record attendance',
      error: error.message
    });
  }
};

// Get attendance records for a specific day
exports.getAttendanceByDay = async (req, res) => {
  try {
    const { date } = req.params;
    
    const records = await Attendance.findAll({
      where: { day: date }
    });
    
    return res.status(200).json({
      success: true,
      count: records.length,
      data: records
    });
  } catch (error) {
    console.error('Error getting attendance records:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get attendance records',
      error: error.message
    });
  }
};

// Get attendance records for a specific person
exports.getAttendanceByPerson = async (req, res) => {
  try {
    const { id_real } = req.params;
    
    const records = await Attendance.findAll({
      where: { id_real },
      order: [['day', 'DESC']]
    });
    
    return res.status(200).json({
      success: true,
      count: records.length,
      data: records
    });
  } catch (error) {
    console.error('Error getting attendance records:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get attendance records',
      error: error.message
    });
  }
};

// Get all attendance records
exports.getAllAttendance = async (req, res) => {
  try {
    const records = await Attendance.findAll({
      order: [['day', 'DESC'], ['first_time', 'ASC']]
    });
    
    return res.status(200).json({
      success: true,
      count: records.length,
      data: records
    });
  } catch (error) {
    console.error('Error getting all attendance records:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get attendance records',
      error: error.message
    });
  }
};