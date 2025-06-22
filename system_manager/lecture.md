Collecting workspace informationDựa trên code hiện tại, tôi thấy hệ thống đã có logic phân biệt giữa nhân viên và giảng viên trong việc tính toán thống kê muộn. Tuy nhiên, cần làm rõ hơn về yêu cầu cho giảng viên. Đây là cách hệ thống hiện tại hoạt động và đề xuất cải tiến:

## Cách hệ thống hiện tại hoạt động:

### 1. Trong report.controller.js:

**Đối với nhân viên (`employee`):**
- Tính số phút muộn dựa trên `start_time`
- Thống kê số ngày muộn và tổng phút muộn

**Đối với giảng viên (`lecturer`):**
- Không tính muộn (`late_minutes = 0`)
- Không có thống kê ngày muộn

## Đề xuất cải tiến cho yêu cầu "giảng viên tuần đủ 8 tiếng":

### 1. Cập nhật report.controller.js để có báo cáo tuần cho giảng viên:

````javascript
// Thêm function mới cho báo cáo tuần giảng viên
exports.getWeeklyLecturerReport = async (req, res) => {
  try {
    const { weekStart } = req.params; // Format: YYYY-MM-DD (Monday của tuần)
    
    // Tính ngày cuối tuần (Sunday)
    const startDate = new Date(weekStart);
    const endDate = new Date(startDate);
    endDate.setDate(startDate.getDate() + 6);
    
    // Lấy tất cả giảng viên
    const lecturers = await Employee.findAll({
      where: { role: 'lecturer' }
    });
    
    const weeklyReport = [];
    
    for (const lecturer of lecturers) {
      // Lấy attendance records của giảng viên trong tuần
      const attendanceRecords = await Attendance.findAll({
        where: {
          id_real: lecturer.id_real,
          day: {
            [Op.between]: [
              startDate.toISOString().split('T')[0], 
              endDate.toISOString().split('T')[0]
            ]
          }
        }
      });
      
      // Tính tổng giờ làm trong tuần
      let totalWeeklyHours = 0;
      const dailyRecords = [];
      
      for (const record of attendanceRecords) {
        const firstTime = new Date(`2000-01-01 ${record.first_time}`);
        const lastTime = new Date(`2000-01-01 ${record.last_time}`);
        const dailyHours = (lastTime - firstTime) / (1000 * 60 * 60);
        
        totalWeeklyHours += dailyHours;
        dailyRecords.push({
          day: record.day,
          hours: parseFloat(dailyHours.toFixed(2))
        });
      }
      
      // Kiểm tra có đủ 8 tiếng/tuần không
      const isWeeklyGoalMet = totalWeeklyHours >= 8;
      const weeklyDeficit = Math.max(0, 8 - totalWeeklyHours);
      
      weeklyReport.push({
        id_real: lecturer.id_real,
        name: lecturer.full_name,
        role: lecturer.role,
        week_start: weekStart,
        total_weekly_hours: parseFloat(totalWeeklyHours.toFixed(2)),
        required_hours: 8,
        goal_met: isWeeklyGoalMet,
        deficit_hours: parseFloat(weeklyDeficit.toFixed(2)),
        days_worked: attendanceRecords.length,
        daily_records: dailyRecords,
        hourly_rate: parseFloat(lecturer.hourly_rate),
        weekly_salary: parseFloat((totalWeeklyHours * lecturer.hourly_rate).toFixed(2))
      });
    }
    
    return res.status(200).json({
      success: true,
      week_start: weekStart,
      week_end: endDate.toISOString().split('T')[0],
      total_lecturers: lecturers.length,
      lecturers_meeting_goal: weeklyReport.filter(l => l.goal_met).length,
      data: weeklyReport
    });
  } catch (error) {
    console.error('Error generating weekly lecturer report:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to generate weekly lecturer report',
      error: error.message
    });
  }
};

