module.exports = app => {
  const reports = require('../controllers/report.controller');
  const router = require('express').Router();
  const auth = require('../middleware/auth.middleware');
  
  // Get daily report
  router.get('/daily/:date', auth, reports.getDailyReport);

  // Generate monthly salary report
  router.get('/monthly/:year/:month', auth, reports.generateMonthlySalaryReport);

  // Export monthly salary as CSV
  router.get('/monthly/:year/:month/csv', auth, reports.exportMonthlySalaryCSV);

  app.use('/api/reports', router);
};