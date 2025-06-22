const Attendance = require('../models/attendance.model');
const { Employee, SalaryReport } = require('../models/employee.model');
const Holiday = require('../models/holiday.model');
const { Op } = require('sequelize');
const { Parser } = require('json2csv');
const moment = require('moment');

// Define associations inline (one-time setup)
if (!Attendance.associations.employee) {
  Attendance.belongsTo(Employee, {
    foreignKey: 'id_real',
    targetKey: 'id_real',
    as: 'employee'
  });
}

if (!SalaryReport.associations.employee) {
  SalaryReport.belongsTo(Employee, {
    foreignKey: 'id_real',
    targetKey: 'id_real',
    as: 'employee'
  });
}

// Helper function để check ngày có phải holiday không
const isHolidayDate = async (date, employeeRole = 'all') => {
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
            { applies_to: `${employeeRole}_only` }
          ]
        }
      ]
    }
  });

  return {
    isHoliday: !!holiday,
    holidayInfo: holiday
  };
};

// Helper function để check ngày có phải holiday không và tính lương
const getHolidayInfo = async (date, employeeRole = 'all') => {
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
            { applies_to: `${employeeRole}_only` }
          ]
        }
      ]
    }
  });

  if (!holiday) {
    return {
      isHoliday: false,
      holidayInfo: null,
      salaryMultiplier: 1.0,
      allowWork: true,
      isPaidLeave: false
    };
  }

  return {
    isHoliday: true,
    holidayInfo: holiday,
    salaryMultiplier: parseFloat(holiday.salary_multiplier),
    allowWork: holiday.allow_work,
    isPaidLeave: holiday.leave_type === 'paid_holiday',
    salaryPolicy: holiday.salary_policy,
    leaveType: holiday.leave_type
  };
};

// Cải tiến hàm getHolidayInfo để sử dụng trong monthly report
const getMonthlyHolidayInfo = async (date, employeeRole = 'all') => {
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
            { applies_to: `${employeeRole}_only` }
          ]
        }
      ]
    }
  });

  if (!holiday) {
    return {
      isHoliday: false,
      salaryMultiplier: 1.0,
      allowWork: true,
      isPaidLeave: false,
      leaveType: null,
      salaryPolicy: null
    };
  }

  return {
    isHoliday: true,
    holidayInfo: holiday,
    salaryMultiplier: parseFloat(holiday.salary_multiplier),
    allowWork: holiday.allow_work,
    isPaidLeave: holiday.leave_type === 'paid_holiday',
    salaryPolicy: holiday.salary_policy,
    leaveType: holiday.leave_type,
    name: holiday.name
  };
};

// Helper function để tính giờ làm việc thực tế (trừ giờ nghỉ trưa)
const calculateActualWorkHours = (firstTime, lastTime, workSchedule, dayOfWeek) => {
  const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const dayName = dayNames[dayOfWeek];
  const daySchedule = workSchedule[dayName];
  
  if (!daySchedule || !daySchedule.active) {
    return 0; // Ngày không làm việc
  }
  
  const start = new Date(`2000-01-01 ${firstTime}`);
  const end = new Date(`2000-01-01 ${lastTime}`);
  const lunchStart = new Date(`2000-01-01 ${daySchedule.lunch_start}`);
  const lunchEnd = new Date(`2000-01-01 ${daySchedule.lunch_end}`);
  
  // Tổng thời gian có mặt
  let totalHours = (end - start) / (1000 * 60 * 60);
  
  // Trừ giờ nghỉ trưa nếu có overlap
  if (start < lunchEnd && end > lunchStart) {
    const lunchOverlapStart = Math.max(start.getTime(), lunchStart.getTime());
    const lunchOverlapEnd = Math.min(end.getTime(), lunchEnd.getTime());
    const lunchHours = (lunchOverlapEnd - lunchOverlapStart) / (1000 * 60 * 60);
    totalHours -= Math.max(0, lunchHours);
  }
  
  return Math.max(0, totalHours);
};