// Cập nhật monthly report để xử lý giảng viên theo tuần
exports.generateMonthlySalaryReport = async (req, res) => {
  try {
    const { month, year } = req.params;
    
    // Get all attendance records for the month
    const startDate = new Date(year, month - 1, 1);
    const endDate = new Date(year, month, 0);
    
    const attendanceRecords = await Attendance.findAll({
      where: {
        day: {
          [Op.between]: [startDate.toISOString().split('T')[0], endDate.toISOString().split('T')[0]]
        }
      }
    });
    
    // Group by employee
    const employeeData = {};
    
    for (const record of attendanceRecords) {
      if (!employeeData[record.id_real]) {
        employeeData[record.id_real] = {
          id_real: record.id_real,
          name: record.name,
          total_hours: 0,
          total_days: 0,
          late_days: 0,
          total_late_minutes: 0,
          records: [],
          // Thêm tracking theo tuần cho giảng viên
          weekly_data: {}
        };
      }
      
      // Calculate work hours for this day
      const firstTime = new Date(`2000-01-01 ${record.first_time}`);
      const lastTime = new Date(`2000-01-01 ${record.last_time}`);
      const workHours = (lastTime - firstTime) / (1000 * 60 * 60);
      
      employeeData[record.id_real].total_hours += workHours;
      employeeData[record.id_real].total_days += 1;
      employeeData[record.id_real].records.push(record);
      
      // Cho giảng viên: group theo tuần
      const recordDate = new Date(record.day);
      const weekStart = getWeekStart(recordDate); // Helper function
      
      if (!employeeData[record.id_real].weekly_data[weekStart]) {
        employeeData[record.id_real].weekly_data[weekStart] = {
          total_hours: 0,
          days_count: 0
        };
      }
      
      employeeData[record.id_real].weekly_data[weekStart].total_hours += workHours;
      employeeData[record.id_real].weekly_data[weekStart].days_count += 1;
    }
    
    // Calculate salary and performance metrics for each employee
    const salaryReports = [];
    
    for (const id_real in employeeData) {
      const employee = await Employee.findOne({ where: { id_real } });
      
      if (employee) {
        let performanceData = {};
        
        if (employee.role === 'employee') {
          // Cho nhân viên: tính muộn như cũ
          let lateData = { late_days: 0, total_late_minutes: 0 };
          
          for (const record of employeeData[id_real].records) {
            const standardStart = new Date(`2000-01-01 ${employee.start_time}`);
            const actualStart = new Date(`2000-01-01 ${record.first_time}`);
            if (actualStart > standardStart) {
              lateData.late_days += 1;
              lateData.total_late_minutes += (actualStart - standardStart) / (1000 * 60);
            }
          }
          
          performanceData = {
            late_days: lateData.late_days,
            total_late_minutes: Math.floor(lateData.total_late_minutes),
            // Thêm metrics cho nhân viên
            required_daily_hours: 8,
            avg_daily_hours: employeeData[id_real].total_days > 0 
              ? parseFloat((employeeData[id_real].total_hours / employeeData[id_real].total_days).toFixed(2)) 
              : 0
          };
        } else if (employee.role === 'lecturer') {
          // Cho giảng viên: tính theo tuần
          const weeklyPerformance = [];
          let weeksMetGoal = 0;
          let totalDeficitHours = 0;
          
          for (const weekStart in employeeData[id_real].weekly_data) {
            const weekData = employeeData[id_real].weekly_data[weekStart];
            const goalMet = weekData.total_hours >= 8;
            const deficit = Math.max(0, 8 - weekData.total_hours);
            
            if (goalMet) weeksMetGoal++;
            totalDeficitHours += deficit;
            
            weeklyPerformance.push({
              week_start: weekStart,
              hours: parseFloat(weekData.total_hours.toFixed(2)),
              goal_met: goalMet,
              deficit: parseFloat(deficit.toFixed(2))
            });
          }
          
          performanceData = {
            late_days: 0, // Giảng viên không tính muộn
            total_late_minutes: 0,
            // Metrics riêng cho giảng viên
            required_weekly_hours: 8,
            total_weeks: Object.keys(employeeData[id_real].weekly_data).length,
            weeks_meeting_goal: weeksMetGoal,
            total_deficit_hours: parseFloat(totalDeficitHours.toFixed(2)),
            weekly_performance: weeklyPerformance
          };
        }
        
        const totalSalary = employeeData[id_real].total_hours * employee.hourly_rate;
        
        const reportData = {
          id_real,
          name: employeeData[id_real].name,
          role: employee.role,
          month: parseInt(month),
          year: parseInt(year),
          total_hours: parseFloat(employeeData[id_real].total_hours.toFixed(2)),
          total_days_worked: employeeData[id_real].total_days,
          hourly_rate: parseFloat(employee.hourly_rate),
          total_salary: parseFloat(totalSalary.toFixed(2)),
          ...performanceData
        };
        
        // Save to database (có thể cần update schema để lưu thêm fields cho giảng viên)
        await SalaryReport.upsert({
          id_real,
          month: parseInt(month),
          year: parseInt(year),
          total_hours: reportData.total_hours,
          total_salary: reportData.total_salary,
          total_days_worked: reportData.total_days_worked,
          late_days: reportData.late_days,
          total_late_minutes: reportData.total_late_minutes
        });
        
        salaryReports.push(reportData);
      }
    }
    
    return res.status(200).json({
      success: true,
      month: parseInt(month),
      year: parseInt(year),
      total_employees: salaryReports.length,
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

// Helper function để tính ngày đầu tuần (Monday)
function getWeekStart(date) {
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
  const monday = new Date(date.setDate(diff));
  return monday.toISOString().split('T')[0];
}
````

### 2. Cập nhật Routes để thêm API báo cáo tuần:

````javascript
module.exports = app => {
  const reports = require('../controllers/report.controller');
  const router = require('express').Router();
  
  // Get daily report
  router.get('/daily/:date', reports.getDailyReport);
  
  // Generate monthly salary report
  router.get('/monthly/:year/:month', reports.generateMonthlySalaryReport);
  
  // Export monthly salary as CSV
  router.get('/monthly/:year/:month/csv', reports.exportMonthlySalaryCSV);
  
  // Thêm báo cáo tuần cho giảng viên
  router.get('/weekly/:weekStart', reports.getWeeklyLecturerReport);
  
  app.use('/api/reports', router);
};
````

### 3. Cập nhật Frontend để hiển thị metrics khác nhau:

````javascript
// Cập nhật MonthlyReport.js
const columns = [
  {
    title: 'Mã NV',
    dataIndex: 'id_real',
    key: 'id_real',
    width: 100,
  },
  {
    title: 'Họ và tên',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: 'Chức vụ',
    dataIndex: 'role',
    key: 'role',
    render: (role) => role === 'employee' ? 'Nhân viên' : 'Giảng viên'
  },
  {
    title: 'Tổng giờ',
    dataIndex: 'total_hours',
    key: 'total_hours',
    render: (hours) => `${hours}h`,
    sorter: (a, b) => a.total_hours - b.total_hours,
  },
  {
    title: 'Số ngày làm',
    dataIndex: 'total_days_worked',
    key: 'total_days_worked',
    sorter: (a, b) => a.total_days_worked - b.total_days_worked,
  },
  // Conditional columns based on role
  {
    title: 'Hiệu suất',
    key: 'performance',
    render: (_, record) => {
      if (record.role === 'employee') {
        return (
          <div>
            <div style={{ color: record.late_days > 0 ? '#ff4d4f' : '#52c41a' }}>
              Muộn: {record.late_days} ngày
            </div>
            <div style={{ color: record.total_late_minutes > 0 ? '#ff4d4f' : '#52c41a' }}>
              {record.total_late_minutes} phút
            </div>
          </div>
        );
      } else {
        // Giảng viên
        return (
          <div>
            <div style={{ color: record.weeks_meeting_goal === record.total_weeks ? '#52c41a' : '#ff4d4f' }}>
              Tuần đạt: {record.weeks_meeting_goal}/{record.total_weeks}
            </div>
            {record.total_deficit_hours > 0 && (
              <div style={{ color: '#ff4d4f' }}>
                Thiếu: {record.total_deficit_hours}h
              </div>
            )}
          </div>
        );
      }
    }
  },
  // ... other columns
];
````

## Tóm tắt các thay đổi:

1. **Nhân viên (`employee`)**: Giữ nguyên logic hiện tại - tính muộn theo giờ, thống kê ngày muộn và phút muộn
2. **Giảng viên (`lecturer`)**: 
   - Không tính muộn (như hiện tại)
   - Thêm tracking theo tuần để kiểm tra có đủ 8 tiếng/tuần
   - Báo cáo hiển thị số tuần đạt mục tiêu vs tổng số tuần
   - Tính số giờ thiếu nếu không đủ 8 tiếng/tuần

3. **API mới**: `/api/reports/weekly/:weekStart` để xem báo cáo tuần riêng cho giảng viên

Hệ thống này sẽ phân biệt rõ ràng giữa yêu cầu khác nhau cho nhân viên và giảng viên, phù hợp với tính chất công việc của từng vai trò.