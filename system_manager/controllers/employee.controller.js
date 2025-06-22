const { Employee } = require('../models/employee.model');
const { Parser } = require('json2csv');
const multer = require('multer');
const csv = require('csv-parser');
const fs = require('fs');

// Create employee
exports.createEmployee = async (req, res) => {
  try {
    const { id_real, full_name, role, hourly_rate } = req.body;
    
    if (!id_real || !full_name || !role || !hourly_rate) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: id_real, full_name, role, hourly_rate'
      });
    }
    
    const employee = await Employee.create({
      id_real,
      full_name,
      role,
      hourly_rate
    });
    
    return res.status(201).json({
      success: true,
      message: 'Employee created successfully',
      data: employee
    });
  } catch (error) {
    console.error('Error creating employee:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to create employee',
      error: error.message
    });
  }
};

// Get all employees
exports.getAllEmployees = async (req, res) => {
  try {
    const employees = await Employee.findAll();
    
    return res.status(200).json({
      success: true,
      count: employees.length,
      data: employees
    });
  } catch (error) {
    console.error('Error getting employees:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to get employees',
      error: error.message
    });
  }
};

// Update employee
exports.updateEmployee = async (req, res) => {
  try {
    const { id_real } = req.params;
    const updateData = req.body;
    
    const employee = await Employee.findOne({ where: { id_real } });
    
    if (!employee) {
      return res.status(404).json({
        success: false,
        message: 'Employee not found'
      });
    }
    
    await employee.update(updateData);
    
    return res.status(200).json({
      success: true,
      message: 'Employee updated successfully',
      data: employee
    });
  } catch (error) {
    console.error('Error updating employee:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to update employee',
      error: error.message
    });
  }
};

// Delete employee
exports.deleteEmployee = async (req, res) => {
  try {
    const { id_real } = req.params;

    const employee = await Employee.findOne({ where: { id_real } });

    if (!employee) {
      return res.status(404).json({
        success: false,
        message: 'Employee not found'
      });
    }

    await employee.destroy();

    return res.status(200).json({
      success: true,
      message: 'Employee deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting employee:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to delete employee',
      error: error.message
    });
  }
};

// Export employees to CSV
exports.exportEmployeesCSV = async (req, res) => {
  try {
    const employees = await Employee.findAll({
      order: [['id_real', 'ASC']]
    });
    
    if (employees.length === 0) {
      return res.status(404).json({
        success: false,
        message: 'No employees found to export'
      });
    }
    
    const csvData = employees.map(employee => {
      // Format work schedule for CSV export
      const schedule = employee.work_schedule || {};
      const activeDays = Object.entries(schedule)
        .filter(([day, config]) => config && config.active)
        .map(([day, config]) => `${day}:${config.start}-${config.end}`)
        .join(';');
      
      return {
        'Mã nhân viên': employee.id_real,
        'Họ và tên': employee.full_name,
        'Chức vụ': employee.role === 'employee' ? 'Nhân viên' : 'Giảng viên',
        'Lương/giờ (VNĐ)': employee.hourly_rate,
        'Giờ làm việc tiêu chuẩn': employee.standard_work_hours || 8.0,
        'Loại lịch': employee.schedule_type || 'fixed',
        'Lịch làm việc': activeDays || 'Chưa thiết lập',
        'Ngày tạo': new Date(employee.createdAt).toLocaleDateString('vi-VN')
      };
    });
    
    const parser = new Parser();
    const csv = parser.parse(csvData);
    
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename=danh_sach_nhan_vien.csv');
    
    return res.status(200).send('\ufeff' + csv); // Add BOM for Vietnamese characters
  } catch (error) {
    console.error('Error exporting employees CSV:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to export employees CSV',
      error: error.message
    });
  }
};

