const multer = require('multer');

// Configure multer for file upload
const upload = multer({
  dest: 'uploads/temp/',
  fileFilter: (req, file, cb) => {
    if (file.mimetype === 'text/csv' || file.originalname.endsWith('.csv')) {
      cb(null, true);
    } else {
      cb(new Error('Chỉ chấp nhận file CSV'));
    }
  },
  limits: {
    fileSize: 5 * 1024 * 1024 // 5MB
  }
});

module.exports = app => {
  const employees = require('../controllers/employee.controller');
  const router = require('express').Router();
  const auth = require('../middleware/auth.middleware');
  
  // Create employee
  router.post('/', auth, employees.createEmployee);

  // Get all employees
  router.get('/', auth, employees.getAllEmployees);

  // Update employee
  router.put('/:id_real', auth, employees.updateEmployee);

  // Delete employee
  router.delete('/:id_real', auth, employees.deleteEmployee);

  // work schedule
  router.put('/:id_real/schedule', auth, employees.updateWorkSchedule);
  router.get('/:id_real/schedule', employees.getWorkSchedule);

  // Export employees CSV
  router.get('/export/csv', auth, employees.exportEmployeesCSV);

  // Download CSV template
  router.get('/template/csv', auth, employees.downloadTemplate);

  // Import employees CSV
  router.post('/import/csv', auth, upload.single('csvFile'), employees.importEmployeesCSV);

  app.use('/api/employees', router);
};