// Helper function để tính số phút muộn theo lịch làm việc
const calculateLateMinutes = (firstTime, workSchedule, dayOfWeek) => {
  const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
  const dayName = dayNames[dayOfWeek];
  const daySchedule = workSchedule[dayName];
  
  if (!daySchedule || !daySchedule.active) {
    return 0; // Ngày không làm việc
  }
  
  const actualStart = new Date(`2000-01-01 ${firstTime}`);
  const scheduledStart = new Date(`2000-01-01 ${daySchedule.start}`);
  
  if (actualStart > scheduledStart) {
    return (actualStart - scheduledStart) / (1000 * 60); // minutes
  }
  
  return 0;
};

// Generate daily report với holiday info chi tiết
exports.getDailyReport = async (req, res) => {
  try {
    const { date } = req.params;
    
    // Get all attendance records for the date
    const attendanceRecords = await Attendance.findAll({
      where: { day: date }
    });

    // Get all employees to include those who didn't attend
    const allEmployees = await Employee.findAll();
    
    const dayOfWeek = new Date(date).getDay();
    const reportData = [];
    let totalEmployees = allEmployees.length;

    for (const employee of allEmployees) {
      // Find attendance record for this employee
      const record = attendanceRecords.find(r => r.id_real === employee.id_real);
      
      // Get holiday information
      const holidayInfo = await getHolidayInfo(date, employee.role);
      
      if (!record) {
        // Employee didn't attend
        let dailySalary = 0;
        let status = 'absent';
        
        // Check if it's a paid holiday
        if (holidayInfo.isHoliday && holidayInfo.isPaidLeave) {
          // Paid holiday - calculate salary based on standard hours
          const standardHours = employee.standard_work_hours || 8;
          dailySalary = standardHours * employee.hourly_rate * holidayInfo.salaryMultiplier;
          status = 'paid_leave';
        }
        
        reportData.push({
          id_real: employee.id_real,
          name: employee.full_name,
          role: employee.role,
          first_time: null,
          last_time: null,
          work_hours: 0,
          late_minutes: 0,
          hourly_rate: parseFloat(employee.hourly_rate),
          daily_salary: parseFloat(dailySalary.toFixed(2)),
          status: status,
          is_work_day: false,
          is_holiday: holidayInfo.isHoliday,
          holiday_name: holidayInfo.holidayInfo?.name || null,
          holiday_type: holidayInfo.leaveType || null,
          salary_policy: holidayInfo.salaryPolicy || null,
          holiday_multiplier: holidayInfo.salaryMultiplier,
          allow_work: holidayInfo.allowWork
        });
        continue;
      }

      // Employee attended - calculate actual work
      const actualWorkHours = calculateActualWorkHours(
        record.first_time, 
        record.last_time, 
        employee.work_schedule, 
        dayOfWeek
      );
      
      // Calculate late minutes
      let lateMinutes = 0;
      if (employee.role === 'employee') {
        lateMinutes = calculateLateMinutes(
          record.first_time,
          employee.work_schedule,
          dayOfWeek
        );
      }

      // Check if this is a scheduled work day
      const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const dayName = dayNames[dayOfWeek];
      const isWorkDay = employee.work_schedule[dayName]?.active || false;

      // Calculate salary based on holiday policy
      let dailySalary = 0;
      let salaryMultiplier = 1.0;
      
      if (holidayInfo.isHoliday) {
        if (holidayInfo.allowWork && actualWorkHours > 0) {
          // Working on holiday - apply multiplier
          salaryMultiplier = holidayInfo.salaryMultiplier;
          dailySalary = actualWorkHours * employee.hourly_rate * salaryMultiplier;
        } else if (holidayInfo.isPaidLeave) {
          // Paid holiday - use standard hours
          const standardHours = employee.standard_work_hours || 8;
          salaryMultiplier = holidayInfo.salaryMultiplier;
          dailySalary = standardHours * employee.hourly_rate * salaryMultiplier;
        }
        // Unpaid leave - no salary
      } else {
        // Normal working day
        dailySalary = actualWorkHours * employee.hourly_rate;
      }

      reportData.push({
        id_real: record.id_real,
        name: employee.full_name,
        role: employee.role,
        first_time: record.first_time,
        last_time: record.last_time,
        work_hours: parseFloat(actualWorkHours.toFixed(2)),
        late_minutes: Math.max(0, Math.floor(lateMinutes)),
        hourly_rate: parseFloat(employee.hourly_rate),
        daily_salary: parseFloat(dailySalary.toFixed(2)),
        status: holidayInfo.isHoliday ? 'holiday_work' : 'present',
        is_work_day: isWorkDay,
        is_holiday: holidayInfo.isHoliday,
        holiday_name: holidayInfo.holidayInfo?.name || null,
        holiday_type: holidayInfo.leaveType || null,
        salary_policy: holidayInfo.salaryPolicy || null,
        holiday_multiplier: salaryMultiplier,
        allow_work: holidayInfo.allowWork,
        standard_hours: employee.standard_work_hours,
        overtime_hours: Math.max(0, actualWorkHours - (employee.standard_work_hours || 8))
      });
    }

    return res.status(200).json({
      success: true,
      date,
      day_of_week: dayOfWeek,
      total_employees: totalEmployees,
      present: reportData.filter(r => r.status === 'present').length,
      absent: reportData.filter(r => r.status === 'absent').length,
      paid_leave: reportData.filter(r => r.status === 'paid_leave').length,
      holiday_workers: reportData.filter(r => r.status === 'holiday_work').length,
      holiday_info: reportData.find(r => r.is_holiday)?.holiday_name || null,
      data: reportData
    });

  } catch (error) {
    console.error('Error generating daily report:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to generate daily report',
      error: error.message
    });
  }
};