// Import employees from CSV
exports.importEmployeesCSV = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: 'No file uploaded'
      });
    }
    
    const results = [];
    const errors = [];
    let lineNumber = 1;
    
    return new Promise((resolve, reject) => {
      fs.createReadStream(req.file.path)
        .pipe(csv())
        .on('data', (data) => {
          lineNumber++;
          try {
            // Fix BOM issue - clean all keys
            const cleanData = {};
            Object.keys(data).forEach(key => {
              const cleanKey = key.replace(/^\uFEFF/, '').trim();
              cleanData[cleanKey] = data[key];
            });

            // Validate required fields
            const id_real = cleanData['Mã nhân viên'] || cleanData['id_real'];
            const full_name = cleanData['Họ và tên'] || cleanData['full_name'];
            const role_text = cleanData['Chức vụ'] || cleanData['role'];
            const hourly_rate = cleanData['Lương/giờ (VNĐ)'] || cleanData['hourly_rate'];
            
            // Optional fields với default values
            const standard_work_hours = cleanData['Giờ làm việc tiêu chuẩn'] || cleanData['standard_work_hours'] || 8.0;
            const schedule_type = cleanData['Loại lịch'] || cleanData['schedule_type'] || 'fixed';

            // Check for missing required fields
            if (!id_real || !full_name || !role_text || !hourly_rate) {
              errors.push(`Dòng ${lineNumber}: Thiếu thông tin bắt buộc`);
              return;
            }
            
            // Convert role
            let role;
            if (role_text === 'Nhân viên' || role_text.toLowerCase() === 'employee') {
              role = 'employee';
            } else if (role_text === 'Giảng viên' || role_text.toLowerCase() === 'lecturer') {
              role = 'lecturer';
            } else {
              errors.push(`Dòng ${lineNumber}: Chức vụ không hợp lệ (${role_text})`);
              return;
            }
            
            // Validate hourly rate
            const rate = parseFloat(hourly_rate.toString().replace(/[,\s]/g, ''));
            if (isNaN(rate) || rate <= 0) {
              errors.push(`Dòng ${lineNumber}: Lương/giờ không hợp lệ (${hourly_rate})`);
              return;
            }

            // Validate standard work hours
            const workHours = parseFloat(standard_work_hours);
            if (isNaN(workHours) || workHours <= 0 || workHours > 12) {
              errors.push(`Dòng ${lineNumber}: Giờ làm việc tiêu chuẩn không hợp lệ (${standard_work_hours})`);
              return;
            }

            // Validate schedule type
            const validScheduleTypes = ['fixed', 'flexible', 'shift'];
            if (!validScheduleTypes.includes(schedule_type)) {
              errors.push(`Dòng ${lineNumber}: Loại lịch không hợp lệ (${schedule_type})`);
              return;
            }
            
            // Create default work schedule based on role
            let defaultWorkSchedule;
            if (role === 'employee') {
              // Nhân viên: Thứ 2-6, 8h-17h
              defaultWorkSchedule = {
                monday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                tuesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                wednesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                thursday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                friday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                saturday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null },
                sunday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null }
              };
            } else {
              // Giảng viên: Linh hoạt hơn, chỉ thứ 2-6
              defaultWorkSchedule = {
                monday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                tuesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                wednesday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                thursday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                friday: { active: true, start: "08:00:00", end: "17:00:00", lunch_start: "12:00:00", lunch_end: "13:00:00" },
                saturday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null },
                sunday: { active: false, start: null, end: null, lunch_start: null, lunch_end: null }
              };
            }
            
            results.push({
              id_real: id_real.toString().trim(),
              full_name: full_name.toString().trim(),
              role,
              hourly_rate: rate,
              standard_work_hours: workHours,
              schedule_type,
              work_schedule: defaultWorkSchedule
            });
          } catch (error) {
            errors.push(`Dòng ${lineNumber}: Lỗi xử lý dữ liệu - ${error.message}`);
          }
        })
        .on('end', async () => {
          try {
            // Clean up uploaded file
            fs.unlinkSync(req.file.path);
            
            if (errors.length > 0) {
              return res.status(400).json({
                success: false,
                message: 'Có lỗi trong file CSV',
                errors: errors,
                total_processed: results.length
              });
            }
            
            if (results.length === 0) {
              return res.status(400).json({
                success: false,
                message: 'File CSV không có dữ liệu hợp lệ'
              });
            }
            
            // Import data
            const imported = [];
            const duplicates = [];
            
            for (const employeeData of results) {
              try {
                const existingEmployee = await Employee.findOne({
                  where: { id_real: employeeData.id_real }
                });
                
                if (existingEmployee) {
                  duplicates.push(employeeData.id_real);
                } else {
                  const newEmployee = await Employee.create(employeeData);
                  imported.push(newEmployee);
                }
              } catch (createError) {
                errors.push(`Lỗi tạo nhân viên ${employeeData.id_real}: ${createError.message}`);
              }
            }
            
            resolve(res.status(200).json({
              success: true,
              message: 'Import hoàn thành',
              data: {
                total_rows: results.length,
                imported: imported.length,
                duplicates: duplicates.length,
                errors: errors.length,
                duplicate_ids: duplicates,
                error_messages: errors
              }
            }));
          } catch (error) {
            reject(res.status(500).json({
              success: false,
              message: 'Lỗi xử lý import',
              error: error.message
            }));
          }
        })
        .on('error', (error) => {
          // Clean up uploaded file
          if (req.file && req.file.path) {
            fs.unlinkSync(req.file.path);
          }
          reject(res.status(500).json({
            success: false,
            message: 'Lỗi đọc file CSV',
            error: error.message
          }));
        });
    });
  } catch (error) {
    console.error('Error importing employees CSV:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to import employees CSV',
      error: error.message
    });
  }
};

