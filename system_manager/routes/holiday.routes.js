module.exports = app => {
  const holidays = require('../controllers/holiday.controller');
  const router = require('express').Router();

  // Get all holidays
  router.get('/', holidays.getAllHolidays);
  
  // Get holidays by year
  router.get('/year/:year', holidays.getHolidaysByYear);
  
  // Check if specific date is holiday
  router.get('/check/:date', holidays.isHoliday);
  
  // Get holidays in date range
  router.get('/range', holidays.getHolidaysInRange);
  
  // Create holiday
  router.post('/', holidays.createHoliday);
  
  // Update holiday
  router.put('/:id', holidays.updateHoliday);
  
  // Delete holiday
  router.delete('/:id', holidays.deleteHoliday);

  app.use('/api/holidays', router);
};