// Generate monthly salary report với holiday support
// Generate monthly salary report với holiday policy đầy đủ
// Generate monthly salary report với holiday policy đầy đủ và error handling
exports.generateMonthlySalaryReport = async (req, res) => {
  try {
    const { month, year } = req.params;
    
    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0);
    
    // Single query with JOIN để get tất cả attendance records + employee info
    const attendanceRecords = await Attendance.findAll({
      where: {
        day: {
          [Op.between]: [startDate.toISOString().split('T')[0], endDate.toISOString().split('T')[0]]
        }
      },
      include: [{
        model: Employee,
        as: 'employee',
        attributes: ['full_name', 'role', 'hourly_rate', 'work_schedule', 'standard_work_hours'],
        required: true
      }]
    });

    // Get all employees để include cả những người không điểm danh
    const allEmployees = await Employee.findAll();
    
    // Group and calculate with advanced holiday support
    const employeeStats = {};
    
    // Initialize all employees với default values
    for (const employee of allEmployees) {
      employeeStats[employee.id_real] = {
        id_real: employee.id_real,
        name: employee.full_name,
        role: employee.role,
        hourly_rate: parseFloat(employee.hourly_rate) || 0,
        work_schedule: employee.work_schedule || {},
        standard_work_hours: parseFloat(employee.standard_work_hours) || 8.0,
        total_hours: 0,
        total_days: 0,
        late_days: 0,
        total_late_minutes: 0,
        overtime_hours: 0,
        holiday_hours: 0,
        holiday_bonus: 0,
        paid_leave_hours: 0,
        paid_leave_salary: 0,
        records: []
      };
    }
    
    // Process attendance records
    for (const record of attendanceRecords) {
      const { id_real, day } = record;
      const employee = record.employee;
      
      if (!employeeStats[id_real]) continue;
      
      const recordDate = new Date(day);
      const dayOfWeek = recordDate.getDay();
      
      // Get holiday info cho ngày này
      const holidayInfo = await getMonthlyHolidayInfo(day, employee.role);
      
      // Calculate actual work hours
      const actualWorkHours = calculateActualWorkHours(
        record.first_time,
        record.last_time,
        employee.work_schedule || {},
        dayOfWeek
      );
      
      // Check if it's a scheduled work day
      const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const dayName = dayNames[dayOfWeek];
      const isWorkDay = employee.work_schedule?.[dayName]?.active ?? true;
      
      if (actualWorkHours > 0) {
        if (holidayInfo.isHoliday && holidayInfo.allowWork) {
          // Working on holiday
          employeeStats[id_real].holiday_hours += actualWorkHours;
          
          // Calculate holiday bonus based on policy
          let holidayBonus = 0;
          if (holidayInfo.salaryPolicy === 'multiplier_pay') {
            holidayBonus = actualWorkHours * employee.hourly_rate * (holidayInfo.salaryMultiplier - 1);
          } else if (holidayInfo.salaryPolicy === 'full_pay') {
            holidayBonus = actualWorkHours * employee.hourly_rate * (holidayInfo.salaryMultiplier - 1);
          }
          
          employeeStats[id_real].holiday_bonus += holidayBonus;
        }
        
        employeeStats[id_real].total_hours += actualWorkHours;
        employeeStats[id_real].total_days += 1;
        employeeStats[id_real].records.push(record);
        
        // Calculate overtime
        const standardHours = employeeStats[id_real].standard_work_hours;
        const overtimeForDay = Math.max(0, actualWorkHours - standardHours);
        employeeStats[id_real].overtime_hours += overtimeForDay;
        
        // Calculate late minutes for employees only
        if (employee.role === 'employee') {
          const lateMinutes = calculateLateMinutes(
            record.first_time,
            employee.work_schedule || {},
            dayOfWeek
          );
          
          if (lateMinutes > 0) {
            employeeStats[id_real].late_days += 1;
            employeeStats[id_real].total_late_minutes += lateMinutes;
          }
        }
      }
    }
    
    // Calculate paid leave for holidays (nghỉ có lương)
    for (const employeeId in employeeStats) {
      const employee = allEmployees.find(emp => emp.id_real === employeeId);
      if (!employee) continue;
      
      // Check tất cả ngày trong tháng để tìm paid holidays không có attendance
      for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
        const dateStr = d.toISOString().split('T')[0];
        const dayOfWeek = d.getDay();
        
        // Check if có attendance record cho ngày này
        const hasAttendance = employeeStats[employeeId].records.some(r => r.day === dateStr);
        
        if (!hasAttendance) {
          // Check if là paid holiday
          const holidayInfo = await getMonthlyHolidayInfo(dateStr, employee.role);
          
          if (holidayInfo.isHoliday && holidayInfo.isPaidLeave) {
            // Check if đây là ngày làm việc theo schedule
            const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
            const dayName = dayNames[dayOfWeek];
            const isWorkDay = employee.work_schedule?.[dayName]?.active ?? true;
            
            if (isWorkDay) {
              const standardHours = employee.standard_work_hours || 8.0;
              const paidLeaveSalary = standardHours * employee.hourly_rate * holidayInfo.salaryMultiplier;
              
              employeeStats[employeeId].paid_leave_hours += standardHours;
              employeeStats[employeeId].paid_leave_salary += paidLeaveSalary;
            }
          }
        }
      }
    }
    
    // Prepare salary reports với comprehensive calculations và safe parsing
    const salaryReports = Object.values(employeeStats).map(emp => {
      // Ensure all values are numbers with fallbacks
      const totalHours = parseFloat(emp.total_hours) || 0;
      const hourlyRate = parseFloat(emp.hourly_rate) || 0;
      const holidayBonus = parseFloat(emp.holiday_bonus) || 0;
      const paidLeaveSalary = parseFloat(emp.paid_leave_salary) || 0;
      
      const baseSalary = totalHours * hourlyRate;
      const totalSalary = baseSalary + holidayBonus + paidLeaveSalary;
      
      return {
        id_real: emp.id_real,
        name: emp.name,
        role: emp.role,
        month: parseInt(month),
        year: parseInt(year),
        total_hours: parseFloat(totalHours.toFixed(2)),
        total_days_worked: parseInt(emp.total_days) || 0,
        late_days: parseInt(emp.late_days) || 0,
        total_late_minutes: Math.floor(parseFloat(emp.total_late_minutes) || 0),
        hourly_rate: hourlyRate,
        base_salary: parseFloat(baseSalary.toFixed(2)),
        holiday_hours: parseFloat((parseFloat(emp.holiday_hours) || 0).toFixed(2)),
        holiday_bonus: parseFloat(holidayBonus.toFixed(2)),
        paid_leave_hours: parseFloat((parseFloat(emp.paid_leave_hours) || 0).toFixed(2)),
        paid_leave_salary: parseFloat(paidLeaveSalary.toFixed(2)),
        total_salary: parseFloat(totalSalary.toFixed(2)),
        overtime_hours: parseFloat((parseFloat(emp.overtime_hours) || 0).toFixed(2))
      };
    });
    
    // Bulk upsert với fields mới
    if (salaryReports.length > 0) {
      await SalaryReport.bulkCreate(
        salaryReports.map(report => ({
          id_real: report.id_real,
          month: report.month,
          year: report.year,
          total_hours: report.total_hours,
          total_salary: report.total_salary,
          total_days_worked: report.total_days_worked,
          late_days: report.late_days,
          total_late_minutes: report.total_late_minutes,
          holiday_hours: report.holiday_hours,
          holiday_bonus: report.holiday_bonus
        })),
        {
          updateOnDuplicate: [
            'total_hours', 'total_salary', 'total_days_worked', 
            'late_days', 'total_late_minutes', 'holiday_hours', 'holiday_bonus'
          ],
          ignoreDuplicates: false
        }
      );
    }
    
    return res.status(200).json({
      success: true,
      month: parseInt(month),
      year: parseInt(year),
      total_employees: salaryReports.length,
      total_base_salary: salaryReports.reduce((sum, r) => sum + (parseFloat(r.base_salary) || 0), 0),
      total_holiday_bonus: salaryReports.reduce((sum, r) => sum + (parseFloat(r.holiday_bonus) || 0), 0),
      total_paid_leave_salary: salaryReports.reduce((sum, r) => sum + (parseFloat(r.paid_leave_salary) || 0), 0),
      total_salary: salaryReports.reduce((sum, r) => sum + (parseFloat(r.total_salary) || 0), 0),
      data: salaryReports
    });
  } catch (error) {
    console.error('Error generating monthly salary report:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to generate monthly salary report',
      error: error.message
    });
  }
};

