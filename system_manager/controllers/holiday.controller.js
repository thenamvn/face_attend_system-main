const Holiday = require('../models/holiday.model');
const { Op } = require('sequelize');
const moment = require('moment');
// Helper function để tạo danh sách ngày từ start_date đến end_date
const generateDateRange = (startDate, endDate) => {
  const dates = [];
  const current = moment(startDate);
  const end = moment(endDate || startDate);
  
  while (current.isSameOrBefore(end)) {
    dates.push(current.format('YYYY-MM-DD'));
    current.add(1, 'day');
  }
  
  return dates;
};

// Get all holidays with expanded date ranges
exports.getAllHolidays = async (req, res) => {
  try {
    const holidays = await Holiday.findAll({
      order: [['start_date', 'ASC']]
    });

    // Expand periods into individual dates for frontend display
    const expandedHolidays = [];
    
    holidays.forEach(holiday => {
      if (holiday.type === 'period' && holiday.end_date) {
        const dates = generateDateRange(holiday.start_date, holiday.end_date);
        dates.forEach((date, index) => {
          expandedHolidays.push({
            ...holiday.toJSON(),
            id: `${holiday.id}_${index}`,
            date: date,
            is_period_part: true,
            period_day: index + 1,
            total_period_days: dates.length
          });
        });
      } else {
        expandedHolidays.push({
          ...holiday.toJSON(),
          date: holiday.start_date,
          is_period_part: false
        });
      }
    });

    return res.status(200).json({
      success: true,
      data: expandedHolidays
    });
  } catch (error) {
    console.error('Error getting holidays:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get holidays',
      error: error.message
    });
  }
};

// Create holiday
exports.createHoliday = async (req, res) => {
  try {
    const { 
      name, 
      start_date, 
      end_date, 
      type, 
      category,
      salary_multiplier, 
      description, 
      is_active,
      applies_to 
    } = req.body;

    // Validate period dates
    if (type === 'period') {
      if (!end_date) {
        return res.status(400).json({
          success: false,
          message: 'Kỳ nghỉ dài phải có ngày kết thúc'
        });
      }
      
      if (moment(end_date).isBefore(start_date)) {
        return res.status(400).json({
          success: false,
          message: 'Ngày kết thúc phải sau ngày bắt đầu'
        });
      }
    }

    // Check for overlapping holidays
    const overlapping = await Holiday.findAll({
      where: {
        [Op.or]: [
          // Check single day overlap
          {
            type: 'single_day',
            start_date: {
              [Op.between]: [start_date, end_date || start_date]
            }
          },
          // Check period overlap
          {
            type: 'period',
            [Op.and]: [
              { start_date: { [Op.lte]: end_date || start_date } },
              { end_date: { [Op.gte]: start_date } }
            ]
          }
        ]
      }
    });

    if (overlapping.length > 0) {
      return res.status(400).json({
        success: false,
        message: 'Ngày nghỉ này trùng với ngày nghỉ đã có',
        overlapping: overlapping.map(h => ({
          name: h.name,
          start_date: h.start_date,
          end_date: h.end_date
        }))
      });
    }

    const holiday = await Holiday.create({
      name,
      start_date,
      end_date: type === 'period' ? end_date : null,
      type: type || 'single_day',
      category: category || 'national',
      salary_multiplier: salary_multiplier || 2.0,
      description,
      is_active: is_active !== undefined ? is_active : true,
      applies_to: applies_to || 'all'
    });

    return res.status(201).json({
      success: true,
      message: 'Tạo ngày nghỉ thành công',
      data: holiday
    });
  } catch (error) {
    console.error('Error creating holiday:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to create holiday',
      error: error.message
    });
  }
};

// Update holiday
exports.updateHoliday = async (req, res) => {
  try {
    const { id } = req.params;
    const updateData = req.body;
    
    // Validate salary_multiplier if provided
    if (updateData.salary_multiplier !== undefined && 
        (updateData.salary_multiplier < 1.0 || updateData.salary_multiplier > 9.99)) {
      return res.status(400).json({
        success: false,
        message: 'Salary multiplier must be between 1.0 and 9.99'
      });
    }
    
    const holiday = await Holiday.findByPk(id);
    if (!holiday) {
      return res.status(404).json({
        success: false,
        message: 'Holiday not found'
      });
    }
    
    await holiday.update(updateData);
    
    return res.status(200).json({
      success: true,
      message: 'Holiday updated successfully',
      data: holiday
    });
  } catch (error) {
    console.error('Error updating holiday:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to update holiday',
      error: error.message
    });
  }
};

// Delete holiday
exports.deleteHoliday = async (req, res) => {
  try {
    const { id } = req.params;
    
    const holiday = await Holiday.findByPk(id);
    if (!holiday) {
      return res.status(404).json({
        success: false,
        message: 'Holiday not found'
      });
    }
    
    await holiday.destroy();
    
    return res.status(200).json({
      success: true,
      message: 'Holiday deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting holiday:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to delete holiday',
      error: error.message
    });
  }
};