// Download CSV template
exports.downloadTemplate = (req, res) => {
  try {
    const templateData = [
      {
        'Mã nhân viên': 'EMP001',
        'Họ và tên': 'Nguyễn Văn A',
        'Chức vụ': 'Nhân viên',
        'Lương/giờ (VNĐ)': '50000',
        'Giờ làm việc tiêu chuẩn': '8.0',
        'Loại lịch': 'fixed'
      },
      {
        'Mã nhân viên': 'LEC001',
        'Họ và tên': 'Trần Thị B',
        'Chức vụ': 'Giảng viên',
        'Lương/giờ (VNĐ)': '80000',
        'Giờ làm việc tiêu chuẩn': '8.0',
        'Loại lịch': 'flexible'
      }
    ];
    
    const parser = new Parser();
    const csv = parser.parse(templateData);
    
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename=mau_danh_sach_nhan_vien.csv');
    
    return res.status(200).send('\ufeff' + csv);
  } catch (error) {
    console.error('Error downloading template:', error);
    return res.status(500).json({
      success: false,
      message: 'Failed to download template',
      error: error.message
    });
  }
};

// Thêm function để cập nhật lịch làm việc
exports.updateWorkSchedule = async (req, res) => {
  try {
    const { id_real } = req.params;
    const { work_schedule, standard_work_hours, schedule_type } = req.body;

    // Validate work schedule
    const validDays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    
    for (const day of validDays) {
      if (work_schedule[day] && work_schedule[day].active) {
        const { start, end, lunch_start, lunch_end } = work_schedule[day];
        
        // Validate time format and logic
        if (!start || !end || !lunch_start || !lunch_end) {
          return res.status(400).json({
            success: false,
            message: `Thiếu thông tin giờ làm việc cho ngày ${day}`
          });
        }
        
        // Check if lunch break is within work hours
        if (lunch_start <= start || lunch_end >= end || lunch_start >= lunch_end) {
          return res.status(400).json({
            success: false,
            message: `Giờ nghỉ trưa không hợp lệ cho ngày ${day}`
          });
        }
      }
    }

    const employee = await Employee.findOne({ where: { id_real } });
    if (!employee) {
      return res.status(404).json({
        success: false,
        message: 'Không tìm thấy nhân viên'
      });
    }

    await Employee.update(
      { 
        work_schedule, 
        standard_work_hours: standard_work_hours || 8.0,
        schedule_type: schedule_type || 'fixed'
      },
      { where: { id_real } }
    );

    return res.status(200).json({
      success: true,
      message: 'Cập nhật lịch làm việc thành công',
      data: { work_schedule, standard_work_hours, schedule_type }
    });

  } catch (error) {
    console.error('Error updating work schedule:', error);
    return res.status(500).json({
      success: false,
      message: 'Lỗi cập nhật lịch làm việc',
      error: error.message
    });
  }
};

// Lấy lịch làm việc của nhân viên
exports.getWorkSchedule = async (req, res) => {
  try {
    const { id_real } = req.params;
    
    const employee = await Employee.findOne({ 
      where: { id_real },
      attributes: ['id_real', 'full_name', 'role', 'work_schedule', 'standard_work_hours', 'schedule_type']
    });

    if (!employee) {
      return res.status(404).json({
        success: false,
        message: 'Không tìm thấy nhân viên'
      });
    }

    return res.status(200).json({
      success: true,
      data: employee
    });

  } catch (error) {
    console.error('Error getting work schedule:', error);
    return res.status(500).json({
      success: false,
      message: 'Lỗi lấy lịch làm việc',
      error: error.message
    });
  }
};