// Export monthly report as CSV với holiday info đầy đủ
exports.exportMonthlySalaryCSV = async (req, res) => {
  try {
    const { month, year } = req.params;
    
    // Re-generate report to get latest calculations
    const reportResponse = await this.generateMonthlySalaryReport(req, { status: () => ({ json: (data) => data }) });
    const salaryReports = reportResponse.data || [];
    
    if (salaryReports.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'No salary reports found for this month'
      });
    }
    
    const csvData = salaryReports.map(report => ({
      'ID': report.id_real,
      'Họ và tên': report.name,
      'Chức vụ': report.role === 'employee' ? 'Nhân viên' : 'Giảng viên',
      'Tháng': report.month,
      'Năm': report.year,
      'Tổng giờ làm': report.total_hours,
      'Giờ làm ngày lễ': report.holiday_hours || 0,
      'Giờ nghỉ có lương': report.paid_leave_hours || 0,
      'Số ngày làm việc': report.total_days_worked,
      'Số ngày muộn': report.late_days,
      'Tổng phút muộn': report.total_late_minutes,
      'Lương cơ bản (VNĐ)': report.base_salary || report.total_salary,
      'Phụ cấp ngày lễ (VNĐ)': report.holiday_bonus || 0,
      'Lương nghỉ có lương (VNĐ)': report.paid_leave_salary || 0,
      'Tổng lương (VNĐ)': report.total_salary
    }));
    
    const parser = new Parser();
    const csv = parser.parse(csvData);
    
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename=salary_report_${month}_${year}.csv`);
    
    return res.status(200).send('\uFEFF' + csv);
  } catch (error) {
    console.error('Error exporting CSV:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to export CSV',
      error: error.message
    });
  }
};