// Check if a date is holiday
exports.isHoliday = async (req, res) => {
  try {
    const { date } = req.params;
    const { employee_role } = req.query; // 'employee' or 'lecturer'
    
    const holiday = await Holiday.findOne({
      where: {
        [Op.and]: [
          {
            [Op.or]: [
              // Single day holiday
              {
                type: 'single_day',
                start_date: date
              },
              // Period holiday containing this date
              {
                type: 'period',
                start_date: { [Op.lte]: date },
                end_date: { [Op.gte]: date }
              }
            ]
          },
          { is_active: true },
          {
            [Op.or]: [
              { applies_to: 'all' },
              { applies_to: `${employee_role}_only` }
            ]
          }
        ]
      }
    });

    return res.status(200).json({
      success: true,
      is_holiday: !!holiday,
      holiday_info: holiday || null
    });
  } catch (error) {
    console.error('Error checking holiday:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to check holiday',
      error: error.message
    });
  }
};

// Get holidays by year with period support
exports.getHolidaysByYear = async (req, res) => {
  try {
    const { year } = req.params;
    
    const startDate = `${year}-01-01`;
    const endDate = `${year}-12-31`;

    const holidays = await Holiday.findAll({
      where: {
        [Op.or]: [
          // Single day holidays trong năm
          {
            type: 'single_day',
            start_date: {
              [Op.between]: [startDate, endDate]
            }
          },
          // Period holidays overlap với năm
          {
            type: 'period',
            [Op.and]: [
              { start_date: { [Op.lte]: endDate } },
              {
                [Op.or]: [
                  { end_date: { [Op.gte]: startDate } },
                  { end_date: null }
                ]
              }
            ]
          }
        ]
      },
      order: [['start_date', 'ASC']]
    });

    return res.status(200).json({
      success: true,
      data: holidays
    });
  } catch (error) {
    console.error('Error getting holidays by year:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get holidays',
      error: error.message
    });
  }
};


// Get holidays in date range
exports.getHolidaysInRange = async (req, res) => {
  try {
    const { start_date, end_date } = req.query;
    const { employee_role } = req.query;
    
    const holidays = await Holiday.findAll({
      where: {
        [Op.and]: [
          {
            [Op.or]: [
              // Single day holidays in range
              {
                type: 'single_day',
                start_date: {
                  [Op.between]: [start_date, end_date]
                }
              },
              // Period holidays overlapping with range
              {
                type: 'period',
                [Op.and]: [
                  { start_date: { [Op.lte]: end_date } },
                  { end_date: { [Op.gte]: start_date } }
                ]
              }
            ]
          },
          { is_active: true },
          employee_role ? {
            [Op.or]: [
              { applies_to: 'all' },
              { applies_to: `${employee_role}_only` }
            ]
          } : {}
        ]
      },
      order: [['start_date', 'ASC']]
    });

    // Generate flat list of holiday dates
    const holidayDates = [];
    
    holidays.forEach(holiday => {
      if (holiday.type === 'period') {
        const dates = generateDateRange(
          Math.max(holiday.start_date, start_date),
          Math.min(holiday.end_date, end_date)
        );
        dates.forEach(date => {
          holidayDates.push({
            date,
            name: holiday.name,
            salary_multiplier: holiday.salary_multiplier,
            category: holiday.category,
            is_period: true,
            period_name: holiday.name
          });
        });
      } else {
        if (holiday.start_date >= start_date && holiday.start_date <= end_date) {
          holidayDates.push({
            date: holiday.start_date,
            name: holiday.name,
            salary_multiplier: holiday.salary_multiplier,
            category: holiday.category,
            is_period: false
          });
        }
      }
    });

    return res.status(200).json({
      success: true,
      data: holidayDates
    });
  } catch (error) {
    console.error('Error getting holidays in range:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get holidays in range',
      error: error.message
    });
  }
};

// Bulk create holidays (for setting up annual holidays)
exports.bulkCreateHolidays = async (req, res) => {
  try {
    const { holidays } = req.body;
    
    if (!Array.isArray(holidays)) {
      return res.status(400).json({
        success: false,
        message: 'Holidays must be an array'
      });
    }

    // Validate each holiday's salary_multiplier
    for (const holiday of holidays) {
      if (holiday.salary_multiplier !== undefined && 
          (holiday.salary_multiplier < 1.0 || holiday.salary_multiplier > 9.99)) {
        return res.status(400).json({
          success: false,
          message: `Invalid salary multiplier for holiday "${holiday.name}". Must be between 1.0 and 9.99`
        });
      }
    }
    
    const createdHolidays = await Holiday.bulkCreate(holidays, {
      ignoreDuplicates: true,
      validate: true
    });
    
    return res.status(201).json({
      success: true,
      message: `Created ${createdHolidays.length} holidays`,
      data: createdHolidays
    });
  } catch (error) {
    console.error('Error bulk creating holidays:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to bulk create holidays',
      error: error.message
    });
  }
};